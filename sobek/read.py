# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 14:15:46 2019

@author: danie
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString,Point
import os
import re
import numpy as np
import hkvsobekpy as his
import csv

def __between(value, a, b):
    # Find and validate before-part.
    pos_a = value.find(a)
    if pos_a == -1: return ""
    # Find and validate after part.
    pos_b = value.rfind(b)
    if pos_b == -1: return ""
    # Return middle part.
    adjusted_pos_a = pos_a + len(a)
    if adjusted_pos_a >= pos_b: return ""
    return value[adjusted_pos_a:pos_b]

def __split_line(lineString, point,buffer=False):
    if not buffer: 
        pointIntersect = point
    else: pointIntersect = point.buffer(buffer)
    coords = lineString.coords
    j = None    
    for i in range(len(coords) - 1):
        if LineString(coords[i:i + 2]).intersects(pointIntersect):
           j = i
           break    
    assert j is not None    
    # Make sure to always include the point in the first group
    return coords[:j + 1] + [Point(point).coords[0]], [Point(point).coords[0]] + coords[j + 1:]


__friction_models = {'0': 'chezy',
                     '1': 'manning',
                     '2': 'strickler (kn)',
                     '3': 'strickler (ks)',
                     '4': 'white-colebrook',
                     '7':  'bos and bijkerk'}

__flow_boundary_types = {'0': 'waterlevel',
                         '1': 'discharge'}

__profile_types = {}

#%% read network
def network(path,crs):
    links = gpd.GeoDataFrame(columns=['ID','FROM_NODE','TO_NODE','geometry'],geometry='geometry')
    nodes = gpd.GeoDataFrame(columns=['ID','geometry'],geometry='geometry')
    
    with open(os.path.join(path,'network.tp'),'r') as networkTP:
       for line in networkTP.readlines():
        if line[0:4] == 'NODE':
            ident = __between(line,"id '","' nm")
            x = float(__between(line,"px "," py"))
            y = float(__between(line,"py "," node"))
            nodes = nodes.append({'ID':ident,'geometry':Point(x,y)}, ignore_index=True)
        elif line[0:4] == 'BRCH':
            ident = __between(line,"id '","' nm")
            from_node = __between(line,"bn '","' en")
            to_node = __between(line,"en '","' al")
            links = links.append({'ID':ident,'FROM_NODE':from_node,'TO_NODE':to_node}, ignore_index=True)  
            
    # open network.cp to define channel geometry
    with open(os.path.join(path,'network.cp'),'r') as networkCP:
        for reach in networkCP.read().split('BRCH')[1:]:
            ident = __between(reach, "id '","' cp")
            cps = __between(reach, 'TBLE\n',' <\ntble').split(' <\n')
            from_node = list(links.loc[links['ID'] == ident,'FROM_NODE'])[0]
            to_node = list(links.loc[links['ID'] == ident,'TO_NODE'])[0]
            coord_list = list(list(nodes.loc[nodes['ID'] == from_node].geometry)[0].coords)
            sumDistance = 0.
            for idx, cp in enumerate(cps):
                distance, angle = cp.split()
                distance = (float(distance) - sumDistance) *2
                angle = np.deg2rad(90-float(angle))
                x = coord_list[-1][0] + float(distance) * np.cos(angle)
                y = coord_list[-1][1] + float(distance) * np.sin(angle)
                coord_list += [(x,y)]
                sumDistance += distance
            coord_list[-1] = list(list(nodes.loc[nodes['ID'] == to_node].geometry)[0].coords)[0]
            index = links.loc[links['ID'] == ident].index[0]
            links.at[index,'geometry'] = LineString(coord_list)

    network = {}
    objects = gpd.GeoDataFrame(columns=['ID','TYPE','geometry'],geometry='geometry',crs=crs)
    objects_list = []
    with open(os.path.join(path,'network.ntw'),'r') as networkNTW:
        doLinks = True
        for idx, l in  enumerate(csv.reader(networkNTW.readlines(), quotechar='"', delimiter=',',
                     quoting=csv.QUOTE_ALL)):
            if idx > 0:
                if doLinks:
                    if l[0] == '*': doLinks = False
                if doLinks:
                    network.update({l[0]:{'properties':
                        {'type':l[4],'customType':l[5],'startNode':l[14],'endNode':l[27]},
                        'lineString':[[float(l[21]),float(l[22])],[float(l[34]),float(l[35])]]}})
                    if not l[14] in objects_list:
                        objects_list.append(l[14])
                        objects = objects.append({'ID':l[14],'TYPE':l[19],'geometry':Point([float(l[21]),float(l[22])])}, ignore_index=True)
                    if not l[27] in objects_list:
                        objects_list.append(l[27]) 
                        objects = objects.append({'ID':l[27],'TYPE':l[32],'geometry':Point([float(l[34]),float(l[35])])}, ignore_index=True)

    h_points = gpd.GeoDataFrame(columns=['ID','geometry'],geometry='geometry',crs=crs)
    v_links = gpd.GeoDataFrame(columns=['ID','TYPE','CUSTOM_TYPE','FROM_NODE','TO_NODE','geometry'],geometry='geometry',crs=crs)
                       
    with open(os.path.join(path,'network.gr'),'r') as networkGR:
        hLocations = his.read_his.ReadMetadata(os.path.join(path,'calcpnt.his'), hia_file='auto').GetLocations()
        for reach in networkGR.read().split('GRID')[1:]:
            ident = __between(reach, "id '","' ci")
            line = list(links.loc[links['ID'] == ident,'geometry'])[0]
            gridTable = __between(reach, 'TBLE\n',' <\ntble').split(' <\n')
            for idx, grid in enumerate(gridTable):
                grid = grid.split()
                h_point = grid[3].replace("'","")
                if h_point in hLocations: #check if point is ignored by Sobek-core
                    point = (float(grid[5]),float(grid[6]))
                    if not h_point in list(h_points['ID']):
                        h_points = h_points.append({'ID':h_point,'geometry':Point(point)}, ignore_index=True)
                    if idx == 0:
                        v_point = grid[4].replace("'","")
                        Type = network[v_point]['properties']['type']
                        customType = network[v_point]['properties']['customType']
                        pointFrom = h_point
                    else:
                        pointTo = h_point
                        segment, line = __split_line(LineString(line),Point(point),buffer=0.01)
                        v_links = v_links.append({'ID':v_point,'TYPE':Type,'CUSTOM_TYPE':customType,'FROM_NODE':pointFrom,'TO_NODE':pointTo,'geometry':LineString(segment)}, ignore_index=True)
                        v_point = grid[4].replace("'","")
                        pointFrom = h_point
    return {'links':links.set_crs(crs,inplace=True),
            'nodes':nodes.set_crs(crs,inplace=True),
            'objects':objects.set_crs(crs,inplace=True),
            'segments':v_links.set_crs(crs,inplace=True)}

def results(path):
    files = {'links':'reachseg.his','points':'calcpnt.his','structures':'struc.his'}
    result = {'links':None,'points':None,'structures':None}
    for key,item in files.items():
        if os.path.exists(os.path.join(path,item)):
            meta_data = his.read_his.ReadMetadata(os.path.join(path,item), hia_file='auto')
            parameters = meta_data.GetParameters()
            locations = meta_data.GetLocations()
            result.update({key: {'df':meta_data.DataFrame(),'parameters':parameters,
                                 'locations':locations}})
        
    return result

def parameters(path):
    ''' function to read parameters from a sobek case'''
    result = dict()
    with path.joinpath('friction.dat').open() as friction_dat:
        result['friction'] = dict()
        for line in friction_dat:
            if re.match("BDFR",line):
                model = __friction_models[__between(line, 'mf',' mt').replace(' ','')]
                value = float(__between(line, 'mt cp 0','0 mr').replace(' ',''))
                result['friction']['global'] = {'model':model,
                                                'value':value}
                
    return result

def boundaries(path):
    ''' function to read boundaries from a sobek case'''
    result = dict()
    with path.joinpath('BOUNDARY.DAT').open() as boundary_dat:
        result['flow'] = dict()
        for line in boundary_dat:
            if re.match('FLBO',line):
                ident = __between(line, 'id','st').replace(' ','').replace("'","")
                result['flow'][ident] = {'TYPE':__flow_boundary_types[re.search(".ty ([0-9]).",line).group(1)]}
        result['flow'] = pd.DataFrame.from_dict(result['flow'],orient='index')
        
    return result
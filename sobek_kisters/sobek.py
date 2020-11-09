# -*- coding: utf-8 -*-

import csv
import os
import re
import numpy
import fiona
from shapely.geometry import Point,LineString,mapping
import hkvsobekpy as his

def between(value, a, b):
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

def split_line(lineString, point,buffer=False):
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

class sobek(object):

    def __init__(self,path,crs='epsg:28992'):
        with open(os.path.join(os.path.abspath(path),'caselist.cmt'),'r') as CSV:
            self.cases = {}
            for line in CSV.readlines():
                line_split = re.split(r" '",line.replace("'\n",""))
                self.cases.update({line_split[1]:{'caseNum':line_split[0],'crs':crs,'topology':{'reaches':None,'network':None,'calcGrid':
                {'reachSegments':None,'HPoints':None}}}})
        self.path = os.path.abspath(path)
    
    def set_reaches(self,case):
        self.cases[case]['topology']['reaches'] = {}
        if case in list(self.cases.keys()):       
            caseDir = os.path.join(self.path,self.cases[case]['caseNum'])
            # open network.tp to create connection nodes and branches
            nodes = {}
            with open(os.path.join(caseDir,'network.tp'),'r') as networkTP:
                for line in networkTP.readlines():
                    if line[0:4] == 'NODE':
                        ident = between(line,"id '","' nm")
                        x = float(between(line,"px "," py"))
                        y = float(between(line,"py "," node"))
                        nodes.update({ident:{'x':x,'y':y}})
                    elif line[0:4] == 'BRCH':
                        ident = between(line,"id '","' nm")
                        startNode = between(line,"bn '","' en")
                        endNode = between(line,"en '","' al")
                        self.cases[case]['topology']['reaches'].update({ident:{'properties':
                            {'startNode':nodes[startNode],'endNode':nodes[endNode]}}})
               
            # open network.cp to define reach vertices
            with open(os.path.join(caseDir,'network.cp'),'r') as networkCP:
                for reach in networkCP.read().split('BRCH')[1:]:
                    ident = between(reach, "id '","' cp")
                    cps = between(reach, 'TBLE\n',' <\ntble').split(' <\n')
                    lineString = [[self.cases[case]['topology']['reaches'][ident]['properties']['startNode']['x'],
                                  self.cases[case]['topology']['reaches'][ident]['properties']['startNode']['y']]]
                    sumDistance = 0.
                    for idx, cp in enumerate(cps):
                        distance, angle = cp.split()
                        distance = (float(distance) - sumDistance) *2
                        angle = numpy.deg2rad(90-float(angle))
                        x = lineString[-1][0] + float(distance) * numpy.cos(angle)
                        y = lineString[-1][1] + float(distance) * numpy.sin(angle)
                        lineString += [[x,y]]
                        sumDistance += distance
                    lineString[-1] = [self.cases[case]['topology']['reaches'][ident]['properties']['endNode']['x'],
                               self.cases[case]['topology']['reaches'][ident]['properties']['endNode']['y']]
                    self.cases[case]['topology']['reaches'][ident].update({'lineString':lineString})
              
    def set_network(self,case):
        self.cases[case]['topology']['network'] = {}
        if case in list(self.cases.keys()):       
            caseDir = os.path.join(self.path,self.cases[case]['caseNum'])            
                    # open network.ntw to define the network
            with open(os.path.join(caseDir,'network.ntw'),'r') as networkNTW:
                doLinks = True
                for idx, l in  enumerate(csv.reader(networkNTW.readlines(), quotechar='"', delimiter=',',
                             quoting=csv.QUOTE_ALL, skipinitialspace=True)):
                    if idx > 0:
                        if doLinks:
                            if l[0] == '*': doLinks = False
                        if doLinks:
                            self.cases[case]['topology']['network'].update({l[0]:{'properties':
                                {'type':l[4],'customType':l[5],'startNode':l[14],'endNode':l[27]},
                                'lineString':[[float(l[21]),float(l[22])],[float(l[34]),float(l[35])]]}})

    def set_calcGrid(self,case):
        # can only be created if network and reaches are present
        if self.cases[case]['topology']['network'] == None: self.set_network(case)
        if self.cases[case]['topology']['reaches'] == None: self.set_reaches(case)
        self.cases[case]['topology']['calcGrid'] = {'reachSegments':{},'HPoints':{}}
        if case in list(self.cases.keys()):       
            caseDir = os.path.join(self.path,self.cases[case]['caseNum'])            
            if case in list(self.cases.keys()):                        
                with open(os.path.join(caseDir,'network.gr'),'r') as networkGR:
                    hLocations = his.read_his.ReadMetadata(os.path.join(caseDir,'calcpnt.his'), hia_file='auto').GetLocations()
                    for reach in networkGR.read().split('GRID')[1:]:
                        ident = between(reach, "id '","' ci")
                        line = self.cases[case]['topology']['reaches'][ident]['lineString']
                        gridTable = between(reach, 'TBLE\n',' <\ntble').split(' <\n')
                        for idx, grid in enumerate(gridTable):
                            grid = grid.split()
                            hPoint = grid[3].replace("'","")
                            if hPoint in hLocations: #check if point is ignored by Sobek-core
                                point = (float(grid[5]),float(grid[6]))
                                self.cases[case]['topology']['calcGrid']['HPoints'].update({hPoint:{'point':point}})
                                if idx == 0:
                                    Vpoint = grid[4].replace("'","")
                                    Type = self.cases[case]['topology']['network'][Vpoint]['properties']['type']
                                    customType = self.cases[case]['topology']['network'][Vpoint]['properties']['customType']
                                    pointFrom = hPoint
                                else:
                                    pointTo = hPoint
                                    segment, line = split_line(LineString(line),Point(point),buffer=0.01)
                                    self.cases[case]['topology']['calcGrid']['reachSegments'].update({Vpoint:
                                        {'properties':{'type':Type,'customType':customType,'pointFrom':pointFrom,'pointTo':pointTo},'lineString':segment}})                  
                                    Vpoint = grid[4].replace("'","") 
                                    pointFrom = hPoint
                            

    # export reaches       
    def export_reaches(self,case,reachesFile,driver='ESRI Shapefile'):
        if self.cases[case]['topology']['reaches'] == None: self.set_reaches(case)
        schema = {'geometry': 'LineString','properties': {'ID':'str'},}
        crs = self.cases[case]['crs']
        with fiona.open(reachesFile, 'w',crs={'init': crs}, driver=driver, schema=schema) as file:
            for ident in list(self.cases[case]['topology']['reaches'].keys()):
                file.write({'geometry':mapping(LineString(self.cases[case]['topology']['reaches'][ident]['lineString'])),'properties': {'ID':ident},})
    
    # export network
    def export_network(self,case,networkFile,driver='ESRI Shapefile'):
        if self.cases[case]['topology']['network'] == None: self.set_network(case)
        schema = {'geometry': 'LineString','properties': {'ID':'str','type':'str','customType':'str','startNode':'str','endNode':'str'},}
        crs = self.cases[case]['crs']
        with fiona.open(networkFile, 'w',crs={'init': crs}, driver=driver, schema=schema) as file:
            for ident in list(self.cases[case]['topology']['network'].keys()):
                properties = {'ID':ident}
                properties.update(self.cases[case]['topology']['network'][ident]['properties'])
                file.write({'geometry':mapping(LineString(self.cases[case]['topology']['network'][ident]['lineString'])),'properties': 
                    properties,})
    
    # export reachSegments
    def export_reachSegments(self,case,segmentFile,driver='ESRI Shapefile'):
        if self.cases[case]['topology']['calcGrid']['reachSegments'] == None: self.set_calcGrid(case)
        schema = {'geometry': 'LineString','properties': {'ID':'str','type':'str','customType':'str','pointFrom':'str','pointTo':'str'},}
        crs = self.cases[case]['crs']
        with fiona.open(segmentFile, 'w',crs={'init': crs}, driver=driver, schema=schema) as file:
            for ident in list(self.cases[case]['topology']['calcGrid']['reachSegments'].keys()):
                properties = {'ID':ident}
                properties.update(self.cases[case]['topology']['calcGrid']['reachSegments'][ident]['properties'])
                file.write({'geometry':mapping(LineString(self.cases[case]['topology']['calcGrid']['reachSegments'][ident]['lineString'])),'properties': 
                    properties,})
    
    def export_HPoints(self,case,PointFile,driver='ESRI Shapefile'):
        if self.cases[case]['topology']['calcGrid']['HPoints'] == None: self.set_calcGrid(case)
        schema = {'geometry': 'Point','properties': {'ID':'str'},}
        crs = self.cases[case]['crs']
        with fiona.open(PointFile, 'w',crs={'init': crs}, driver=driver, schema=schema) as file:
            for ident in list(self.cases[case]['topology']['calcGrid']['HPoints'].keys()):
                properties = {'ID':ident}
                file.write({'geometry':mapping(Point(self.cases[case]['topology']['calcGrid']['HPoints']['point'])),'properties': 
                    properties,})

    
def test(sobekDir, case, folder):        
    project = sobek(sobekDir)
    project.set_case(case)
    project.export_reaches(case,os.path.join(folder,'reaches.shp'))
    project.export_network(case,os.path.join(folder,'network.shp'))
    project.export_reachSegments(case,os.path.join(folder,'reachSegments.shp'))
    project.export_HPoints(case,os.path.join(folder,'Hpoints.shp'))

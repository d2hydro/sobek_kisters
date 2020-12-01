# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 12:38:16 2019

@author: danie
"""

#%%
from pathlib import Path
from sobek import project
import geopandas as gpd
import pandas as pd
import hkvsobekpy as his
import re

lit_dir = Path(r'c:\SK215003\Tol_inun.lit')
sbk_case = '20201127 Geaggregeerd Model 0D1D 2013 KNMI Tertiair met Flush GEKALIBREERD'
kisters_name = 'de-tol'

sbk_project = project.Project(lit_dir)
sbk_project.drop_cache()
sbk_cases = sbk_project.get_cases()
sbk_case = sbk_project[sbk_case]

#%% toevoegen parameters

#kunstwerken
boezempeil = -0.4
sbk_case.parameters.structures['G2901']['dh'] = boezempeil - -2.05
sbk_case.parameters.structures['G2901p2']['dh'] = boezempeil - -2.05
sbk_case.parameters.structures['I0982']['hds'] = -1.85
sbk_case.parameters.structures['I1284']['hds'] = -1.9
sbk_case.parameters.structures['I0424']['hds'] = -1.85
sbk_case.parameters.structures['I0025']['hds'] = -1.85
sbk_case.parameters.structures['I0417']['hds'] = -1.85
sbk_case.parameters.structures['I0027']['hds'] = -1.75
sbk_case.parameters.structures['I0026']['hds'] = -1.75
sbk_case.parameters.structures['I0418']['hds'] = -1.8
sbk_case.parameters.structures['I0024']['hds'] = -1.8
sbk_case.parameters.structures['I1486']['hds'] = -1.8
sbk_case.parameters.structures['I0812']['hds'] = -1.9
sbk_case.parameters.structures['I0809']['hds'] = -0.67
sbk_case.parameters.structures['I0029']['hds'] = -0.67
sbk_case.parameters.structures['I0804']['hds'] = -2.05
sbk_case.parameters.structures['I2075']['hds'] = -1.70
sbk_case.parameters.structures['I6175']['hds'] = -1.70

for structure, parameters in sbk_case.parameters.structures.items():
    if parameters['type'] == 'orifice':
        parameters['opening_height'] = 0.5
        parameters['hus'] = boezempeil
    #geef stuwen met PID controllers een min & max waarde mee
    if parameters['type'] == 'weir':
        if structure in sbk_case.control.keys():
            if sbk_case.control[structure]['type'] == 'PID':
                parameter = sbk_case.control[structure]['parameter']
                parameters[f'max_{parameter}'] = sbk_case.control[structure]['max_value']
                parameters[f'min_{parameter}'] = sbk_case.control[structure]['min_value']
#%%
#initiele conditie op nodes
def get_node_init(row,default=-1.8):
    '''apply-functie voor het toekennen van intiele conditie uit resultaten'''
    if row['ID'] in df[wl_param].columns:
        try:
            return df[wl_param][row['ID']][0]
        except:
            df[wl_param][row['ID']].iloc[0][0]
    else:
        print(f'{row["ID"]} not in calcpnt.his')
        return default
    
#initiele conditie op nodes
def get_link_init(row,default=-1.8):
    '''apply-functie voor het toekennen van intiele conditie uit resultaten'''
    if row['ID'] in df.index:
        return df.loc[row['ID']][6]
    else:
        print(f'{row["ID"]} not in initial.dat')
        return default   

wl_param = next((param for param in sbk_case.results.points['parameters'] 
                 if re.match('Waterl.', param)), None)

if wl_param:
    his_file = his.read_his.ReadMetadata(sbk_case.path.joinpath('calcpnt.his'))
    df = his_file.DataFrame()
    sbk_case.network.nodes['initial_level'] = sbk_case.network.nodes.apply(get_node_init,axis=1)  
else:
    print('cannot read waterlevel from results')

init_date_time = df[wl_param].index[0]
    
#initiele conditie op links
df = pd.read_csv(sbk_case.path.joinpath('INITIAL.DAT'), 
                 skiprows=1, 
                 header=None, 
                 sep=None,
                 engine='python')

df.index = [value.replace("'",'') for value in df[2].values]

sbk_case.network.links['initial_level'] = sbk_case.network.links.apply(get_link_init,axis=1) 
   


#%% upload to kisters network store
link_classes = {'SBK_PUMP': 'Pump',
                'SBK_WEIR': 'Weir',
                'SBK_ORIFICE': 'FlowControlledStructure'}

rto_network = sbk_case.to_kisters(name = kisters_name,
                                  link_classes = link_classes,
                                  prefix='a',
                                  initials=False)
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 12:38:16 2019

@author: danie
"""

#%%
from pathlib import Path
from sobek import project
import pandas as pd
import geopandas as gpd
import pandas as pd
import hkvsobekpy as his
import re

pd.options.mode.chained_assignment = None

lit_dir = Path(r'c:\SK215003\Tol_inun.lit')
sbk_case = '20201127 Geaggregeerd Model 0D1D 2013 KNMI Tertiair met Flush GEKALIBREERD'
kisters_name = 'de-tol'
sbk_project = project.Project(lit_dir)
sbk_cases = sbk_project.get_cases()
sbk_case = sbk_project[sbk_case]

#%% linken lateralen aan ds node
laterals_df = sbk_case.network.objects.loc[sbk_case.network.objects['TYPE'] == 'SBK_SBK-3B-REACH']
links_df = sbk_case.network.links
laterals_df['TO_NODE'] = laterals_df.apply((lambda x:links_df.loc[x['LINK']]['TO_NODE']),axis=1)

#%%
laterals_grouper = laterals_df.groupby('TO_NODE')
his_file = his.read_his.ReadMetadata(sbk_case.path.joinpath('BNDFLODT.HIS'))
param = next((par for par in his_file.GetParameters() if re.match('Flow.',par)), None)
sbk_bound_ts_df = his_file.DataFrame()[param]

flow_bound = {'id':[],
              'time_series':[]}

for lateral, df in laterals_grouper:
    flow_bound['id'] += [lateral]
    flow_bound['time_series'] += [sbk_bound_ts_df[df['ID'].values].sum(axis=1)]
    
flow_bound_df = pd.DataFrame(flow_bound)
flow_bound_df.index = flow_bound_df['id']
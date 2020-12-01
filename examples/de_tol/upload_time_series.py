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
from kisters.water.time_series.tsa import TSAStore

pd.options.mode.chained_assignment = None
prefix = 'a'
boezempeil = -0.4

store = TSAStore("https://hdsr-detol-tsa.water.kisters.cloud/")

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

#%% lateralen uploaden
laterals_grouper = laterals_df.groupby('TO_NODE')
his_file = his.read_his.ReadMetadata(sbk_case.path.joinpath('BNDFLODT.HIS'))
param = next((par for par in his_file.GetParameters() if re.match('Flow.',par)), None)
sbk_bound_ts_df = his_file.DataFrame()[param]

for lateral, df in laterals_grouper:
    print(lateral)
    ts = store.create_time_series(f'{prefix}{lateral}/flow.historical')
    df = pd.DataFrame(sbk_bound_ts_df[df['ID'].values].sum(axis=1), columns = ['value'])
    ts.write_data_frame(df)

#%% boezempeil uploaden
df['value'] = boezempeil

for boundary in sbk_case.boundaries.flow.index:
    ts = store.create_time_series(f'{prefix}{boundary}/level.historical')
    ts.write_data_frame(df)
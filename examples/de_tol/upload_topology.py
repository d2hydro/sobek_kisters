# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 12:38:16 2019

@author: danie
"""

#%%
from pathlib import Path
from sobek import project

lit_dir = Path(r'c:\SK215003\Tol_inun.lit')
sbk_case = '20201106 Geaggregeerd Model 0D1D'
kisters_name = 'de-tol'


sbk_project = project.Project(lit_dir)
sbk_project.drop_cache()
sbk_cases = sbk_project.get_cases()
sbk_case = sbk_project[sbk_case]


#%% upload to kisters network store
rto_network = sbk_case.to_kisters(kisters_name)
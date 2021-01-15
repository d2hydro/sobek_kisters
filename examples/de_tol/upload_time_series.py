# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 12:38:16 2019

@author: danie
"""

#%%
from pathlib import Path
from sobek import project
from datetime import timezone, timedelta
import pandas as pd
import geopandas as gpd
import pandas as pd
import hkvsobekpy as his
import re
from kisters.water.time_series.tsa import TSAStore

import nest_asyncio

from config import(
    LIT_DIR,
    CASE_NAME,
    KISTERS_NAME,
    DATA_DIR,
    CLIENT_ID,
    CLIENT_SECRET)

nest_asyncio.apply()

pd.options.mode.chained_assignment = None
prefix = "a"
boezempeil = -0.4

store = TSAStore("https://hdsr-detol-tsa.water.kisters.cloud/")

lit_dir = LIT_DIR
sbk_case = CASE_NAME
kisters_name = KISTERS_NAME
sbk_project = project.Project(lit_dir)
sbk_cases = sbk_project.get_cases()
sbk_case = sbk_project[sbk_case]

#%% linken lateralen aan ds node
laterals_df = sbk_case.network.objects.loc[
    sbk_case.network.objects["TYPE"] == "SBK_SBK-3B-REACH"
]
links_df = sbk_case.network.links
laterals_df["TO_NODE"] = laterals_df.apply(
    (lambda x: links_df.loc[x["LINK"]]["TO_NODE"]), axis=1
)

#%% lateralen uploaden
laterals_grouper = laterals_df.groupby("TO_NODE")
his_file = his.read_his.ReadMetadata(sbk_case.path.joinpath("bndflodt.his"))
param = next((par for par in his_file.GetParameters() if re.match("Flow.", par)), None)
sbk_bound_ts_df = his_file.DataFrame()[param]


def get_ts(path):
    try:
        ts = store.get_by_path(path)
    except KeyError:
        ts = store.create_time_series(path)
    return ts


for lateral, df in laterals_grouper:
    path = f"mongo({prefix}{lateral}/flow.historical)"
    ts = get_ts(path)
    df = pd.DataFrame(sbk_bound_ts_df[df["ID"].values].sum(axis=1), columns=["value"])
    df.index = df.index.tz_localize(timezone(timedelta(hours=1)))
    ts.write_data_frame(df)

#%% boezempeil uploaden
df["value"] = boezempeil

for boundary in sbk_case.boundaries.flow.index:
    ts = get_ts(f"mongo({prefix}{boundary}/level.historical)")
    ts.write_data_frame(df)


# simulatiedata uploaden
mapping = {
    "Discharge mean(m³/s)": "flow",
    "Crest level mean (m AD)": "crest.level",
}


for loc in sbk_case.results.structures["locations"]:
    for q_in, q_out in mapping.items():
        path = f"mongo({prefix}{loc}/{q_out}.historical)"
        print(path)
        ts = get_ts(path)
        df = sbk_case.results.structures["df"][q_in][loc]
        df.index = df.index.tz_localize(timezone(timedelta(hours=1)))
        ts.write_data_frame(df)


mapping = {
    "Waterlevel mean (m AD)": "level",
    "Lateral Flow at Node (m3/s)": "flow",
}

for loc in sbk_case.results.points["locations"]:
    for q_in, q_out in mapping.items():
        path = f"mongo({prefix}{loc}/{q_out}.historical)"
        print(path)
        ts = get_ts(path)
        df = sbk_case.results.points["df"][q_in][loc]
        if isinstance(df, pd.DataFrame):
            df = df.iloc[:, 0]
        df.index = df.index.tz_localize(timezone(timedelta(hours=1)))
        ts.write_data_frame(df)


mapping = {
    "Discharge mean(m³/s)": "flow",
}

for loc in sbk_case.results.links["locations"]:
    for q_in, q_out in mapping.items():
        loc_rto = "_".join(loc.split("_")[:-1])
        path = f"mongo({prefix}{loc_rto}/{q_out}.historical)"
        print(path)
        ts = get_ts(path)
        df = sbk_case.results.links["df"][q_in][loc]
        if isinstance(df, pd.DataFrame):
            df = df.iloc[:, 0]
        df.index = df.index.tz_localize(timezone(timedelta(hours=1)))
        ts.write_data_frame(df)

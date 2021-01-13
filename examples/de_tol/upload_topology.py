# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 12:38:16 2019

@author: danie
"""

#%%
from pathlib import Path
from sobek import project
import geopandas as gpd
import numpy as np
import pandas as pd
import hkvsobekpy as his
from shapely.geometry import Point
import re
import json

lit_dir = Path(r"/home/jbaayen/Downloads/tol_inun.lit")
sbk_case = "20210104 Geaggregeerd Model 0D1D OPTIMALISATIE OWD"
kisters_name = "de-tol"
data_dir = Path("data")
time_controller_min_value_offset = (
    -0.25
)  # Subtract 25 cm from min_crest_levels obtained from time controllers

sbk_project = project.Project(lit_dir)
sbk_project.drop_cache()
sbk_cases = sbk_project.get_cases()
sbk_case = sbk_project[sbk_case]

#%% toevoegen parameters

# kunstwerken
boezempeil = -0.4
sbk_case.parameters.structures["G2901"]["dh"] = boezempeil - -2.05
sbk_case.parameters.structures["G2901p2"]["dh"] = boezempeil - -2.05
sbk_case.parameters.structures["I0982"]["hds"] = -1.85
sbk_case.parameters.structures["I1284"]["hds"] = -1.9
sbk_case.parameters.structures["I0424"]["hds"] = -1.85
sbk_case.parameters.structures["I0025"]["hds"] = -1.85
sbk_case.parameters.structures["I0417"]["hds"] = -1.85
sbk_case.parameters.structures["I0027"]["hds"] = -1.75
sbk_case.parameters.structures["I0026"]["hds"] = -1.75
sbk_case.parameters.structures["I0418"]["hds"] = -1.8
sbk_case.parameters.structures["I0024"]["hds"] = -1.8
sbk_case.parameters.structures["I1486"]["hds"] = -1.8
sbk_case.parameters.structures["I0812"]["hds"] = -1.9
sbk_case.parameters.structures["I0809"]["hds"] = -0.67
sbk_case.parameters.structures["I0029"]["hds"] = -0.67
sbk_case.parameters.structures["I0804"]["hds"] = -2.05
sbk_case.parameters.structures["I2075"]["hds"] = -1.70
sbk_case.parameters.structures["I6175"]["hds"] = -1.70

for structure, parameters in sbk_case.parameters.structures.items():
    if parameters["type"] == "orifice":
        parameters["opening_height"] = 0.5
        parameters["hus"] = boezempeil
    # geef stuwen met PID controllers een min & max waarde mee
    if parameters["type"] == "weir":
        if structure in sbk_case.control.keys():
            if sbk_case.control[structure]["type"] == "PID":
                parameter = sbk_case.control[structure]["parameter"]
                parameters[f"max_{parameter}"] = sbk_case.control[structure][
                    "max_value"
                ]
                parameters[f"min_{parameter}"] = sbk_case.control[structure][
                    "min_value"
                ]
            elif sbk_case.control[structure]["type"] == "time":
                parameter = sbk_case.control[structure]["parameter"]
                parameters[f"max_{parameter}"] = sbk_case.control[structure][
                    "max_value"
                ]
                parameters[f"min_{parameter}"] = (
                    sbk_case.control[structure]["min_value"]
                    + time_controller_min_value_offset
                )
#%%
# initiele conditie op nodes
def get_node_init(row, default=-1.8):
    """apply-functie voor het toekennen van intiele conditie uit resultaten"""
    if row["ID"] in df[wl_param].columns:
        try:
            return df[wl_param][row["ID"]][0]
        except:
            df[wl_param][row["ID"]].iloc[0][0]
    else:
        print(f'{row["ID"]} not in calcpnt.his')
        return default


# initiele conditie op nodes
def get_link_init(row, default=-1.8):
    """apply-functie voor het toekennen van intiele conditie uit resultaten"""
    if row["ID"] in df.index:
        return df.loc[row["ID"]][12]
    else:
        print(f'{row["ID"]} not in initial.dat')

        return default

wl_param = next(
    (
        param
        for param in sbk_case.results.points["parameters"]
        if re.match("Waterl.", param)
    ),
    None,
)

if wl_param:
    his_file = his.read_his.ReadMetadata(sbk_case.path.joinpath("calcpnt.his"))
    df = his_file.DataFrame()
    sbk_case.network.nodes["initial_level"] = sbk_case.network.nodes.apply(
        get_node_init, axis=1
    )
else:
    print("cannot read waterlevel from results")

init_date_time = df[wl_param].index[0]

# initiele conditie op links
df = pd.read_csv(
    sbk_case.path.joinpath("initial.dat"),
    skiprows=1,
    header=None,
    sep=None,
    engine="python",
)

df.index = [value.replace("'", "") for value in df[2].values]

sbk_case.network.links["initial_level"] = sbk_case.network.links.apply(
    get_link_init, axis=1
)
sbk_case.network.links['initial_flow'] = 0
sbk_case.network.nodes['initial_flow'] = 0

#%% upload to kisters network store
link_classes = {
    "SBK_PUMP": "Pump",
    "SBK_WEIR": "Weir",
    "SBK_ORIFICE": "FlowControlledStructure",
}

groups = json.load(open(data_dir.joinpath("groups.json")))
sbk_case.network.nodes["group"] = None
sbk_case.network.links["group"] = None

#%%
for group in groups:
    # set us/ds nodes to group-id
    sbk_case.network.nodes.loc[
        [val for key, val in group.items() if key in ["us_node", "ds_node"]], "group"
    ] = group["uid"]

    # now find all nodes and links in between
    ds_found = False
    us_node = group["us_node"]
    while not ds_found:
        # set upstream node and link
        sbk_case.network.links.loc[
            sbk_case.network.links["FROM_NODE"] == us_node, "group"
        ] = group["uid"]
        sbk_case.network.nodes.loc[us_node, "group"] = group["uid"]
        ds_nodes = list(
            sbk_case.network.links.loc[
                sbk_case.network.links["FROM_NODE"] == us_node, "TO_NODE"
            ].unique()
        )
        if group["ds_node"] in ds_nodes:
            ds_found = True
            # sbk_case.network.nodes.loc[ds_nodes[0], 'group'] = group['uid']
        else:
            if len(ds_nodes) == 1:
                us_node = ds_nodes[0]
            else:
                print("more than 1 ds node, this goes wrong!")
    #%%
    nodes = (
        sbk_case.network.nodes.to_crs(epsg="3857")
        .loc[
            [val for key, val in group.items() if key in ["us_node", "ds_node"]],
            "geometry",
        ]
        .values
    )
    node = Point((nodes[0].x + nodes[1].x) / 2, (nodes[0].y + nodes[1].y) / 2)
    group["schematic_location"] = {"x": node.x, "y": node.y, "z": 0.0}
    group["location"] = {"x": node.x, "y": node.y, "z": 0.0}

# #%%
rto_network = sbk_case.to_kisters(
    name=kisters_name,
    link_classes=link_classes,
    prefix="a",
    initials=True,
    rto_groups=groups,
    hydraulic_routing_model="inertial-wave",
)

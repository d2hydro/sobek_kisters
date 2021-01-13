# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 14:15:46 2019

@author: danie
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point
import os
import re
import numpy as np
import hkvsobekpy as his
import csv

#%%
def __between(value, a, b):
    # Find and validate before-part.
    pos_a = value.find(a)
    if pos_a == -1:
        return ""
    # Find and validate after part.
    pos_b = value.rfind(b)
    if pos_b == -1:
        return ""
    # Return middle part.
    adjusted_pos_a = pos_a + len(a)
    if adjusted_pos_a >= pos_b:
        return ""
    return value[adjusted_pos_a:pos_b]


def __split_line(lineString, point, buffer=False):
    if not buffer:
        pointIntersect = point
    else:
        pointIntersect = point.buffer(buffer)
    coords = lineString.coords
    j = None
    for i in range(len(coords) - 1):
        if LineString(coords[i : i + 2]).intersects(pointIntersect):
            j = i
            break
    assert j is not None
    # Make sure to always include the point in the first group
    return (
        coords[: j + 1] + [Point(point).coords[0]],
        [Point(point).coords[0]] + coords[j + 1 :],
    )


__friction_models = {
    "0": "chezy",
    "1": "manning",
    "2": "strickler (kn)",
    "3": "strickler (ks)",
    "4": "white-colebrook",
    "7": "bos and bijkerk",
}

__flow_boundary_types = {"0": "waterlevel", "1": "discharge"}

__structure_types = {"6": "weir", "7": "orifice", "9": "pump"}

__structure_flow_dirs = {"0": "both", "1": "positive", "2": "negative", "3": "no_flow"}

__pump_control = {"1": "suction", "2": "delivery", "3": "both_sides"}

__control_types = {"0": "time", "1": "hydraulic", "2": "interval", "3": "PID"}

__control_param = {
    "0": "crest_level",
    "1": "crest_width",
    "2": "gate_height",
    "3": "pump_capacity",
}

__profile_types = {}

__match_num = "[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?"

#%% read network
def network(path, crs):
    links = gpd.GeoDataFrame(
        columns=["ID", "FROM_NODE", "TO_NODE", "geometry"], geometry="geometry"
    )
    nodes = gpd.GeoDataFrame(columns=["ID", "geometry"], geometry="geometry")

    with open(os.path.join(path, "network.tp"), "r") as networkTP:
        for line in networkTP.readlines():
            if line[0:4] == "NODE":
                ident = __between(line, "id '", "' nm")
                x = float(__between(line, "px ", " py"))
                y = float(__between(line, "py ", " node"))
                nodes = nodes.append(
                    {"ID": ident, "geometry": Point(x, y)}, ignore_index=True
                )
            elif line[0:4] == "BRCH":
                ident = __between(line, "id '", "' nm")
                from_node = __between(line, "bn '", "' en")
                to_node = __between(line, "en '", "' al")
                links = links.append(
                    {"ID": ident, "FROM_NODE": from_node, "TO_NODE": to_node},
                    ignore_index=True,
                )

    # open network.cp to define channel geometry
    with open(os.path.join(path, "network.cp"), "r") as networkCP:
        for reach in networkCP.read().split("BRCH")[1:]:
            ident = __between(reach, "id '", "' cp")
            cps = __between(reach, "TBLE\n", " <\ntble").split(" <\n")
            from_node = list(links.loc[links["ID"] == ident, "FROM_NODE"])[0]
            to_node = list(links.loc[links["ID"] == ident, "TO_NODE"])[0]
            coord_list = list(
                list(nodes.loc[nodes["ID"] == from_node].geometry)[0].coords
            )
            sumDistance = 0.0
            for idx, cp in enumerate(cps):
                distance, angle = cp.split()
                distance = (float(distance) - sumDistance) * 2
                angle = np.deg2rad(90 - float(angle))
                x = coord_list[-1][0] + float(distance) * np.cos(angle)
                y = coord_list[-1][1] + float(distance) * np.sin(angle)
                coord_list += [(x, y)]
                sumDistance += distance
            coord_list[-1] = list(
                list(nodes.loc[nodes["ID"] == to_node].geometry)[0].coords
            )[0]
            index = links.loc[links["ID"] == ident].index[0]
            links.at[index, "geometry"] = LineString(coord_list)

    network = {}
    objects = gpd.GeoDataFrame(
        columns=["ID", "TYPE", "LINK", "LINK_POS", "geometry"],
        geometry="geometry",
        crs=crs,
    )
    objects_list = []
    with open(os.path.join(path, "network.ntw"), "r") as networkNTW:
        doLinks = True
        for idx, l in enumerate(
            csv.reader(
                networkNTW.readlines(),
                quotechar='"',
                delimiter=",",
                quoting=csv.QUOTE_ALL,
            )
        ):
            if idx > 0:
                if doLinks:
                    if l[0] == "*":
                        doLinks = False
                if doLinks:
                    network.update(
                        {
                            l[0]: {
                                "properties": {
                                    "type": l[4],
                                    "customType": l[5],
                                    "startNode": l[14],
                                    "endNode": l[27],
                                },
                                "lineString": [
                                    [float(l[21]), float(l[22])],
                                    [float(l[34]), float(l[35])],
                                ],
                            }
                        }
                    )
                    if not l[14] in objects_list:
                        objects_list.append(l[14])
                        objects = objects.append(
                            {
                                "ID": l[14],
                                "NAME": l[15],
                                "TYPE": l[19],
                                "geometry": Point([float(l[21]), float(l[22])]),
                            },
                            ignore_index=True,
                        )
                    if not l[27] in objects_list:
                        objects_list.append(l[27])
                        objects = objects.append(
                            {
                                "ID": l[27],
                                "NAME": l[28],
                                "TYPE": l[32],
                                "geometry": Point([float(l[34]), float(l[35])]),
                            },
                            ignore_index=True,
                        )

    h_points = gpd.GeoDataFrame(
        columns=["ID", "geometry"], geometry="geometry", crs=crs
    )
    v_links = gpd.GeoDataFrame(
        columns=["ID", "TYPE", "CUSTOM_TYPE", "FROM_NODE", "TO_NODE", "geometry"],
        geometry="geometry",
        crs=crs,
    )

    with open(os.path.join(path, "network.gr"), "r") as networkGR:
        hLocations = his.read_his.ReadMetadata(
            os.path.join(path, "calcpnt.his"), hia_file="auto"
        ).GetLocations()
        for reach in networkGR.read().split("GRID")[1:]:
            ident = __between(reach, "id '", "' ci")
            line = list(links.loc[links["ID"] == ident, "geometry"])[0]
            gridTable = __between(reach, "TBLE\n", " <\ntble").split(" <\n")
            for idx, grid in enumerate(gridTable):
                grid = grid.split()
                h_point = grid[3].replace("'", "")
                if h_point in hLocations:  # check if point is ignored by Sobek-core
                    point = (float(grid[5]), float(grid[6]))
                    if not h_point in list(h_points["ID"]):
                        h_points = h_points.append(
                            {"ID": h_point, "geometry": Point(point)}, ignore_index=True
                        )
                    if idx == 0:
                        v_point = grid[4].replace("'", "")
                        Type = network[v_point]["properties"]["type"]
                        customType = network[v_point]["properties"]["customType"]
                        pointFrom = h_point
                    else:
                        pointTo = h_point
                        segment, line = __split_line(
                            LineString(line), Point(point), buffer=0.01
                        )
                        v_links = v_links.append(
                            {
                                "ID": v_point,
                                "TYPE": Type,
                                "CUSTOM_TYPE": customType,
                                "FROM_NODE": pointFrom,
                                "TO_NODE": pointTo,
                                "geometry": LineString(segment),
                            },
                            ignore_index=True,
                        )
                        v_point = grid[4].replace("'", "")
                        pointFrom = h_point

    # use ID as index
    for df in [links, nodes, objects, v_links]:
        df.index = df["ID"]

    with open(os.path.join(path, "network.cr"), "r") as networkCR:
        for line in networkCR:
            if re.match("CRSN", line):
                object_id = re.search(".id '(.*)' nm.", line).group(1)
                objects.loc[object_id, "LINK"] = re.search(".ci '(.*)' lc", line).group(
                    1
                )
                objects.loc[object_id, "LINK_POS"] = float(
                    re.search(".lc (.*) crsn", line).group(1)
                )

    with open(os.path.join(path, "network.st"), "r") as networkST:
        for line in networkST:
            if re.match("STRU", line):
                object_id = re.search(".id '(.*)' nm.", line).group(1)
                objects.loc[object_id, "LINK"] = re.search(".ci '(.*)' lc", line).group(
                    1
                )
                objects.loc[object_id, "LINK_POS"] = float(
                    re.search(".lc (.*) stru", line).group(1)
                )

    with open(os.path.join(path, "network.cn"), "r") as networkCN:
        for line in networkCN:
            if re.match("FLBX", line):
                object_id = re.search(".id '(.*)' nm.", line).group(1)
                objects.loc[object_id, "LINK"] = re.search(".ci '(.*)' lc", line).group(
                    1
                )
                objects.loc[object_id, "LINK_POS"] = float(
                    re.search(".lc (.*) flbx", line).group(1)
                )

    return {
        "links": links.set_crs(crs, inplace=True),
        "nodes": nodes.set_crs(crs, inplace=True),
        "objects": objects.set_crs(crs, inplace=True),
        "segments": v_links.set_crs(crs, inplace=True),
    }


def results(path):
    files = {
        "links": "reachseg.his",
        "points": "calcpnt.his",
        "structures": "struc.his",
    }
    result = {"links": None, "points": None, "structures": None}
    for key, item in files.items():
        if os.path.exists(os.path.join(path, item)):
            meta_data = his.read_his.ReadMetadata(
                os.path.join(path, item), hia_file="auto"
            )
            parameters = meta_data.GetParameters()
            locations = meta_data.GetLocations()
            result.update(
                {
                    key: {
                        "df": meta_data.DataFrame(),
                        "parameters": parameters,
                        "locations": locations,
                    }
                }
            )

    return result


def parameters(path):
    """ function to read parameters from a sobek case"""
    result = dict()
    with path.joinpath("friction.dat").open() as friction_dat:
        result["friction"] = dict()
        for line in friction_dat:
            if re.match(".*BDFR.*",line):
                model = __friction_models[__between(line, 'mf',' mt').replace(' ','')]
                value = float(__between(line, 'mt cp 0','0 mr').replace(' ',''))
                result['friction']['global'] = {'model':model,
                                                'value':value}
    
    with path.joinpath('struct.dat').open() as struct_dat:
        structures = dict()
        for line in struct_dat:
            if re.match("STRU", line):
                struc_id = re.search(".id '(.*)' nm.", line).group(1)
                structures[struc_id] = {}
                structures[struc_id]["def_id"] = re.search(
                    ".dd '(.*)' ca.", line
                ).group(1)
                structures[struc_id]["control_id"] = re.search(
                    "cj '(.*)' ", line
                ).group(1)
                structures[struc_id]["control_active"] = bool(
                    int(re.search(f"ca ({__match_num}) ", line).group(1))
                )
        result["structures"] = structures

    with path.joinpath("struct.def").open() as struct_def:
        for stds in struct_def.read().split("stds"):
            if "STDS" in stds:
                def_id = re.search(".id '(.*)' nm.", stds).group(1)
                struc_def = dict()
                struc_def["type"] = __structure_types[
                    re.search(".ty ([0-9]).", stds).group(1)
                ]
                if struc_def["type"] in ["weir", "orifice"]:
                    struc_def["crest_level"] = float(
                        re.search(f".cl ({__match_num}).", stds).group(1)
                    )
                    struc_def["crest_width"] = float(
                        re.search(f".cw ({__match_num}).", stds).group(1)
                    )
                    struc_def["flow_dir"] = __structure_flow_dirs[
                        re.search(f".rt ({__match_num}).", stds).group(1)
                    ]
                    if struc_def["type"] == "weir":
                        cw = float(re.search(f".sc ({__match_num}).", stds).group(1))
                        ce = float(re.search(f".ce ({__match_num}).", stds).group(1))
                        struc_def["coefficient"] = ce * cw

                    if struc_def["type"] == "orifice":
                        cw = float(re.search(f".sc ({__match_num}).", stds).group(1))
                        mu = float(re.search(f".mu ({__match_num}).", stds).group(1))
                        struc_def["coefficient"] = mu * cw
                elif struc_def["type"] == "pump":
                    struc_def["control_side"] = __pump_control[
                        re.search(f".dn ({__match_num}).", stds).group(1)
                    ]
                    stages = (
                        re.search(".*\nTBLE\n(.*)<\ntble.", stds).group(1).split("<")
                    )
                    stages = [stage.split() for stage in stages]
                    struc_def["pump_stages"] = [
                        {
                            "capacity": float(stage[0]),
                            "suction_on": float(stage[1]),
                            "suction_off": float(stage[2]),
                            "delivery_on": float(stage[3]),
                            "delivery_off": float(stage[4]),
                        }
                        for stage in stages
                    ]

                struc_id = next(
                    (
                        st_id
                        for st_id, values in structures.items()
                        if values["def_id"] == def_id
                    ),
                    None,
                )
                if struc_id:
                    result["structures"][struc_id] = {
                        **result["structures"][struc_id],
                        **struc_def,
                    }
                else:
                    print(f"structure definition {def_id} not linked to structure-id")

        with path.joinpath("profile.dat").open() as profile_dat:
            cross_sections = dict()
            for line in profile_dat:
                if re.match("CRSN", line):
                    xs_id = re.search(".id '(.*)' di.", line).group(1)
                    cross_sections[xs_id] = re.search(".di '(.*)' rl.", line).group(1)
            result["cross_sections"] = cross_sections.copy()

        with path.joinpath("profile.def").open() as profile_dat:
            for crds in profile_dat.read().split("crds"):
                if "CRDS" in crds:
                    def_id = re.search(".id '(.*)' nm.", crds).group(1)
                    xs_type = re.search(f".ty ({__match_num}).", crds).group(1)
                    crds = crds.replace("\n", "")
                    coords = re.search(r".*TBLE(.*)<tble.", crds).group(1).split("<")
                    if xs_type == "0":
                        z = np.array([float(coord.split()[0]) for coord in coords])
                        w = np.array([float(coord.split()[1]) for coord in coords])
                        series = pd.Series(
                            data=np.concatenate([np.flip(z), z]),
                            index=np.concatenate([np.flip(-w / 2), w / 2]),
                        )
                    else:
                        print(f"ERROR: structure type {xs_type} not supported!")

                prof_ids = [
                    xs_id
                    for xs_id, xs_def in cross_sections.items()
                    if xs_def == def_id
                ]
                if prof_ids:
                    for prof_id in prof_ids:
                        result["cross_sections"][prof_id] = series.copy()
                else:
                    print(f"profile definition {def_id} not linked to profile-id")

    return result


def control(path):
    """ function to read controls from a sobek case"""
    result = dict()
    with path.joinpath("control.def").open() as control_def:
        for cntl in control_def.read().split("cntl"):
            if "CNTL" in cntl:
                cntl_def = {}
                def_id = re.search(".id '(.*)' nm.", cntl).group(1)
                cntl_def["type"] = __control_types[
                    re.search(f".ct ({__match_num}).", cntl).group(1)
                ]
                cntl_def["parameter"] = __control_param[
                    re.search(f".ca ({__match_num}).", cntl).group(1)
                ]
                if cntl_def["type"] == "PID":
                    cntl_def["min_value"] = float(
                        re.search(f".ui ({__match_num}) ", cntl).group(1)
                    )
                    cntl_def["max_value"] = float(
                        re.search(f".ua ({__match_num}) ", cntl).group(1)
                    )
                elif cntl_def["type"] == "time":
                    crest_levels = []
                    for cntl_line in cntl.splitlines():
                        if "<" in cntl_line:
                            crest_levels.append(float(cntl_line.split(" ")[1]))
                    if len(crest_levels) > 0:
                        cntl_def["min_value"] = np.min(crest_levels)
                        cntl_def["max_value"] = np.max(crest_levels)
                tble_str = cntl.replace("\n", "")
                if "TBLE" in tble_str:
                    cntl_def["table"] = {}
                    tbl_props = re.findall("PDIN (.*) pdin", tble_str)
                    if len(tbl_props) > 0:
                        tbl_props = tbl_props[0].split()
                        cntl_def["table"]["function"] = tbl_props[0]
                        cntl_def["table"]["use_periodicity"] = bool(int(tbl_props[1]))
                        if cntl_def["table"]["use_periodicity"] == "1":
                            cntl_def["table"]["periodicity"] = tbl_props[2]
                    tble_list = (
                        re.search(r".*TBLE(.*)<tble.", tble_str).group(1).split("<")
                    )
                    date_time = [
                        pd.to_datetime(row.split()[0], format="'%Y/%m/%d;%H:%M:%S'")
                        for row in tble_list
                    ]
                    values = [float(row.split()[1]) for row in tble_list]
                    cntl_def["table"]["data"] = pd.Series(data=values, index=date_time)
                result[def_id] = cntl_def

    return result


def boundaries(path):
    """ function to read boundaries from a sobek case"""
    result = dict()
    with path.joinpath("boundary.dat").open() as boundary_dat:
        result["flow"] = dict()
        for line in boundary_dat:
            if re.match("FLBO", line):
                ident = __between(line, "id", "st").replace(" ", "").replace("'", "")
                result["flow"][ident] = {
                    "TYPE": __flow_boundary_types[
                        re.search(".ty ([0-9]).", line).group(1)
                    ]
                }
        result["flow"] = pd.DataFrame.from_dict(result["flow"], orient="index")

    return result
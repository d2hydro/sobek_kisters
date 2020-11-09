# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 12:38:16 2019

@author: danie
"""

from kisters.network_store.model_library.water import links, nodes
from kisters.network_store.client.network import Network
from kisters.water.rest_client import RESTClient
from kisters.water.rest_client.auth import OpenIDConnect


rest_server_url = "https://hdsr-detol-network.water.kisters.cloud/"


authentication = OpenIDConnect(
    client_id="hdsr-detol.operational.external.0D2EDE59",
    client_secret="3e7a9a06-33ea-4d2d-b46f-0348cf305a9f",
)

client = RESTClient(url=rest_server_url, authentication=authentication)
network = Network("sobek-test1", client, drop_existing=True)


channel = links.Channel(
    created="2019-06-27T16:53:05",
    uid="channel",
    source_uid="flow_boundary",
    target_uid="junction",
    display_name="channel",
    hydraulic_routing={
        "model": "saint-venant",
        "roughness_model": "chezy",
        "stations": [
            {
                "roughness": 10.0,
                "distance": 0.0,
                "cross_section": [
                    {"z": 0.0, "lr": -5.0},
                    {"z": 10.0, "lr": -5.0},
                    {"z": 0.0, "lr": 5.0},
                    {"z": 10.0, "lr": 5.0},
                ],
            }
        ],
    },
    length=100.0,
)

weir = links.Weir(
    created="2019-06-27T16:53:05",
    uid="weir",
    source_uid="junction",
    target_uid="level_boundary",
    display_name="weir",
    flow_model="free",
    coefficient=1.0,
    min_crest_level=0.0,
    max_crest_level=0.0,
    crest_width=10.0,
)

flow_boundary = nodes.FlowBoundary(
    created="2019-06-27T16:53:05",
    uid="flow_boundary",
    display_name="flow_boundary",
    location={"x": 0.0, "y": 0.0, "z": 0.0},
    schematic_location={"x": 0.0, "y": 0.0, "z": 0.0},
)
junction = nodes.Junction(
    created="2019-06-27T16:53:05",
    uid="junction",
    display_name="junction",
    location={"x": 0.0, "y": 1.0, "z": 0.0},
    schematic_location={"x": 0.0, "y": 1.0, "z": 0.0},
)
level_boundary = nodes.LevelBoundary(
    created="2019-06-27T16:53:05",
    uid="level_boundary",
    display_name="level_boundary",
    location={"x": 1.0, "y": 0.0, "z": 0.0},
    schematic_location={"x": 1.0, "y": 0.0, "z": 0.0},
)

network.save_nodes([flow_boundary, junction, level_boundary])
network.save_links([channel, weir])

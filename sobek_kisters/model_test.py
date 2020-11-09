# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 12:38:16 2019

@author: danie
"""

from kisters.water.hydraulic_network.client import (
    Network,
    OpenIDConnect,
    RESTClient,
)
import kisters.water.hydraulic_network.models.link as link
import kisters.water.hydraulic_network.models.node as node
from kisters.water.hydraulic_network.models import Metadata
import os
import fiona

import sobek


GIS_dir = os.path.abspath(r'GIS')
auth_config = {
    "client_id": "sobek-hydronet",
    "client_secret": "c93822c1-2e7e-4864-8f18-271c5674dcb0",
    "issuer_url": "https://auth.kisters.cloud/auth/realms/external",
}
rest_server_url = "http://hydraulic-network.kisters.eu.ngrok.io/"

authentication = OpenIDConnect(**auth_config)

client = RESTClient(url=rest_server_url, authentication=authentication)
network = Network("sobek-test1", client=client)

#%% build network

model = sobek.sobek(r'c:\SK215003\net_stor.lit')



#%% upload network


channel = link.Channel(created="2019-06-27T16:53:05",
        uid="channel",
        source_uid="flow_boundary",
        target_uid="junction",
        display_name="channel",
        cross_sections=[{"cross_section": [{"level": 0.0, "width": 10.0}, {"level": 10.0, "width": 10.0}]}],
        length=100.0,
        roughness=10.0,
        roughness_model="chezy",
        model="saint-venant")

weir = link.Weir(created="2019-06-27T16:53:05",
     uid="weir",
     source_uid="junction",
     target_uid="level_boundary",
     display_name="weir",
     model="free",
     coefficient=1.0,
     min_crest_level=0.0,
     max_crest_level=0.0,
     crest_width=10.0)

flow_boundary  = node.FlowBoundary(created="2019-06-27T16:53:05",
              uid="flow_boundary",
              display_name="flow_boundary",
              location={"x": 0.0, "y": 0.0, "z": 0.0},
              schematic_location={"x": 0.0, "y": 0.0, "z": 0.0})
junction = node.Junction(created="2019-06-27T16:53:05",
          uid="junction",
          display_name="junction",
          location={"x": 0.0, "y": 1.0, "z": 0.0},
          schematic_location={"x": 0.0, "y": 1.0, "z": 0.0})
level_boundary =  node.LevelBoundary(created="2019-06-27T16:53:05",
               uid="level_boundary",
               display_name="level_boundary",
               location={"x": 1.0, "y": 0.0, "z": 0.0},
               schematic_location={"x": 1.0, "y": 0.0, "z": 0.0})

network.initialize(nodes=[flow_boundary,junction,level_boundary],links=[channel,weir])
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 14:15:46 2019

@author: danie
"""

from kisters.network_store.model_library.water import links, nodes
from kisters.network_store.client.network import Network
from kisters.water.rest_client import RESTClient
from kisters.water.rest_client.auth import OpenIDConnect

#%% kisters client
rest_server_url = "https://hdsr-detol-network.water.kisters.cloud/"


authentication = OpenIDConnect(
    client_id="hdsr-detol.operational.external.0D2EDE59",
    client_secret="3e7a9a06-33ea-4d2d-b46f-0348cf305a9f",
)

client = RESTClient(url=rest_server_url, authentication=authentication)

_translate_boundary_class = {'waterlevel': 'LevelBoundary',
                             'discharge': 'FlowBoundary'}

#%% write to kisters
def kisters(sbk_case,name):
    sobek_network = sbk_case.network
    network = Network(name, client, drop_existing=True)
    
    def sbk_nodes(sobek_network):
        sbk_nodes = []
        for index, row in sobek_network.nodes.to_crs(epsg='3857').iterrows():
            if row['ID'] in sbk_case.boundaries.flow.index:
                node_type = getattr(nodes,
                                    _translate_boundary_class[sbk_case.boundaries.flow.loc['bndPG0394']['TYPE']])
            else:
                node_type = nodes.Junction
                
            x,y = row['geometry'].xy[0][0], row['geometry'].xy[1][0]
            ident = 'a{}'.format(row['ID']).replace('-','_')           
            sbk_nodes.append(node_type(
                            uid=ident,
                            display_name=row['ID'],
                            location={"x": x, "y": y, "z": 0.0},
                            schematic_location={"x": x, "y": y, "z": 0.0})
                            )
        return sbk_nodes
    
    def sbk_links(sobek_network):
        sbk_links = []
        for index, row in sobek_network.links.to_crs(epsg='3857').iterrows():
            x,y = row['geometry'].xy[0][0], row['geometry'].xy[1][0]
            sbk_links.append(links.Channel(
                            uid='a{}'.format(row['ID']).replace('-','_'),
                            source_uid='a{}'.format(row['FROM_NODE']).replace('-','_'),
                            target_uid='a{}'.format(row['TO_NODE']).replace('-','_'),
                            display_name=row['ID'],
                            hydraulic_routing={
                                "model": "saint-venant",
                                "roughness_model": "manning",
                                "stations":[
                                    {
                                     "roughness": 0.04,          #manning
                                     "distance": 0.0,
                                     "cross_section": [
                                            {"z": 0.0, "lr": -5.0}, #hier mag de yz definitie in
                                            {"z": 10.0, "lr": -5.0},
                                            {"z": 0.0, "lr": 5.0},
                                            {"z": 10.0, "lr": 5.0},
                                            ],
                                     }
                                    ],
                                },
                            length = row['geometry'].length,
                            )
                )
        
        return sbk_links
    
    network.save_nodes(sbk_nodes(sobek_network))
    network.save_links(sbk_links(sobek_network))
    return network
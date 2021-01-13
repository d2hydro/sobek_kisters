# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 14:15:46 2019

@author: danie
"""

from kisters.network_store.model_library.water import links, nodes, groups
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

_translate_boundary_class = {"waterlevel": "LevelBoundary", "discharge": "FlowBoundary"}

_translate_link_class = {
    "SBK_PUMP": "Pump",
    "SBK_WEIR": "Weir",
    "SBK_ORIFICE": "TopDownRectangularOrifice",
}

g = 9.81
rho = 977

#%% write to kisters
def kisters(
    sbk_case,
    name,
    link_classes,
    extra_params,
    prefix="",
    initials=False,
    rto_groups=None,
    hydraulic_routing_model="saint-venant",
):
    if link_classes:
        _translate_link_class = link_classes
    sobek_network = sbk_case.network
    lateral_links = sobek_network.objects.loc[
        (sobek_network.objects["TYPE"] == "SBK_SBK-3B-REACH")
    ]["LINK"]
    lateral_nodes = sobek_network.links.loc[
        sobek_network.links["ID"].isin(lateral_links)
    ]["TO_NODE"].values
    sobek_structures = sbk_case.network.objects.loc[
        sbk_case.network.objects["TYPE"].isin(["SBK_WEIR", "SBK_PUMP", "SBK_ORIFICE"])
    ]
    sobek_cross_sections = sbk_case.network.objects.loc[
        sbk_case.network.objects["TYPE"] == "SBK_PROFILE"
    ]
    network = Network(name, client, drop_existing=True)

    def sbk_nodes(sobek_network):
        rto_params = dict()
        sbk_nodes = []
        for index, row in sobek_network.nodes.to_crs(epsg="3857").iterrows():
            if row["ID"] in sbk_case.boundaries.flow.index:
                node_type = getattr(
                    nodes,
                    _translate_boundary_class[
                        sbk_case.boundaries.flow.loc[row['ID']]["TYPE"]
                    ],
                )
            elif row["ID"] in lateral_nodes:
                node_type = getattr(nodes, "FlowBoundary")
            else:
                node_type = nodes.Junction

            x, y = row["geometry"].xy[0][0], row["geometry"].xy[1][0]
            rto_params["location"] = {"x": x, "y": y, "z": 0.0}
            rto_params["schematic_location"] = {"x": x, "y": y, "z": 0.0}
            rto_params["uid"] = f'{prefix}{row["ID"]}'.replace("-", "_")
            rto_params["display_name"] = row["ID"]
            if rto_groups:
                if row["group"]:
                    rto_params["group_uid"] = row["group"]
                else:
                    rto_params = {key:value for key,value in rto_params.items() if not key == 'group_uid'}
            
            if initials:
                if node_type in ['Junction', 'FlowBoundary']:
                    rto_params['initial_level'] = row['initial_level']
                    if 'initial_flow' in rto_params.keys():
                        rto_params.pop('initial_flow')
                elif node_type == 'LevelBoundary':
                    rto_params['initial_flow'] = row['initial_flow']
                    if 'initial_level' in rto_params.keys():
                        rto_params.pop('initial_level')
            
            sbk_nodes += [getattr(nodes,node_type)(**rto_params)]
            
        return sbk_nodes

    def sbk_links(sobek_network):
        sbk_links = []
        for index, row in sobek_network.links.to_crs(epsg="3857").iterrows():
            link_id = row["ID"]
            rto_params = dict()
            rto_params["source_uid"] = f'{prefix}{row["FROM_NODE"].replace("-","_")}'
            rto_params["target_uid"] = f'{prefix}{row["TO_NODE"].replace("-","_")}'
            # rto_params['initial_level'] = row['initial_level']

            if link_id in sobek_structures["LINK"].values:
                structure = sobek_structures.loc[
                    sobek_structures["LINK"] == link_id
                ].iloc[0]
                link_id = structure["ID"]
                rto_params["display_name"] = structure["NAME"]
                structure_params = sbk_case.parameters.structures[link_id]
                link_type = _translate_link_class[structure["TYPE"]]

                if link_type == "Pump":
                    rto_params["min_flow"] = 0
                    rto_params["max_flow"] = max(
                        [stage["capacity"] for stage in structure_params["pump_stages"]]
                    )
                    rto_params["min_power"] = 0
                    rto_params["max_power"] = (
                        g * rho * rto_params["max_flow"] * structure_params["dh"]
                    )

                elif link_type in ["Weir", "TopDownRectangularOrifice"]:
                    rto_params["coefficient"] = structure_params["coefficient"]
                    rto_params["flow_model"] = "dynamic"

                    if link_type == "Weir":
                        rto_params["crest_width"] = structure_params["crest_width"]
                        assert rto_params["crest_width"] > 0
                        for param in ["min_crest_level", "max_crest_level"]:
                            if param in structure_params.keys():
                                rto_params[param] = structure_params[param]
                            else:
                                rto_params[param] = structure_params["crest_level"]

                if link_type == "FlowControlledStructure":
                    rto_params["min_flow"] = 0
                    coeff = structure_params["coefficient"]
                    width = structure_params["crest_width"]
                    height = structure_params["opening_height"]
                    crest_level = structure_params["crest_level"]
                    hus = structure_params["hus"]
                    q = (
                        coeff
                        * width
                        * height
                        * (2 * g * (hus - (crest_level + coeff * height))) ** (1 / 2)
                    )
                    rto_params["max_flow"] = q

            else:
                link_type = "Channel"
                stations = []
                for idx, xs_row in sobek_cross_sections.loc[
                    sobek_cross_sections["LINK"] == link_id
                ].iterrows():
                    station = dict()
                    station["roughness"] = sbk_case.parameters.friction["global"][
                        "value"
                    ]
                    station["distance"] = xs_row["LINK_POS"]
                    station["cross_section"] = [
                        {"z": z, "lr": y}
                        for y, z in sbk_case.parameters.cross_sections[
                            xs_row["ID"]
                        ].items()
                    ]
                    if initials:
                        station["initial_level"] = row["initial_level"]
                    stations += [station]
                    
                rto_params['hydraulic_routing'] = {"model": "saint-venant",
                                                   "roughness_model": "manning",
                                                   "stations": stations}
                if initials:
                    rto_params['hydraulic_routing'].update({"initial_flow":row['initial_flow']})
                    
                
                rto_params['length'] = row['geometry'].length  
                
            rto_params['uid'] = f'a{link_id.replace("-","_")}' 
            
            if initials:
                if link_type in ['FlowControlledStructure', 'Pump']:
                    rto_params['initial_flow'] = row['initial_flow']
                elif link_type == 'Weir':
                    rto_params['initial_crest_level'] = structure_params['crest_level']
  
            if rto_groups:
                if row["group"]:
                    rto_params["group_uid"] = row["group"]

            # overwrite all that is supplied from extra parameters
            if link_id in extra_params.keys():
                for key, value in extra_params[link_id].items():
                    rto_params[key] = value
            try:
                sbk_links += [getattr(links, link_type)(**rto_params)]
            except:
                f"error in writing link_id {link_id} with type {link_type} to kisters"

        return sbk_links

    def add_rto_groups(rto_groups):
        res_groups = []
        for group in rto_groups:
            params = {
                key: value
                for key, value in group.items()
                if key in ["uid", "display_name", "location", "schematic_location"]
            }
            res_groups += [getattr(groups, group["type"])(**params)]

        return res_groups

    rto_nodes = sbk_nodes(sobek_network)
    rto_links = sbk_links(sobek_network)
    rto_groups = add_rto_groups(rto_groups)
    network.save_nodes(rto_nodes)
    network.save_links(rto_links)
    network.save_groups(rto_groups)

    return dict(nodes=rto_nodes, links=rto_links, groups=rto_groups)

import json

from kisters.network_store.client.network import Network
from kisters.water.rest_client import RESTClient
from kisters.water.rest_client.auth import OpenIDConnect


rest_server_url = "https://hdsr-detol-network.water.kisters.cloud/"


authentication = OpenIDConnect(
    client_id="hdsr-detol.operational.external.0D2EDE59",
    client_secret="3e7a9a06-33ea-4d2d-b46f-0348cf305a9f",
)


client = RESTClient(url=rest_server_url, authentication=authentication)
network = Network("de-tol", client=client)

groups = [
    {
        "type": "WeirComplex",
        "uid": weir.uid[1:],
        "display_name": weir.display_name,
        "us_node": weir.source_uid,
        "ds_node": weir.target_uid,
        "schematic_location": network.get_nodes([weir.source_uid])[
            0
        ].schematic_location.dict(),
        "location": network.get_nodes([weir.source_uid])[0].location.dict(),
    }
    for weir in network.get_links(element_class="Weir")
]
print(json.dumps(groups, indent=4))
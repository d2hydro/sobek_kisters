# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 14:07:20 2019

@author: danie
"""

# bokeh serve --show model_web.py"

from bokeh.layouts import column
from bokeh.models import Button
from bokeh.plotting import curdoc

from network_viewer import NetworkViewer
from kisters.water.hydraulic_network.client import (
    Network,
    OpenIDConnect,
    RESTClient,
)
import kisters.water.hydraulic_network.models.link as link
import kisters.water.hydraulic_network.models.node as node




auth_config = {
    "client_id": "sobek-hydronet",
    "client_secret": "c93822c1-2e7e-4864-8f18-271c5674dcb0",
    "issuer_url": "https://auth.kisters.cloud/auth/realms/external",
}
rest_server_url = "http://hydraulic-network.kisters.eu.ngrok.io/"

authentication = OpenIDConnect(**auth_config)

client = RESTClient(url=rest_server_url, authentication=authentication)
network = Network("test", client=client)

network_viewer = NetworkViewer(network=network)

def callback():
    print("Hello")
button = Button(label="Press Me")
button.on_click(callback)

curdoc().add_root(network_viewer.figure)

#curdoc().add_root(column(button, network_viewer.figure))
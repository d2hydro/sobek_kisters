# -*- coding: utf-8 -*-
"""
Created on Wed Jul 10 14:07:20 2019

@author: danie
"""

# bokeh serve --show model_web.py"

from bokeh.layouts import column
from bokeh.models import Button
from bokeh.plotting import curdoc

from viewer import NetworkViewer

from kisters.network_store.client.network import Network
from kisters.water.rest_client import RESTClient
from kisters.water.rest_client.auth import OpenIDConnect

#%%
rest_server_url = "https://hdsr-detol-network.water.kisters.cloud/"


authentication = OpenIDConnect(
    client_id="hdsr-detol.operational.external.0D2EDE59",
    client_secret="3e7a9a06-33ea-4d2d-b46f-0348cf305a9f",
)


client = RESTClient(url=rest_server_url, authentication=authentication)
network = Network('de-tol-owd', client=client)

network_viewer = NetworkViewer(network=network)

def callback():
    print("Hello")
button = Button(label="Press Me")
button.on_click(callback)

curdoc().add_root(network_viewer.figure)

#curdoc().add_root(column(button, network_viewer.figure))
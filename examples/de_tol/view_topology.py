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

from config import(
    KISTERS_NAME,
    CLIENT_ID,
    CLIENT_SECRET)

#%%



rest_server_url = "https://hdsr-detol-network.water.kisters.cloud/"


authentication = OpenIDConnect(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)


client = RESTClient(url=rest_server_url, authentication=authentication)
network = Network(KISTERS_NAME, client=client)

network_viewer = NetworkViewer(network=network)

def callback():
    print("Hello")
button = Button(label="Press Me")
button.on_click(callback)

curdoc().add_root(network_viewer.figure)

#curdoc().add_root(column(button, network_viewer.figure))
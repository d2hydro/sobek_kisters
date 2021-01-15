from pathlib import Path

import numpy as np
from bokeh.models import (
    BoxZoomTool,
    Circle,
    GraphRenderer,
    HoverTool,
    ImageURL,
    MultiLine,
    Plot,
    Range1d,
    ResetTool,
    StaticLayoutProvider,
)
from bokeh.models.ranges import Range1d
from bokeh.models.tiles import WMTSTileSource
from bokeh.plotting import figure
from scipy.interpolate import make_interp_spline


class NetworkViewer:
    node_size = 10

    image_path = "https://gitlab.com/kisters/water/hydraulic-network/visualization/raw/master/kisters/water/hydraulic_network/visualization/images"
    vertex_interpolation_density = 1.0 / 50.0

    link_as_node_types = "Pump", "Turbine", "Valve", "Orifice"

    def __init__(self, network, schematic_location: bool = False):
        if schematic_location:
            self.location_key = "schematic_location"
            self.figure = figure()
        else:
            self.location_key = "location"
            self.figure = figure(x_axis_type="mercator", y_axis_type="mercator")

            # Add OpenStreetMaps background
            tile_source = WMTSTileSource(
                url="https://tiles.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2.png",
                # url="http://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
                attribution=(
                    # '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, '
                    '&copy; <a href="https://cartodb.com/attributions">CartoDB</a>'
                ),
                initial_resolution=None,
            )

            self.figure.add_tile(tile_source)

        # Add renderer
        self._graph_renderer = GraphRenderer()
        self.figure.renderers.append(self._graph_renderer)
        self.figure.add_tools(
            HoverTool(
                tooltips=[
                    ("uid", "@index"),
                    # ("name", "@text"),
                ]
            )
        )

        # Render
        self._network = network
        self._get_topology()
        self._render()

    def _get_topology(self):
        self._nodes = {
            node.uid: node.dict(exclude_none=True) for node in self._network.get_nodes()
        }

        raw_links = [link.dict(exclude_none=True) for link in self._network.get_links()]
        links = []

        def centroid(a, b):
            va = np.array([a[self.location_key]["x"], a[self.location_key]["y"]])
            vb = np.array([b[self.location_key]["x"], b[self.location_key]["y"]])
            return np.mean(np.vstack([va, vb]), axis=0)

        for link in raw_links:
            # In hydraulic network, pumps and valves are links.  We display a pump (or a valve) as a
            # link - node - link in the graph.
            if link["element_class"] in self.link_as_node_types:
                source_node = self._nodes[link["source_uid"]]
                target_node = self._nodes[link["target_uid"]]
                vertices = link.get("vertices", [])
                if len(vertices) >= 1:
                    center = vertices[len(vertices) // 2]
                else:
                    center = centroid(source_node, target_node)
                self._nodes[link["uid"]] = {
                    "uid": link["uid"],
                    "display_name": link["display_name"],
                    self.location_key: {"x": center[0], "y": center[1]},
                    "element_class": link["element_class"],
                }
                links.append(
                    {
                        "uid": f"{source_node['uid']}__{link['uid']}",
                        "source_uid": link["source_uid"],
                        "target_uid": link["uid"],
                        "vertices": vertices[: len(vertices) // 2],
                    }
                )
                links.append(
                    {
                        "uid": f"{link['uid']}__{target_node['uid']}",
                        "source_uid": link["uid"],
                        "target_uid": link["target_uid"],
                        "vertices": vertices[len(vertices) // 2 + 1 :],
                    }
                )
            else:
                links.append(link)

        self._links = {link["uid"]: link for link in links}

    def _render(self):
        nodes, links = self._nodes.values(), self._links.values()

        # Add nodes
        def image_url(node):
            return f"{self.image_path}/{node['element_class']}.svg"

        self._graph_renderer.node_renderer.data_source.data = dict(
            index=[node["uid"] for node in nodes],
            text=[node["display_name"] for node in nodes],
            # url=[image_url(node) for node in nodes],
        )
        # self._graph_renderer.node_renderer.glyph = ImageURL(
        #     w={"value": self.node_size, "units": "screen"},
        #     h={"value": self.node_size, "units": "screen"},
        #     anchor="center",
        #     url="url",
        # )

        xs = []
        ys = []
        for link in links:
            x = [
                self._nodes[link["source_uid"]][self.location_key]["x"],
                *[v["x"] for v in link.get("vertices", [])],
                self._nodes[link["target_uid"]][self.location_key]["x"],
            ]

            y = [
                self._nodes[link["source_uid"]][self.location_key]["y"],
                *[v["y"] for v in link.get("vertices", [])],
                self._nodes[link["target_uid"]][self.location_key]["y"],
            ]
            xs.append(x)
            ys.append(y)

        # Add edges
        self._graph_renderer.edge_renderer.data_source.data = dict(
            start=[link["source_uid"] for link in links],
            end=[link["target_uid"] for link in links],
            xs=xs,
            ys=ys,
        )
        self._graph_renderer.edge_renderer.glyph = MultiLine(
            line_color="#6686ba", line_alpha=1.0, line_width=5
        )

        # Set node layout
        graph_layout = {
            node["uid"]: (
                node[self.location_key]["x"],
                node[self.location_key]["y"],
            )
            for node in nodes
        }
        self._graph_renderer.layout_provider = StaticLayoutProvider(
            graph_layout=graph_layout
        )

        # Set viewport
        x = [node[self.location_key]["x"] for node in nodes] + [
            v["x"] for link in links for v in link.get("vertices", [])
        ]
        y = [node[self.location_key]["y"] for node in nodes] + [
            v["y"] for link in links for v in link.get("vertices", [])
        ]
        min_x = np.min(x)
        max_x = np.max(x)
        min_y = np.min(y)
        max_y = np.max(y)

        margin = 0.5 * self.node_size
        width = np.max([max_x - min_x, max_y - min_y]) + 2 * margin

        mean_x = np.mean([min_x, max_x])
        self.figure.x_range = Range1d(
            int(mean_x - 0.5 * width), int(mean_x + 0.5 * width)
        )
        self.figure.x_range.reset_start = self.figure.x_range.start
        self.figure.x_range.reset_end = self.figure.x_range.end

        mean_y = np.mean([min_y, max_y])
        self.figure.y_range = Range1d(
            int(mean_y - 0.5 * width), int(mean_y + 0.5 * width)
        )
        self.figure.y_range.reset_start = self.figure.y_range.start
        self.figure.y_range.reset_end = self.figure.y_range.end


if __name__ == "__main__":
    from bokeh.embed import file_html
    from bokeh.plotting import figure
    from bokeh.resources import CDN

    from upload_model import network

    figure = NetworkViewer(network).figure
    html = file_html(figure, CDN, "network")
    Path("network.html").write_text(html)

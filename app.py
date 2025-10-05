import sys
from pathlib import Path

# Add parent directory to path using absolute path

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.SPACELAB])
sidebar = dbc.Nav(
            [
                dbc.NavLink(
                    [
                        html.Div(page["name"], className="ms-0"),
                    ],
                    href=page["path"],
                    active="exact",
                )
                for page in dash.page_registry.values()
            ],
            vertical=True,
            pills=True,
            horizontal="center",
            className="bg-light",
)

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.Div("Digital Twin for Air Quality Monitoring and Prediction",
                         style={'fontSize':50, 'textAlign':'center', 'color':'blue'}))
    ]),

    html.Hr(),

    dbc.Row(
        [
            dbc.Col(
                [
                    sidebar
                ], xs=2, sm=2, md=1, lg=1, xl=1, xxl=1),

            dbc.Col(
                [
                    dash.page_container
                ], xs=10, sm=10, md=11, lg=11, xl=11, xxl=11)
        ]
    )
], fluid=True)


server = app.server
if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8080, debug=False)
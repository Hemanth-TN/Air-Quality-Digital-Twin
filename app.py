import sys
from pathlib import Path

# Add parent directory to path using absolute path

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.SPACELAB])
# Configure Flask server for deployment
server = app.server

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

app.layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col(html.Div("Digital Twin for Air Quality Monitoring and Prediction",
                             style={'fontSize': '3.5rem', 'textAlign':'center', 'color':'blue', 
                                   '@media (max-width: 768px)': {'fontSize': '2.5rem'}}))
        ]),

        html.Hr(),

        dbc.Row(
            [
                dbc.Col(
                    [
                        sidebar
                    ], xs=12, sm=12, md=3, lg=2, xl=2, xxl=1),

                dbc.Col(
                    [
                        dash.page_container
                    ], xs=12, sm=12, md=9, lg=10, xl=10, xxl=11)
            ]
        )
    ], fluid=True)
], style={
    '@media (max-width: 768px)': {
        'padding': '10px'
    }
})



# Optional: Set cache headers for static files (though Dash handles most of this)
app.server.config.update(
    SEND_FILE_MAX_AGE_DEFAULT=31536000,  # 1 year cache for static files
    SESSION_COOKIE_SECURE=True,          # HTTPS only cookies (good for production)
    SESSION_COOKIE_HTTPONLY=True,        # Prevent XSS
)

if __name__ == "__main__":
    # This runs only for local development
    # Azure uses Gunicorn, so this block is ignored in deployment
    # app.run_server(host="0.0.0.0", port=8080, debug=True)
    app.run(host="0.0.0.0", port=8080, debug=True)

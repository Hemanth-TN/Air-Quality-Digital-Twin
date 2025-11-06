from dash import dcc, html, Input, Output, register_page, callback, Patch
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import functools
from data_handling import get_data, CITIES

# Register the new page
register_page(
    __name__,
    path='/',  # This page will be accessible at the root URL
    name='Data Coverage Summary',
)

# Get a list of all unique pollutants from all locations (lazy loading)
def get_all_pollutants_and_locations():
    all_data_dfs = []
    for city in CITIES:
        all_data_dfs.append(get_data(city))
    all_data_df = pd.concat(all_data_dfs)
    all_pollutants = all_data_df['pollutant'].unique().tolist()
    all_locations = all_data_df['location_name'].unique().tolist()
    return all_pollutants, all_locations

all_pollutants, all_locations = get_all_pollutants_and_locations()

def get_availability(df):
    expected = 24
    actual = df['avg'].notna().sum()
    return (actual/expected)*100

@functools.lru_cache(maxsize=32)
def get_availability_cached(city_name, location_name):
    """Cache the availability calculation for faster repeat queries."""
    df = get_data(city_name)
    location_df = df[df['location_name'] == location_name]
    
    if location_df.empty:
        return pd.DataFrame()
    
    temp_df = location_df.groupby('pollutant').resample('D', level=0, include_groups=False).apply(get_availability).unstack(level=0)
    
    if isinstance(temp_df, pd.Series):
        temp_df = temp_df.unstack(-1)
    
    return pd.melt(temp_df.reset_index(), id_vars=['Timestamp'], var_name='pollutant', value_name='availability')

def create_initial_heatmap_figure():
    """Create an initial empty heatmap figure that can be patched later."""
    fig = go.Figure(go.Scatter(
        x=[], y=[], mode='markers',
        marker=dict(
            size=25,
            symbol='square',
            color=[],
            colorscale=px.colors.sequential.YlGn,
            cmin=0,
            cmax=100,
            colorbar=dict(
                title="Data Availability (%)",
                tickvals=[0, 25, 50, 75, 100],
                ticktext=['0%', '25%', '50%', '75%', '100%'],
                tickmode='array',
                thickness=15,
                len=0.7
            )
        ),
        hovertemplate='Date: %{x}<br>Pollutant: %{y}<br>Data Availability: %{marker.color:.2f}%'
    ))
    
    fig.update_layout(
        title={
            'text': 'Select location to view data availability',
            'font': {'size': 16},
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='Date',
        yaxis_title='Pollutant',
        xaxis=dict(
            side='bottom',
            tickformat='%Y-%m-%d',
            dtick='M3',
            showgrid=False,
            showline=False,
            ticks='outside',
            ticklen=5,
            tickangle=45,
            tickfont=dict(size=12)
        ),
        yaxis=dict(
            automargin=True,
            showgrid=False,
            showline=False,
            ticks='',
            tickfont=dict(size=12)
        ),
        plot_bgcolor='rgb(30,30,30)',
        paper_bgcolor='rgb(30,30,30)',
        font_color='white',
        margin=dict(l=80, r=80, t=60, b=80),
        autosize=True,
        height=400
    )
    return fig

layout = html.Div([
    # html.H1("Data summary Dashboard", style={'textAlign': 'center', 'color': 'blue'}),
    html.Br(),
    dcc.RadioItems(options=[ 'Chicago',  'Sacramento','Bangalore','New Delhi'], 
                   value='Chicago', 
                   id='city_radio', 
                   inline=True, 
                   style={
                       'textAlign': 'center', 
                       'marginRight': '15px',
                       'fontSize': '16px',
                       'padding': '10px'
                   }
    ),
    html.Br(),
    dcc.Dropdown(
        id='location_dropdown', 
        multi=False, 
        placeholder='Select a location',
        style={'fontSize': '16px', 'minHeight': '44px'}
    ),
    html.Br(),
    html.Div(
        dcc.Loading(
            id='loading-graph',
            type='circle',
            children=dcc.Graph(
                id='timeseries_data_summary',
                figure=create_initial_heatmap_figure(),  # Add initial figure
                style={
                    'height': '70vh',
                    'width': '100%',
                    'minHeight': '500px'
                },
                config={
                    'scrollZoom': True,
                    'responsive': True,
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'air_quality_data',
                        'height': 800,
                        'width': 1200,
                        'scale': 1
                    }
                }
            ),
        ),
        style={
            'display': 'flex', 
            'justifyContent': 'center',
            'width': '100%',
            'overflow': 'auto'
        }
    )
], style={
    'padding': '10px',
    'maxWidth': '100%',
    'margin': '0 auto'
})

@callback(
    Output(component_id='location_dropdown', component_property='options'),
    Output(component_id='location_dropdown', component_property='value'),
    Input(component_id='city_radio', component_property='value'))
def update_location_dropdown(city_name):
    df = get_data(city_name)
    locations = df['location_name'].unique().tolist()
    
    options = [{'label': loc, 'value': loc} for loc in locations]
    value = locations[0] if locations else None
    
    return options, value

@callback(
    Output(component_id='timeseries_data_summary', component_property='figure'),
    Input(component_id='city_radio', component_property='value'),
    Input(component_id='location_dropdown', component_property='value'))
def show_data_summary(city_name, location_name):
    if location_name is None:
        return create_initial_heatmap_figure()
    
    df = get_data(city_name)
    location_df = df[df['location_name'] == location_name]
    
    if location_df.empty:
        return create_initial_heatmap_figure()
    
    # Process data (keep this part optimized)
    temp_df = location_df.groupby('pollutant').resample('D', level=0, include_groups=False).apply(get_availability).unstack(level=0)

    if isinstance(temp_df, pd.Series):
        temp_df = temp_df.unstack(-1)

    availability_df = pd.melt(temp_df.reset_index(), id_vars=['Timestamp'], var_name='pollutant', value_name='availability')
    
    # Use Patch to update only the data
    patch = Patch()
    
    # Update scatter plot data
    patch['data'][0]['x'] = availability_df['Timestamp'].tolist()
    patch['data'][0]['y'] = availability_df['pollutant'].tolist()
    patch['data'][0]['marker']['color'] = availability_df['availability'].tolist()
    
    # Update title
    patch['layout']['title']['text'] = f'Daily Data Availability for Pollutants at {location_name}'
    
    # Update height based on number of pollutants
    num_pollutants = len(availability_df['pollutant'].unique())
    patch['layout']['height'] = max(400, num_pollutants * 50)
    
    return patch
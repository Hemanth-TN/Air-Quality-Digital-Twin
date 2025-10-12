from dash import callback, dcc, html, Input, Output, register_page
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data_handling import get_data, get_location_data, get_limits_data, CITIES
from pathlib import Path

# Register the page with Dash
register_page(
    __name__,
    path='/Data_Visualization',  # This page will be the homepage
    name='Sensor Locations and Raw Data',
)

# CITIES is imported from data_handling

# for city in ['Bangalore', 'New Delhi']:
#     df_temp = DATA[city]
#     M = {'so2': 64.066, 'no2': 46.0055, 'co': 28.01, 'o3': 48.00}
#     mask_ppb = (df_temp['unit'] == 'ppb') & (df_temp['pollutant'].isin(M))
#     factor = df_temp.loc[mask_ppb, 'pollutant'].map(M)
#     df_temp.loc[mask_ppb, 'avg'] = df_temp.loc[mask_ppb, 'avg'] * factor / 24.45
#     df_temp.loc[mask_ppb, 'unit'] = 'µg/m³'

#     mask_ppm = (df_temp['unit'] == 'ppm') & (df_temp['pollutant'].isin(M))
#     factor2 = df_temp.loc[mask_ppm, 'pollutant'].map(M)
#     df_temp.loc[mask_ppm, 'avg'] = df_temp.loc[mask_ppm, 'avg'] * factor2 * 1000 / 24.45
#     df_temp.loc[mask_ppm, 'unit'] = 'µg/m³'

def get_location_data(df):
    """Aggregates location data for plotting on the map."""
    location_data = df.groupby('location_name').agg(
        latitude=('latitude', 'first'),
        longitude=('longitude', 'first'),
        readings_available=('pollutant', lambda x: x.unique().tolist())
    ).reset_index()
    location_data['size'] = 1
    return location_data

def get_all_locations_pollutant(df:pd.DataFrame, pollutant:str):
    """Pivots data for a given pollutant across all locations."""
    df = df[df['pollutant'] == pollutant].copy()
    return df.pivot_table(index='Timestamp', columns='location_name', values='avg')


layout = html.Div([
    # html.H1("Air Quality Monitoring Dashboard", style={'textAlign': 'center', 'color': 'blue'}),
    
    # Store component to hold the selected location name
    dcc.Store(id='selected_location_store', data=None, storage_type='session'),

    html.Div([
        # Left Panel for the City Map
        html.Div([
            html.Label('Select a city'),
            dcc.Dropdown(options=CITIES, value='Chicago', id='city_dropdown'),
            html.Br(),
            html.Label('City Map'),
            dcc.Graph(id='city_map', style={'height': '800px'}, config={'scrollZoom': True}),
        ], style={'padding': 10, 'flex': 0.8}),

        # Right Panel for Pollutant Trends
        html.Div([
            html.Label('Select Measurement'),
            dcc.Dropdown(id='pollutant_dropdown', multi=False, placeholder='Click location or select available measurement'),
            html.Br(),
            html.Label('Time Series at selected location'),
            html.Div(
                dcc.Loading(
                    id='loading-graph-1',
                    type='circle',                     # spinner style: 'circle'|'dot'|'default'
                    children=dcc.Graph(
                        id='timeseries_graph_single',
                        style={'height': '450px','width': '1200px'},  # Set a fixed width
                        config={'scrollZoom': True}
                    )
                ),
            ),
            html.Label('Time Series at all locations'),
            html.Div(
                dcc.Loading(
                    id='loading-graph-2',
                    type='circle',                     # spinner style: 'circle'|'dot'|'default'
                    children=dcc.Graph(
                        id='timeseries_graph_all',
                        style={'height': '450px', 'width': '1200px'},  # Set a fixed width
                        config={'scrollZoom': True}
                    )
                ),
            ),
        ], style={'padding': 10, 'flex': 1.6})

    ], style={'display': 'flex', 'flexDirection': 'row'})
], style={'width': '100%'})

# --- Callbacks ---

# Callback 1: Update the map and reset the selected location store
@callback(
    Output('city_map', 'figure'),
    Output('selected_location_store', 'data'),
    Input('city_dropdown', 'value'),
    Input('selected_location_store', 'data')
)
def show_city_sensors(city_name, selected_location):
    df = get_data(city_name)
    if selected_location is None:
        selected_location = df['location_name'].unique()[0]

    unique_locations_df = get_location_data(df)
    unique_locations_df['highlight'] = unique_locations_df['location_name'].apply(lambda loc: 'Selected' if loc == selected_location else 'Other')
    fig = px.scatter_mapbox(
        unique_locations_df,
        lat="latitude",
        lon="longitude",
        hover_name="location_name",
        size='size',
        hover_data={"size": False, "latitude": False, "longitude": False, 'readings_available': True},
        custom_data=['location_name'],
        color='highlight',
        color_discrete_map={'Selected': 'red', 'Other': 'blue'},
        zoom=9,
        width=1000,
        height=700
    )
    
    latitude = unique_locations_df['latitude'].mean()
    longitude = unique_locations_df['longitude'].mean()
    
    fig.update_layout(
        title=f"Locations in the {city_name} Region",
        mapbox_style="open-street-map",
        mapbox=dict(
            center=dict(lat=latitude, lon=longitude),
            zoom=9
        )
    )

    if selected_location not in unique_locations_df['location_name'].values:
        selected_location = None


    # Return a figure and reset the selected location to None
    return fig, selected_location

# Callback 2: Store the clicked location name
@callback(
    Output('selected_location_store', 'data', allow_duplicate=True),
    Input('city_map', 'clickData'),
    prevent_initial_call=True
)
def store_selected_location(clickData):
    if clickData and 'points' in clickData:
        location_name = clickData['points'][0]['customdata'][0]
        return location_name
    return None

# Callback 3: Update pollutant dropdown based on the selected location (from store) or city change
@callback(
    Output('pollutant_dropdown', 'options'),
    Output('pollutant_dropdown', 'value'),
    Input('selected_location_store', 'data'),
    Input('city_dropdown', 'value')
)
def update_pollutant_options(location_name, city_name):
    df = get_data(city_name)

    if location_name is None:
        # Default to the first location in the city if none is selected
        unique_locations = df['location_name'].unique()
        if unique_locations.size > 0:
            location_name = unique_locations[0]
        else:
            return [], None # No locations found
    
    location_df = df[df['location_name'] == location_name]
    pollutants = location_df['pollutant'].unique().tolist()
    
    options = [{'label': p, 'value': p} for p in pollutants]
    
    # Set the default value to the first pollutant available
    value = 'temperature' if pollutants else None
    
    return options, value

# Callback 4: Update the time series graphs based on city, pollutant, and selected location (from store)
@callback(
    Output('timeseries_graph_single', 'figure'),
    Output('timeseries_graph_all', 'figure'),
    Input('city_dropdown', 'value'),
    Input('pollutant_dropdown', 'value'),
    Input('selected_location_store', 'data')
)
def update_timeseries(city_name, selected_pollutant, location_name):
    # Check for valid inputs
    if not city_name or not selected_pollutant:
        return {}, {}
    
    df = get_data(city_name)
    
    # Set a default location if none is clicked
    if location_name is None:
        unique_locations = df['location_name'].unique()
        if unique_locations.size > 0:
            location_name = unique_locations[0]
        else:
            return {}, {}

    # Single location graph
    filtered_df = df[
        (df['location_name'] == location_name) & 
        (df['pollutant'] == selected_pollutant)
    ]
    
    if filtered_df.empty:
        single_fig = px.scatter(title="No data available for this pollutant at this location.")
        all_fig = px.scatter(title="No data available for this pollutant across all locations.")
        return single_fig, all_fig
    
    fig_data = go.Scatter(x=filtered_df.index, y=filtered_df['avg'], mode='markers',
                          name=filtered_df['pollutant'].iloc[0],
                          marker=dict(color='crimson', size=8, opacity=0.6))
    fig_layout = go.Layout(
        title=f"{selected_pollutant} at {location_name}",
        xaxis_title='Timestamp',
        yaxis_title=filtered_df['unit'].unique()[0],
        width=1200,
        height=450
    )
    single_fig = go.Figure(data=[fig_data], layout=fig_layout)


    df_data_pollutant = get_all_locations_pollutant(df, selected_pollutant)

    all_fig = go.Figure()
    # add dimmed traces for all other locations
    for loc in df_data_pollutant.columns:
        y_ser = df_data_pollutant[loc]
        if loc != location_name:
            # highlighted trace for selected location
            all_fig.add_trace(go.Scatter(
                x=y_ser.index, y=y_ser.values,
                mode='lines',
                name=str(loc),
                line=dict(width=1, color='rgba(211,211,211,0.5)'),
                hoverinfo='text',
                showlegend=True,
                hovertext=[f"{loc}<br>{selected_pollutant}: {v:.3f}" if pd.notna(v) else f"{loc}<br>NaN" for v in y_ser.values]
            ))
        else:
            # dimmed / de-emphasized traces
            all_fig.add_trace(go.Scatter(
                x=y_ser.index, y=y_ser.values,
                mode='lines+markers',
                name=str(loc),
                marker=dict(color='crimson', size=8, opacity=0.95),
                line=dict(color='crimson', width=2),
                hoverinfo='text',
                hovertext=[f"{loc}<br>{selected_pollutant}: {v:.3f}" if pd.notna(v) else f"{loc}<br>NaN" for v in y_ser.values]
            ))

    all_fig.update_layout(
        title=f"{selected_pollutant} at all locations (highlight: {location_name})",
        xaxis_title='Timestamp',
        yaxis_title=filtered_df['unit'].unique()[0],
        width=1200,
        height=450
    )

    # Read limits CSV and add to both figures (if available)
    
    lower, upper = None, None
    limits_df = get_limits_data(city_name)
    if selected_pollutant in limits_df.index:
        # flexible column name handling
        if 'lower limit' in limits_df.columns and 'upper limit' in limits_df.columns:
            lower =  0 #float(limits_df.loc[selected_pollutant, 'lower limit'])
            upper = float(limits_df.loc[selected_pollutant, 'upper limit'])
        else:
            col_lower = next((c for c in limits_df.columns if 'lower' in c.lower()), None)
            col_upper = next((c for c in limits_df.columns if 'upper' in c.lower()), None)
            if col_lower and col_upper:
                lower = float(limits_df.loc[selected_pollutant, col_lower])
                upper = float(limits_df.loc[selected_pollutant, col_upper])
            elif len(limits_df.columns) >= 2:
                lower = float(limits_df.iloc[limits_df.index.get_loc(selected_pollutant), 1])
                upper = float(limits_df.iloc[limits_df.index.get_loc(selected_pollutant), 0])


    # Set y-axis range from limits (with small padding) instead of drawing shapes
    if lower is not None and upper is not None:
        try:
            lower = float(lower)
            upper = float(upper)
            if upper <= lower:
                # fallback: use the exact bounds if quantiles weirdly inverted
                y0, y1 = lower, upper
            else:
                pad = max((upper - lower) * 0.25, 1e-6)  # 25% padding
                y0, y1 = lower - pad, upper + pad

            single_fig.update_yaxes(range=[y0, y1])
            all_fig.update_yaxes(range=[y0, y1])
        except Exception:
            # if casting fails, leave default axes
            pass

    return single_fig, all_fig
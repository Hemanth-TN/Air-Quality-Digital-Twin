from dash import dcc, html, Input, Output, register_page, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data_handling import get_data, CITIES

# Register the new page
register_page(
    __name__,
    path='/',  # This page will be accessible at the root URL
    name='Data Coverage Summary',
)

# Get a list of all unique pollutants from all cities (lazy loading)
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

layout = html.Div([
    # html.H1("Data summary Dashboard", style={'textAlign': 'center', 'color': 'blue'}),
    html.Br(),
    dcc.RadioItems(options=[ 'Chicago',  'Sacramento','Bangalore','New Delhi'], 
                   value='Chicago', 
                   id='city_radio', 
                   inline=True, 
                   style={'textAlign': 'center', 'marginRight': '15px'}  # Add spacing between buttons
    ),
    html.Br(),
    dcc.Dropdown(id='location_dropdown', multi=False, placeholder='Select a location'),
    html.Br(),
    html.Div(
            dcc.Loading(
                id='loading-graph',
                type='circle',                     # spinner style: 'circle'|'dot'|'default'
                children=dcc.Graph(
                    id='timeseries_data_summary',
                    style={'height': '1000px'},
                    config={'scrollZoom': True}
                )
            ),
        style={'display': 'flex', 'justifyContent': 'center'}
    )
    ])


@callback(
    Output(component_id='location_dropdown', component_property='options'),
    Output(component_id='location_dropdown', component_property='value'),
    Input(component_id='city_radio', component_property='value'))
def update_location_dropdown(city_name):
    df = get_data(city_name)
    locations = df['location_name'].unique().tolist()
    
    options = [{'label': loc, 'value': loc} for loc in locations]
    # Set the value to the first location by default
    value = locations[0] if locations else None
    
    return options, value

@callback(
    Output(component_id='timeseries_data_summary', component_property='figure'),
    Input(component_id='city_radio', component_property='value'),
    Input(component_id='location_dropdown', component_property='value'))
def show_data_summary(city_name, location_name):
    df = get_data(city_name)
    if location_name is None:
        return {}
    
    location_df = df[df['location_name'] == location_name]
    if location_df.empty:
        return {}
    
    temp_df = location_df.groupby('pollutant').resample('D', level=0, include_groups=False).apply(get_availability).unstack(level=0)

    if isinstance(temp_df, pd.Series):
        temp_df = temp_df.unstack(-1)

    availability_df = pd.melt(temp_df.reset_index(), id_vars=['Timestamp'], var_name='pollutant', value_name='availability')

    fig = go.Figure(go.Scatter(
                        x=availability_df['Timestamp'],
                        y=availability_df['pollutant'],
                        mode='markers',
                        marker=dict(
                            size=30, # Adjust marker size to make them look like rectangles
                            symbol='square',
                            color=availability_df['availability'],
                            colorscale=px.colors.sequential.YlGn,
                            cmin=0,
                            cmax=100,
                            colorbar=dict(
                                title="Data Availability (%)",
                                tickvals=[0, 25, 50, 75, 100],
                                ticktext=['0%', '25%', '50%', '75%', '100%'],
                                tickmode='array')),
                        hovertemplate='Date: %{x}<br>Pollutant: %{y}<br>Data Availability: %{marker.color:.2f}%',),
                    )

    # 4. Configure the plot layout
    fig.update_layout(
        title=f'Daily Data Availability for Pollutants at {location_name}',
        xaxis_title='Date',
        yaxis_title='Pollutant',
        xaxis=dict(
            side='bottom',
            tickformat='%Y-%m-%d',
            dtick='M3', # Monthly ticks
            showgrid=False,
            showline=False,
            ticks='outside',
            ticklen=5,
            tickangle=45,
        ),
        yaxis=dict(
            automargin=True,
            showgrid=False,
            showline=False,
            ticks='',
        ),
        plot_bgcolor='rgb(30,30,30)',
        paper_bgcolor='rgb(30,30,30)',
        font_color='white',
        width=1200,
        height=max(600,len(availability_df['pollutant'].unique()) * 70)   # Dynamic height based on number of pollutants``
    )
    return fig
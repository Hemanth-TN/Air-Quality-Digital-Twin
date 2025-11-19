from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode, tools_condition
import requests
import os
from langchain_core.tools import Tool
from langchain_core.messages import SystemMessage

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

import dash
from dash import dcc, html, Input, Output, State, register_page, callback
import plotly.express as px

from dash import dcc, html, Input, Output
from dash import State as DashState

import pandas as pd
import asyncio
from geopy.geocoders import ArcGIS

from typing import Dict, Any


register_page(
    __name__,
    path='/Agent_AirWatch', 
    name='Agent AirWatch',
)


load_dotenv(override=True)


def get_city_data(city_name:str) -> pd.DataFrame:
    """
        Internal method to fetch city data from OpenAQ API.
        
        Args:
            city_name: Name of the city
            
        Returns:
            DataFrame with city air quality data or None if not found
    """
    geolocator = ArcGIS()
    radius = 24999  # in meters
    limit = 100
        # Geocode the city
    try:
        location = geolocator.geocode(city_name)
        if not location:
            return None
    except Exception as e:
        raise Exception(f"Could not geocode city: {str(e)}")
        
    latitude = location.latitude
    longitude = location.longitude
    
    # Fetch data from OpenAQ API
    headers = {"X-API-Key": os.getenv("OPENAQ-API-KEY", "")}
    url = f"https://api.openaq.org/v3/locations?coordinates={str(latitude)}%2C%20{str(longitude)}&radius={radius}&limit={limit}&page=1&order_by=id&sort_order=asc"
    
    try:
        city_response = requests.get(url, headers=headers, timeout=10).json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")
    
    if not city_response.get('results'):
        return None
    
    # Parse results
    locations = [location['name'] for location in city_response['results']]
    latitudes = [location['coordinates']['latitude'] for location in city_response['results']]
    longitudes = [location['coordinates']['longitude'] for location in city_response['results']]
    
    pollutants = []
    for f in city_response['results']:
        pollutants.append([k['name'] for k in f['sensors']])
    
    sensor_ids = []
    for f in city_response['results']:
        sensor_ids.append([k['id'] for k in f['sensors']])
    
    city_data_dict = {
        "Location Names": locations,
        "Latitudes": latitudes,
        "Longitudes": longitudes,
        "Pollutants Measured": pollutants,
        "Sensor IDs": sensor_ids
    }
    
    city_data = pd.DataFrame(city_data_dict)
    city_data['Size'] = 3  # Add a size column for map plotting
    return city_data


# Add this global dictionary to store fetched data
last_city_data = {}

def get_city_data_for_llm(city_name: str) -> str:
    """
    Fetch city data and return it in a format the LLM can understand.
    
    Args:
        city_name: Name of the city
        
    Returns:
        String representation of city air quality data
    """
    df = get_city_data(city_name)
    
    if df is None or df.empty:
        return f"No air quality data found for {city_name}"
    
    # Store the data frame for laster use by the plot function
    last_city_data[city_name.lower()] = df
    
    # Convert to a readable string format
    summary = f"Found {len(df)} air quality monitoring locations in {city_name}:\n\n"
    
    for idx, row in df.iterrows():
        summary += f"Location {idx+1}: {row['Location Names']}\n"
        summary += f"  Coordinates: ({row['Latitudes']:.4f}, {row['Longitudes']:.4f})\n"
        summary += f"  Pollutants: {', '.join(row['Pollutants Measured'])}\n\n"
    
    return summary

tool_search = Tool(
    name='get_city_pollutants_and_sensors',
    func=get_city_data_for_llm,  # Use the wrapper function
    description='useful for when you need to get pollutants and sensor information for a specific city. Input should be the city name.'
)

pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_user = os.getenv("PUSHOVER_USER")
pushover_url = "https://api.pushover.net/1/messages.json"

def push(text: str):
    """Send a push notification to the user"""
    try: 
        requests.post(pushover_url, data = {"token": pushover_token, "user": pushover_user, "message": text})
    except Exception as e:
        print(f"Failed to send push notification: {e}")

tool_push = Tool(
        name="send_push_notification",
        func=push,
        description="useful for when you want to send a push notification"
    )


# Store the latest plot
latest_plot = None

def plot_city_map_return_fig(city_name: str) -> str:
    """Plot and store the figure"""
    global latest_plot
    
    city_key = city_name.lower()
    
    if city_key not in last_city_data:
        return f"Please search for {city_name} data first before plotting."
    
    city_data = last_city_data[city_key]
    
    fig = px.scatter_map(
        city_data,
        lat="Latitudes",
        lon="Longitudes",
        size='Size',
        hover_name="Location Names",
        hover_data={"Pollutants Measured": True, "Latitudes": False, "Longitudes": False, "Size": False},
        zoom=10,
        height=600
    )
    
    fig.update_layout(
        mapbox_style="open-street-map",
        title=f"Air Quality Monitoring Locations in {city_name}",
        title_x=0.5
    )
    
    latest_plot = fig
    
    return f"Map created showing {len(city_data)} air quality monitoring locations in {city_name}"  # Add marker

tool_plot = Tool(
    name='plot_city_air_quality_map',
    func=plot_city_map_return_fig,
    description='Use this to create a map visualization of air quality monitoring locations for a city. The city data must be fetched first. Input should be the city name.'
)


tools = [tool_search, tool_plot, tool_push]


class State(TypedDict):
    
    messages: Annotated[list, add_messages]


llm = ChatOpenAI(model_name="gpt-4o-mini")
llm_with_tools = llm.bind_tools(tools)

def chatbot(state: State) -> Dict[str, Any]:
    system_message = f"""You are a friendly courteous AI assistant named 'AirWatch AI Assistant' that ONLY answers questions about the air quality digital twin application.
    The app is developed by Hemanth, who is hoping to showcase his skills to potential hiring managers.
    The intent of this digital app is to attract potential hiring managers so please ensure your answers highlight the features and capabilities of the app.
    The abbrevations used in the digital twin correspond to the following pollutants along with their measurement units

    'no' is 'Nitric Oxide (NO)' measured in 'ppb,
    'no2' is 'Nitrogen Dioxide (NO2)' measured in 'µg/m³',
    'o3' is 'Ozone (O3)' measured in 'µg/m³',
    'co' is 'Carbon Monoxide (CO)' measured in 'µg/m³',
    'so2' is 'Sulfur Dioxide (SO2)' measured in 'µg/m³',
    'temperature' is 'Temperature' measured in 'c',
    'pm25' is 'Particulate Matter (PM2.5)' measured in 'µg/m³',
    'relativehumidity' is 'Relative Humidity' measured in '%',
    'um003' is 'Ultrafine Particles (UM003)' measured in 'particles/cm³',
    'pm10' is 'Particulate Matter (PM10)' measured in 'µg/m³',
    'pm1' is 'Particulate Matter (PM1)' measured in 'µg/m³',
    'bc' is 'Black Carbon (BC)' measured in 'µg/m³',
    'nox' is 'Nitrogen Oxides (NOx)' measured in 'ppm',
    'wind_direction' is 'Wind Direction' measured in 'degrees',
    'wind_speed' is 'Wind Speed' measured in 'm/s'


    The app  has data for four cities: Chicago, Sacramento, Bangalore and New Delhi.

    Use the following information to answer the questions about the digital app.
    This digital app has four pages. They are

    1. Data Coverage Summary 
    This page gives information on the daily coverage at each location of the selected city amongst Chicago, Sacramento, Bangalore and New Delhi. 
    It displays the pollutants available at given location within a city. The data is measured at 1 hour frequency when it is available.
    The data coverage is calculated on a daily basis as number_of_data_points_recorded/24
    The data coverage is indicated by the color. 100% data corresponds to dark green and 0% corresponds to yellow.
    To collect the data Hemanth studied the API docs of OpenAQ Inc at (https://docs.openaq.org/).
    Their generous API rate limits was sufficient for my project. So a big thanks to them.


    2. Sensor Locations and Raw data
    This page has two panels.
    On the left panel,
        - one can visualize the sensor locations in the selected city.
        - The user can select one city amongst Chicago, Sacramento, Bangalore and New Delhi to see the sensor locations on the map.
    The user can select the location  by clicking on it.

    On the right panel,
        - the top figure shows the raw pollutant levels with time at a selected location.
        - the bottom figure shows how the pollutant at the chosen location compares with the pollutants at the rest of the city locations.
    

    3. Forecasting of Average Values
    This pages is about forecasting the average value of the pollutant at a chosen city. 
    The user can select one city amongst Chicago, Sacramento, Bangalore and New Delhi to see the forecast.
    The forecast is done through Prophet. 
    The raw data is shown as black dots. The trend in the observed data is displayed as orange line, while the forecast in the future is shown in blue line.
    The blue shades indicate 95% confidence interval.

    4. Agent AirWatch
    This page is where you are now. Here users can ask questions about the air quality digital twin application.
    The users can ask about the sensors, pollutants measured for any city. Once the user about any given city, please use one of your tools.
    You can search for any city in the world to get the pollutant and sensor information.
    You can also plot the sensor locations on a map for any city.
    you can also send push notifications to the developer if needed.
    You have access to following tools
      1) Search for pollutant measurement data for any city
      2) Plot the sensor locations on a map for any city
      3) Send push notifications to the developer
    
    The conversation history so far is as follows \n
    """

    found_system_message = False
    messages = state["messages"]
    for message in messages:
        if isinstance(message, SystemMessage):
            message.content = system_message
            found_system_message = True
    
    if not found_system_message:
        messages = [SystemMessage(content=system_message)] + messages
    
    # Invoke the LLM with tools
    response = llm_with_tools.invoke(messages)
    
    # Return updated state
    return {
        "messages": [response],
    }



graph_builder = StateGraph(State)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode(tools=tools))
graph_builder.add_conditional_edges("chatbot", tools_condition, "tools")
graph_builder.add_edge("tools", "chatbot")


memory = MemorySaver()

graph = graph_builder.compile(checkpointer=memory)


config = {"configurable": {"thread_id": "10"}}

# Store chat history and latest plot
chat_history = []

layout = html.Div([
    html.H1("AirWatch AI Assistant", 
            style={'textAlign': 'center', 'color': '#1f77b4', 'padding': '20px'}),
    
    html.Div([
        # Left column - Chat interface
        html.Div([
            dcc.Loading(
                id="loading-chat",
                type="default",
                children=html.Div(id='chat-display', 
                        style={
                            'height': '500px', 
                            'overflowY': 'scroll', 
                            'border': '1px solid #ddd',
                            'padding': '10px',
                            'marginBottom': '10px',
                            'backgroundColor': '#f9f9f9'
                        })
            ),
            dcc.Input(
                id='user-input',
                type='text',
                placeholder="e.g., 'What pollutants are measured in Chicago?'",
                style={'width': '100%', 'padding': '10px', 'marginBottom': '10px', 'boxSizing': 'border-box'}
            ),
            html.Button('Send', id='send-button', n_clicks=0, 
                       style={'width': '100%', 'padding': '10px', 'marginBottom': '5px', 'backgroundColor': 'green', 'color': 'white', 'border': 'none', 'cursor': 'pointer'}),
            html.Button('Clear', id='clear-button', n_clicks=0,
                       style={'width': '100%', 'padding': '10px', 'backgroundColor': 'red', 'color': 'white', 'border': 'none', 'cursor': 'pointer'})
        ], style={
            'flex': '1',
            'minWidth': '300px',
            'padding': '10px',
            'boxSizing': 'border-box'
        }),
        
        # Right column - Map visualization
        html.Div([
            html.H3("Visualization", style={'textAlign': 'center'}),
            dcc.Graph(id='map-plot', style={'height': '700px'})
        ], style={
            'flex': '1',
            'minWidth': '300px',
            'padding': '10px',
            'boxSizing': 'border-box'
        })
    ], style={
        'display': 'flex',
        'flexWrap': 'wrap',
        'gap': '10px',
        'padding': '10px'
    }),
    
    # Store for chat history
    dcc.Store(id='chat-store', data=[])
], style={
    'maxWidth': '1800px',
    'margin': '0 auto',
    'fontFamily': 'Arial, sans-serif'
})

# Callback for sending messages
@callback(
    [Output('chat-display', 'children'),
     Output('map-plot', 'figure'),
     Output('user-input', 'value'),
     Output('chat-store', 'data')],
    [Input('send-button', 'n_clicks'),
     Input('clear-button', 'n_clicks')],
    [DashState('user-input', 'value'),
     DashState('chat-store', 'data')]
)
def update_chat(send_clicks, clear_clicks, user_message, stored_history):
    global latest_plot
    
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return [], {}, '', []
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Clear button clicked
    if button_id == 'clear-button':
        return [], {}, '', []
    
    # Send button clicked
    if button_id == 'send-button' and user_message and user_message.strip():
        # Get response from agent (synchronous wrapper for async)
        
        try:
            # Run the async function
            # Use synchronous invoke instead of async
            result = graph.invoke(
                {"messages": [{"role": "user", "content": user_message}]}, 
                config=config
            )
            
            response = result["messages"][-1].content
            
            # Update chat history
            stored_history.append({'user': user_message, 'bot': response})
                
            # Create chat display
            chat_elements = []
            for msg in stored_history:
                chat_elements.append(
                    html.Div([
                        html.Strong("You: ", style={'color': '#1f77b4'}),
                        html.Span(msg['user'])
                    ], style={'marginBottom': '10px'})
                )
                chat_elements.append(
                    html.Div([
                        html.Strong("Agent AirWatch: ", style={'color': '#2ca02c'}),
                        dcc.Markdown(msg['bot'], style={'display': 'inline-block', 'width': '100%'})
                    ], style={'marginBottom': '15px', 'paddingBottom': '10px', 'borderBottom': '1px solid #eee'})
                )
            
            # Return with latest plot if available
            fig = latest_plot if latest_plot is not None else {}
            
            return chat_elements, fig, '', stored_history
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            stored_history.append({'user': user_message, 'bot': error_msg})
            
            chat_elements = []
            for msg in stored_history:
                chat_elements.append(
                    html.Div([
                        html.Strong("You: ", style={'color': '#1f77b4'}),
                        html.Span(msg['user'])
                    ], style={'marginBottom': '10px'})
                )
                chat_elements.append(
                    html.Div([
                        html.Strong("Agent AirWatch: ", style={'color': '#d62728'}),
                        html.Span(msg['bot'])
                    ], style={'marginBottom': '15px', 'paddingBottom': '10px', 'borderBottom': '1px solid #eee'})
                )
            
            return chat_elements, {}, '', stored_history
    
    return [], {}, '', stored_history
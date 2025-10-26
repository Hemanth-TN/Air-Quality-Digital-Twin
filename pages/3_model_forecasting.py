import pandas as pd
from pathlib import Path
import plotly.express as px
from dash import Dash, callback, html, dcc, Input, Output, register_page
import plotly.graph_objects as go
from prophet import Prophet
import gc

from data_handling import get_filtered_data

import warnings
warnings.filterwarnings("ignore")

register_page(
    __name__,
    path='/Model_Forecasting',  # This page will be the homepage
    name='Forecasting of Average Values',
)

units = {'no': 'ppb',
 'no2': 'µg/m³',
 'o3': 'µg/m³',
 'co': 'µg/m³',
 'so2': 'µg/m³',
 'temperature': 'c',
 'pm25': 'µg/m³',
 'relativehumidity': '%',
 'um003': 'particles/cm³',
 'pm10': 'µg/m³',
 'pm1': 'µg/m³',
 'bc': 'µg/m³',
 'nox':'ppm',
 'no': 'ppm'}

pollutant_name = {'no': 'Nitric Oxide (NO)',
 'no2': 'Nitrogen Dioxide (NO2)',
 'o3': 'Ozone (O3)',
 'co': 'Carbon Monoxide (CO)',
 'so2': 'Sulfur Dioxide (SO2)',
 'temperature': 'Temperature',
 'pm25': 'Particulate Matter (PM2.5)',
 'relativehumidity': 'Relative Humidity',
 'um003': 'Ultrafine Particles (UM003)',
 'pm10': 'Particulate Matter (PM10)',
 'pm1': 'Particulate Matter (PM1)',
 'bc': 'Black Carbon (BC)',
 'nox':'Nitrogen Oxides (NOx)',
 'no': 'Nitric Oxide (NO)'}

layout = html.Div([
    # html.H1("Time Series Prediction of Average Values", style={'textAlign': 'center', 'color': 'blue'}),
    html.Br(),
    dcc.RadioItems(options=[ 'Chicago', 'Sacremento', 'Bangalore','New Delhi'], 
                   value='Chicago', 
                   id='city_radio', 
                   inline=True, 
                   style={'textAlign': 'center', 'marginRight': '15px'}  # Add spacing between buttons
    ),
    html.Br(),
    dcc.Dropdown(id='pollutant_dropdown_predict', multi=False, placeholder='Select a pollutant'),
    html.Br(),
    html.Div(
        dcc.Loading(
            id='loading-graph',
            type='circle',                     # spinner style: 'circle'|'dot'|'default'
            children=dcc.Graph(
                id='scatterplot_graph',
                style={'height': '1000px', 'width': '2000px'},
                config={'scrollZoom': True}
            )
        ),
    )
    ])

@callback(
    Output(component_id='pollutant_dropdown_predict', component_property='options'),
    Output(component_id='pollutant_dropdown_predict', component_property='value'),
    Input(component_id='city_radio', component_property='value'))
def update_location_dropdown(city_name):
    df = get_filtered_data(city_name)
    pollutants = list(df.columns)

    if city_name == 'Chicago':
        pollutants.remove('pm10')
    
    if city_name == "Bangalore":
        pollutants.remove('no')
        pollutants.remove('co')
        pollutants.remove('pm1')
        pollutants.remove('so2')
        pollutants.remove('um003')
    
    if city_name == "New Delhi":
        pollutants.remove('no')
        pollutants.remove('co')
        pollutants.remove('no2')
        pollutants.remove('pm1')
        pollutants.remove('um003')


    
    options = [{'label': poll, 'value': poll} for poll in pollutants]
    # Set the value to the first location by default
    value = 'temperature'
    
    return options, value


@callback(
    Output(component_id='scatterplot_graph', component_property='figure'),
    Input(component_id='city_radio', component_property='value'),
    Input(component_id='pollutant_dropdown_predict', component_property='value'))
def show_prediction(city_name, pollutant):
    df = get_filtered_data(city_name)
    df = df[pollutant].dropna().reset_index()
    df.rename({'Timestamp':'ds',pollutant: 'y'}, axis=1, inplace=True)
    df['ds'] = df['ds'].dt.tz_localize(None)
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True, 
        daily_seasonality=True,
        interval_width=0.80,      # Reduced from 0.95
        uncertainty_samples=100,   # Reduced from 1000 (10x less memory!)
        n_changepoints=15,        # Reduced from default 25
        changepoint_prior_scale=0.05,
        mcmc_samples=0,            # Disable MCMC for faster processing
        stan_backend='CMDSTANPY'
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=1500, freq='H')  # hourly frequency

    # Predict
    forecast = model.predict(future)

    train_end = df['ds'].max()          # last date in the training set
    future_only = forecast[forecast['ds'] > train_end]   # the *future* part
    train_only  = forecast[forecast['ds'] <= train_end]  # the historical part
    # train_only = train_only.resample('D', on='ds').mean().reset_index()

    # Interactive forecast plot
    fig = go.Figure()

    # Historical
    fig.add_trace(go.Scatter(x=df['ds'], y=df['y'],
                            mode='markers', name='Training points',
                            marker=dict(color='black')))
    
    #historial forecast
    fig.add_trace(go.Scatter(x=train_only['ds'], 
                             y=train_only['yhat'],
                             mode='lines', name='In-sample prediction',
                                line=dict(color='orange')))

    # Future forecast
    fig.add_trace(go.Scatter(x=future_only['ds'], y=future_only['yhat'],
                            mode='lines', name='Future forecast',
                            line=dict(color='steelblue')))

    # Confidence band
    fig.add_trace(go.Scatter(x=list(future_only['ds']) + list(future_only['ds'])[::-1],
                            y=list(future_only['yhat_upper']) + list(future_only['yhat_lower'])[::-1],
                            fill='toself', fillcolor='rgba(70, 130, 180, 0.2)',
                            line=dict(color='rgba(255,255,255,0)'),
                            name='confidence bounds',
                            hoverinfo='skip', showlegend=True))

    fig.update_layout(title=dict(text=f"{city_name} - Trend and forecast of {pollutant_name[pollutant]}",
                            x=0.5,
                            font=dict(color='black', size=24)),
                    xaxis_title='Date', yaxis_title=units[pollutant], width=2000, height=1000)
    
    del forecast, future, model
    gc.collect()  # Force garbage collection

    return fig
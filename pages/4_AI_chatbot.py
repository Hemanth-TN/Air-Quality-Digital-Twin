import os
import dash
from dash import html, dcc, Input, Output, State, callback, Dash, register_page
from embedchain import App


register_page(
    __name__,
    path='/Chatbox',  # This page will be the homepage
    name='Chatbot Interface',
)


ai_bot = App.from_config(config_path="config.yaml")

# Embed resources: websites, PDFs, videos

ai_bot.add("digital_twin_explanation.txt", data_type='text_file')



layout = html.Div([
    html.H3('Helpful AI Chatbot'),
    html.Label('Ask your question:'),
    html.Br(),
    dcc.Textarea(id='question-area', value=None, style={'width': '25%', 'height': 100}),
    html.Br(),
    html.Button(id='submit-btn', children='Submit'),
    dcc.Loading(id="load", children=html.Div(id='response-area', children='')),
])

@callback(
    Output('response-area', 'children'),
    Input('submit-btn', 'n_clicks'),
    State('question-area', 'value'),
    prevent_initial_call=True
)
def create_response(_, question):
    # What kind of glass should I use to keep birds safe from window collisions?
    answer = ai_bot.query(question)
    return answer
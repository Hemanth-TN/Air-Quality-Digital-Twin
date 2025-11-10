import os
import dash
from dash import html, dcc, Input, Output, State, callback, Dash, register_page
from embedchain import App


register_page(
    __name__,
    path='/Chatbox',
    name='Chatbot Interface',
)


ai_bot = App.from_config(config_path="config.yaml")

ai_bot.add("digital_twin_explanation.txt", data_type='text_file')


layout = html.Div([
    html.H3('Helpful AI Chatbot', style={
        'textAlign': 'center',
        'marginBottom': '20px',
        'fontSize': 'clamp(1.2rem, 5vw, 2rem)'  # Responsive font size
    }),
    html.Label('Ask your question:', style={
        'fontSize': 'clamp(0.9rem, 3vw, 1.1rem)',
        'marginBottom': '10px'
    }),
    html.Br(),
    dcc.Textarea(
        id='question-area',
        value=None,
        placeholder='Type your question here...',
        style={
            'width': '100%',  # Full width on all screens
            'maxWidth': '800px',  # Max width for large screens
            'height': '120px',
            'padding': '10px',
            'fontSize': '16px',  # Prevents zoom on iOS
            'borderRadius': '5px',
            'border': '1px solid #ccc',
            'resize': 'vertical'
        }
    ),
    html.Br(),
    html.Button(
        id='submit-btn',
        children='Submit',
        style={
            'padding': '12px 30px',
            'fontSize': '16px',
            'backgroundColor': '#007bff',
            'color': 'white',
            'border': 'none',
            'borderRadius': '5px',
            'cursor': 'pointer',
            'width': '100%',
            'maxWidth': '200px',
            'marginTop': '10px'
        }
    ),
    dcc.Loading(
        id="load",
        type="default",
        children=html.Div(
            id='response-area',
            children='',
            style={
                'marginTop': '20px',
                'width': '100%',
                'maxWidth': '800px'
            }
        )
    ),
], style={
    'padding': '20px',
    'maxWidth': '1200px',
    'margin': '0 auto',
    'display': 'flex',
    'flexDirection': 'column',
    'alignItems': 'center',
    'boxSizing': 'border-box'
})

@callback(
    Output('response-area', 'children'),
    Input('submit-btn', 'n_clicks'),
    State('question-area', 'value'),
    prevent_initial_call=True
)
def create_response(_, question):
    answer = ai_bot.query(question)
    return dcc.Markdown(
        answer,
        style={
            'padding': '20px',
            'backgroundColor': '#f5f5f5',
            'borderRadius': '5px',
            'width': '100%',
            'wordWrap': 'break-word',  # Prevents text overflow
            'overflowX': 'auto',  # Allows horizontal scroll for code blocks
            'fontSize': 'clamp(0.9rem, 2.5vw, 1rem)',
            'lineHeight': '1.6'
        }
    )
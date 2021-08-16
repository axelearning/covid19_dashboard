from flask_caching import Cache
from helper.utils import prettify_number
from helper.data_preparation import filter_by_dates, sumurize_by_country, filter_df, get_daily_case
from data.collect_data import collect_data
import collections
import os
from dotenv import load_dotenv

import pandas as pd
import numpy as np

import dash
from dash import Dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input

import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
pio.templates.default = "plotly_white"


load_dotenv()
MAPBOX_TOKEN = os.environ.get('MAPBOX_TOKEN')

DEFAULT_MARGIN = dict(l=10, r=10, t=10, b=10)

EXTERNAL_STYLESHEETS = [dbc.themes.BOOTSTRAP, "assets/test.css"]
app = Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS,  meta_tags=[
           {"name": "viewport", "content": "width=device-width, initial-scale=1"}])
server = app.server

# Refresh and cache the data every H hours
cache = Cache(server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
})
HOURS = 24
TIMEOUT = HOURS*60*60
FILE_PATH = 'data/spreading_covid19.csv'


@cache.memoize(timeout=TIMEOUT)
def refresh_data(FILE_PATH):
    collect_data(saving_path=FILE_PATH)
    return True


# Load the file
covid19 = pd.read_csv(FILE_PATH, parse_dates=['Date'])
countries = covid19['State'].unique()

# Colors
RED = '#ed1d30'
BLUE = '#2e72ff'
GREY = "#6c757d"
COLORS = px.colors.qualitative.Plotly
COLORS = px.colors.qualitative.Plotly * int(len(countries)/len(COLORS)+1)


'''-------------------------------------------------------------------------------------------
                                            LAYOUT
   -------------------------------------------------------------------------------------------
'''

title = html.H1('Spreading of COVID19 🦠', className='title')

country_dropdown = dcc.Dropdown(
    id='country_dropdown',
    options=[{'label': country, 'value': country} for country in countries],
    multi=True,
    value=None,
    placeholder='Search a Location')

time_dropdown = dcc.Dropdown(
    id='time_dropdown',
    options=[
        {'label': 'All time', 'value': 0},
        {'label': '90 days', 'value': 90},
        {'label': '30 days', 'value': 30},
        {'label': '14 days', 'value': 15},
    ],
    searchable=False,
    clearable=False,
    value=0)

filters = html.Div(
    children=[country_dropdown,
              time_dropdown],
    className='filters'
)
one_line_report = dcc.Markdown(
    id='one_line_report'
)

header = html.Div([title, filters, one_line_report], className='header')

remove_buton = ["resetViewMapbox", "", "toImage", "", "", "toggleHover"]
MAP_CONFIG = {'modeBarButtonsToRemove': remove_buton,
              'showAxisDragHandles': False, "displayModeBar": True, "displaylogo": False}
DASH_CONFIG = {'displayModeBar': False, 'showAxisDragHandles': False}

card_map = dcc.Graph(id="maps", config=MAP_CONFIG, className='card')
card_virality = dcc.Graph(
    id="virality_plot", config=DASH_CONFIG, className='card')
detailed_pot = dcc.Graph(id="detailed_plot",
                         config=DASH_CONFIG, className='card')

first_row = html.Div([card_map, card_virality], id='first_row')
cards = html.Div([first_row, detailed_pot],
                 className='cards')


app.layout = html.Div([
    header,
    cards
])


'''-------------------------------------------------------------------------------------------
                                            INTERACT
   -------------------------------------------------------------------------------------------
'''
selected_country = []


@app.callback(
    Output('country_dropdown', 'value'),
    [
        Input('maps', 'clickData'),
        Input('maps', 'selectedData')
    ]
)
def map_selection(click, selected):
    context = dash.callback_context
    condition = context.triggered[0]["prop_id"].split(".")[-1]
    global selected_country

    if condition == "clickData":
        selected_country.append(click["points"][0]["text"])
        # delete the duplicate clicked countries
        selected_country = [country for country, count in collections.Counter(
            selected_country).items() if count <= 1]
        return selected_country

    if condition == "selectedData":
        return [country["text"] for country in selected["points"]]
    # reset the list
    selected_country = []
    return None


@app.callback(
    [
        Output('one_line_report', 'children'),
        Output('maps', 'figure'),
        Output('virality_plot', 'figure'),
        Output('detailed_plot', 'figure'),
    ],
    [
        Input('country_dropdown', 'value'),
        Input('time_dropdown', 'value'),
    ]
)
def global_update(countries, time_range):
    if refresh_data(FILE_PATH):
        covid19 = pd.read_csv(FILE_PATH, parse_dates=['Date'])

    filtered_df = filter_df(covid19, countries, time_range)
    report_by_country = sumurize_by_country(filtered_df)
    daily_cases = get_daily_case(filtered_df)

    # link clicked country and country dropdown to have a smooth interactive clicking map
    global selected_country
    selected_country = countries
    if not selected_country:
        selected_country = []

    # MAP
    # --------------------------------------------------------
    df_map = filter_by_dates(covid19, time_range)
    df_map = sumurize_by_country(df_map)
    df_map = df_map.set_index('State')

    # Colorize marker
    if countries:
        # country_order = df_map.loc[countries].sort_values(
        # by = 'Confirmed').index
        df_map['marker_color'] = GREY
        df_map.loc[countries,
                   'marker_color'] = COLORS[: len(countries)]

    else:
        df_map['marker_color'] = BLUE

    # set the marker size
    bubble_size = df_map['Confirmed']
    bubble_size[bubble_size < 0] = 0

    map_plot = go.Figure(
        go.Scattermapbox(
            lat=df_map['Lat'],
            lon=df_map['Long'],
            customdata=np.dstack((df_map['Confirmed'], df_map['Death']))[0],
            text=df_map.index,
            marker=dict(
                color=df_map['marker_color'],
                size=bubble_size,
                sizemode='area',
                sizemin=2,
                sizeref=2. * max(bubble_size) / (40.**2),
            ),
            hovertemplate='%{customdata[0]:.3s} case<br>' +
            '%{customdata[1]:.3s} deaths<extra> %{text}</extra>'
        )
    )
    map_plot.update_layout(
        margin=DEFAULT_MARGIN,
        mapbox=dict(
            zoom=0.5,
            style='mapbox://styles/axelitorosalito/ckb2erv2q148d1jnp7959xpz0',
            accesstoken=MAPBOX_TOKEN
        ),
        showlegend=False
    )

    # VIRALITY
    # --------------------------------------------------------
    # filtering by country
    if countries:
        virality_plot = go.Figure()

        for c in countries:
            country_daily_cases = daily_cases.loc[:, c]
            country_daily_cases = country_daily_cases.rolling(
                7, min_periods=3).mean()

            virality_plot.add_traces(
                go.Scatter(
                    x=country_daily_cases.index.get_level_values('Date'),
                    y=country_daily_cases,
                    name=c,
                    customdata=country_daily_cases,
                    hovertemplate="%{customdata:.2s} cases",
                    fill='tozeroy',
                )
            )

    # Worldwide
    else:
        daily_cases = daily_cases.groupby('Date').sum()
        daily_cases = daily_cases.rolling(7, min_periods=3).mean()
        virality_plot = go.Figure(
            go.Scatter(
                x=daily_cases.index,
                y=daily_cases,
                hovertemplate="%{y:.2s} cases",
                marker_color=BLUE,
                name="World Wide",
                fill='tozeroy',
            )
        )
    # figure design
    virality_plot.update_yaxes(
        showgrid=False, nticks=5, showticklabels=False, fixedrange=True)
    virality_plot.update_xaxes(
        showline=True, nticks=5, showgrid=True, zeroline=False, fixedrange=True)
    virality_plot.update_layout(
        hovermode="x", showlegend=False, margin=DEFAULT_MARGIN)

    # DETAILED PLOT:
    # a. global : top10
    # b. by country : evolution overtime
    # --------------------------------------------------------
    if countries:
        global_evolution = filtered_df.groupby(
            ['Date', 'State']).sum().reset_index(level='Date')
        detailed_plot = go.Figure()
        for c in countries:
            detailed_plot.add_traces(
                go.Scatter(
                    x=global_evolution.loc[[c], 'Date'].map(
                        lambda x: x.strftime('%d %b %Y')),
                    y=global_evolution.loc[[c], 'Confirmed'],
                    hovertemplate='%{y:.2s} cases',
                    name=c
                )
            )
            detailed_plot.update_yaxes(
                showline=True, nticks=5, fixedrange=True)
            detailed_plot.update_xaxes(
                showline=False, nticks=5, showgrid=True, fixedrange=True)
            detailed_plot.update_layout(
                hovermode="x", margin=DEFAULT_MARGIN, showlegend=False)

    else:
        top10 = report_by_country.nlargest(10, 'Confirmed')
        top10.sort_values('Confirmed', inplace=True)

        keep_top_3 = [None] * len(top10)
        keep_top_3[-3:] = top10['Confirmed'][-3:]
        keep_top_3 = [prettify_number(x) for x in keep_top_3]

        rate_of_death = (top10['Death']/top10['Confirmed'])*100

        detailed_plot = go.Figure([
            go.Bar(
                x=top10['Confirmed'],
                y=top10['State'],
                text=keep_top_3,
                customdata=rate_of_death,
                hovertemplate='%{x:.3s} cases<extra>%{customdata:.1f}% deaths</extra>',
                marker_color=BLUE),

        ])

        detailed_plot.add_traces(
            go.Bar(
                x=top10['Death'],
                y=top10['State'],
                hoverinfo="skip",
                marker_color=RED))

        detailed_plot.update_layout(hovermode="y", showlegend=False,
                                    barmode="overlay", margin=dict(l=50, r=20, t=20, b=20, pad=10))
        detailed_plot.update_traces(textposition='auto', orientation='h')
        detailed_plot.update_xaxes(
            showgrid=False, showticklabels=False, zeroline=False, showline=False, fixedrange=True)
        detailed_plot.update_yaxes(
            showgrid=False, showline=False, fixedrange=True)

#     # COUNTERS
#     # --------------------------------------------------------
    sum_of_cases = report_by_country['Confirmed'].sum()
    sum_of_cases = prettify_number(sum_of_cases)
    sum_of_deaths = report_by_country['Death'].sum()
    sum_of_deaths = prettify_number(sum_of_deaths)

    output_tuple = (
        f'👉 **{sum_of_cases} cases** & {sum_of_deaths} deaths',
        map_plot,
        virality_plot,
        detailed_plot,
    )
    return output_tuple


if __name__ == "__main__":
    app.run_server(debug=True)

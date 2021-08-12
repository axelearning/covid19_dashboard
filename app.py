from flask_caching import Cache
from helper.utils import format_date, prettify_number
from helper.data_preparation import filter_df, sumurize_by_country, format_date, filter_by_dates
from data.collect_data import collect_data
import helper.dash_utilities as du
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

EXTERNAL_STYLESHEETS = [dbc.themes.BOOTSTRAP, "assets/main.css"]
app = Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS)
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
sum_of_cases = covid19.loc[covid19['Date'] ==
                           covid19['Date'].max(), 'Confirmed'].sum()
sum_of_deaths = covid19.loc[covid19['Date']
                            == covid19['Date'].max(), 'Death'].sum()

# Colors
RED = '#ed1d30'
BLUE = '#2e72ff'
GREY = "#6c757d"
colors = px.colors.qualitative.Plotly
colors = px.colors.qualitative.Plotly * int(len(countries)/len(colors)+1)

'''-------------------------------------------------------------------------------------------
                                        DASH COMPONENTS
   -------------------------------------------------------------------------------------------
'''
header = dbc.Row(
    children=[dbc.Col(html.H2(id='my_title'), width=8),
              dbc.Col(html.H4(id='my_date'), width=4)],
    align="center",
    justify='between',
    className='m-2')

# FILTERS
# -------------------------------------------------------------------------------------------------------

date_picker = dcc.DatePickerRange(
    id='date-picker',
    end_date=covid19['Date'].max(),
    max_date_allowed=covid19['Date'].max(),
    start_date=covid19['Date'].min(),
    min_date_allowed=covid19['Date'].min(),
)

dropdown = dcc.Dropdown(
    id='country_dropdown',
    options=[{'label': country, 'value': country} for country in countries],
    multi=True,
    value=None,
    placeholder='Choisir un pays',
    className="my-3 mx-2")

tabs = dcc.Tabs(
    id="tabs",
    value='Confirmed',
    children=[
        dcc.Tab(
            id='tab_conf',
            label=f'{sum_of_cases}',
            value='Confirmed',
            style={'color': BLUE},
            className='count-card confirmed-case',
            selected_className='count-selected count-selected-case'
        ),
        dcc.Tab(
            id='tab_death',
            label=f'{sum_of_deaths}',
            value='Death',
            style={'color': RED},
            className='count-card confirmed-death',
            selected_className='count-selected count-selected-death')
    ])

# Global filters (tabs + slider + dropdown)
filters = dbc.Row(
    [
        dbc.Col(tabs, className="mr-4"),
        dbc.Col(html.Div([date_picker, dropdown], style={
                "background-color": "white"}, className="border ml-2"))
    ],
    no_gutters=True,
    className="m-3",
    align="top"),

'''-------------------------------------------------------------------------------------------
                                            LAYOUT
   -------------------------------------------------------------------------------------------
'''

remove_buton = ["resetViewMapbox", "", "toImage", "", "", "toggleHover"]
config = {'modeBarButtonsToRemove': remove_buton,
          'showAxisDragHandles': False, "displayModeBar": True, "displaylogo": False}

card1 = du.Card(Id="map_plot", title='Map', dash_config=config)
card2 = du.Card(Id="total_case_plot", title="Global Evolution")
card3 = du.Card(Id="top10", title="Most affected countries")
card4 = du.Card(Id="new_cases", title="Virality")

card1.format(row_number=1, width=6)
card2.format(row_number=2, width=6)
card3.format(row_number=2, width=6)
card4.format(row_number=1, width=6)
cards = [card1, card4, card3, card2]

# create the containers
container = du.Container(cards=cards).create()
container.children.insert(0, header)
container.children.insert(1, filters[0])

app.layout = container

'''-------------------------------------------------------------------------------------------
                                            INTERACT
   -------------------------------------------------------------------------------------------
'''
clicked_country = []


@app.callback(
    Output('country_dropdown', 'value'),
    [
        Input('map_plot', 'clickData'),
        Input('map_plot', 'selectedData')
    ]
)
def update_dropwdown(click, selected):
    context = dash.callback_context
    condition = context.triggered[0]["prop_id"].split(".")[-1]
    global clicked_country

    if condition == "clickData":
        clicked_country.append(click["points"][0]["text"])
        # delete the duplicate clicked countries
        clicked_country = [country for country, count in collections.Counter(
            clicked_country).items() if count <= 1]
        return clicked_country

    if condition == "selectedData":
        return [country["text"] for country in selected["points"]]
    # reset the list
    clicked_country = []
    return None


@app.callback(
    [
        Output('my_title', 'children'),
        Output('my_date', 'children'),
        Output('tab_conf', 'label'),
        Output('tab_death', 'label'),
        Output('map_plot', 'figure'),
        Output('total_case_plot', 'figure'),
        Output('new_cases', 'figure'),
        Output('top10', 'figure'),
    ],
    [
        Input('date-picker', 'start_date'),
        Input('date-picker', 'end_date'),
        Input('tabs', 'value'),
        Input('country_dropdown', 'value'),
    ]
)
def global_update(start_date, end_date, tabs_type, country_dropdown):
    if refresh_data(FILE_PATH):
        covid19 = pd.read_csv(FILE_PATH, parse_dates=['Date'])

    filtered_df = covid19.pipe(filter_df, start_date,
                               end_date, country_dropdown)
    report_by_country = sumurize_by_country(filtered_df)
    sum_of_cases = filtered_df['Confirmed'].sum()
    sum_of_deaths = filtered_df['Death'].sum()

    # colors and legend depending on tabs
    if tabs_type == 'Death':
        other, marker_color, type_value = "Confirmed", RED, 'deaths'
    else:
        other, marker_color, type_value = "Death", BLUE, 'case'

    # link clicked country and country dropdown to have a smooth interactive clicking map
    global clicked_country
    clicked_country = country_dropdown
    if not clicked_country:
        clicked_country = []

    # MAP
    # --------------------------------------------------------
    df_map = filter_by_dates(covid19, start_date, end_date)
    df_map = sumurize_by_country(df_map)
    df_map = df_map.set_index('State')

    # Colorize marker
    if country_dropdown:
        country_order = df_map.loc[country_dropdown].sort_values(
            by=tabs_type).index
        df_map['marker_color'] = GREY
        df_map.loc[country_order,
                   'marker_color'] = colors[:len(country_dropdown)]
    else:
        df_map['marker_color'] = marker_color

    # set the marker size
    bubble_size = df_map[tabs_type]
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

    # Top 10
    # --------------------------------------------------------
    if country_dropdown:
        top10 = report_by_country.nlargest(len(country_dropdown), tabs_type)
        top10.set_index('State', inplace=True)

        top10_plot = go.Figure()
        for c in country_order:
            top10_plot.add_traces(go.Bar(
                x=[top10.loc[c, tabs_type]],
                y=[c],
                hovertemplate='%{x:.3s} ' + type_value + '<extra></extra>'))

    else:
        top10 = report_by_country.nlargest(10, tabs_type)
        top10.sort_values(tabs_type, inplace=True)

        keep_top_3 = [None] * len(top10)
        keep_top_3[-3:] = top10[tabs_type][-3:]
        keep_top_3 = [prettify_number(x) for x in keep_top_3]

        top10_plot = go.Figure([
            go.Bar(
                x=top10[tabs_type],
                y=top10['State'],
                text=keep_top_3,
                hovertemplate='%{x:.3s} ' + type_value + '<extra></extra>',
                marker_color=marker_color),

        ])

        if tabs_type == "Confirmed":
            top10_plot.add_traces(
                go.Bar(
                    x=top10[other],
                    y=top10['State'],
                    hoverinfo="skip",
                    marker_color=RED))

    top10_plot.update_layout(hovermode="y", showlegend=False,
                             barmode="overlay", margin=dict(l=50, r=20, t=20, b=20, pad=10))
    top10_plot.update_traces(textposition='auto', orientation='h')
    top10_plot.update_xaxes(
        showgrid=False, showticklabels=False, zeroline=False, showline=False)
    top10_plot.update_yaxes(showgrid=False, showline=False)

    # Global_evolution
    # --------------------------------------------------------
    # filtering by country
    if country_dropdown:
        global_evolution = filtered_df.groupby(
            ['Date', 'State']).sum().reset_index(level='Date')
        total_case = go.Figure()
        for c in country_order:
            total_case.add_traces(
                go.Scatter(
                    x=global_evolution.loc[[c], 'Date'].map(
                        lambda x: x.strftime('%d %b %Y')),
                    y=global_evolution.loc[[c], tabs_type],
                    hovertemplate='%{y:.2s} ' + type_value,
                    name=c
                )
            )

    # global cases
    else:
        global_evolution = filtered_df.groupby('Date').sum().reset_index()
        total_case = go.Figure(
            go.Scatter(
                x=global_evolution['Date'].map(
                    lambda x: x.strftime('%d %b %Y')),
                y=global_evolution[tabs_type],
                hovertemplate='%{y:.2s} ' + type_value,
                marker_color=marker_color,
                name="Monde",

            )
        )
    # figure design
    total_case.update_yaxes(showline=True, nticks=5)
    total_case.update_xaxes(showline=False, nticks=5, showgrid=True)
    total_case.update_layout(
        hovermode="x", margin=DEFAULT_MARGIN, showlegend=False)

    # VIRALITY
    # --------------------------------------------------------
    daily_cases = filtered_df.set_index(['Date', 'State'])
    daily_cases = daily_cases[tabs_type].diff().fillna(0)
    daily_cases[daily_cases < 0] = 0

    # filtering by country
    if country_dropdown:
        new_cases_plot = go.Figure()

        for c in country_order:
            country_daily_cases = daily_cases.loc[:, c]
            country_daily_cases = country_daily_cases.resample('7D').sum()
            country_daily_cases = country_daily_cases[:-1]

            new_cases_plot.add_traces(
                go.Scatter(
                    x=country_daily_cases.index,
                    y=country_daily_cases,
                    name=c,
                    customdata=country_daily_cases,
                    hovertemplate="%{customdata:.2s} " +
                    type_value + "<br> 7-day average ",
                    fill='tozeroy',
                    line_shape='spline'
                )
            )

    # global cases
    else:
        daily_cases = daily_cases.groupby('Date').sum()
        daily_cases = daily_cases.resample('7D').sum()
        daily_cases = daily_cases[:-1]
        new_cases_plot = go.Figure(
            go.Scatter(
                x=daily_cases.index,
                y=daily_cases,
                hovertemplate="%{y:.2s} " + type_value + "<br> 7-day average ",
                marker_color=marker_color,
                name="Monde",
                fill='tozeroy',
                line_shape='spline',
            )
        )
    # figure design
    new_cases_plot.update_yaxes(
        showgrid=False, nticks=5, showticklabels=False, )
    new_cases_plot.update_xaxes(
        showline=True, nticks=5, showgrid=True, zeroline=False)
    new_cases_plot.update_layout(
        hovermode="x", showlegend=False, margin=DEFAULT_MARGIN)

    # Output
    # --------------------------------------------------------
    str_start_date = format_date(start_date, '%d %B %Y')
    str_end_date = format_date(end_date, '%d %B %Y')
    color_title_part = html.Span(
        children='COVID-19', style={'color': marker_color})

    output_tuple = (
        ['Spreading of ', color_title_part],
        '{} to {}'.format(str_start_date, str_end_date),
        f'{prettify_number(sum_of_cases)}',
        f'{prettify_number(sum_of_deaths)}',
        map_plot,
        total_case,
        new_cases_plot,
        top10_plot
    )
    return output_tuple


if __name__ == "__main__":
    app.run_server(debug=True)

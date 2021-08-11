from helper.utils import prettify_number, format_date
import helper.dash_utilities as du
import collections
import os
from dotenv import load_dotenv

import pandas as pd
import numpy as np
from dateutil.parser import parse

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

# Load the file
FILE_PATH = 'data/spreading_covid19.csv'
covid19 = pd.read_csv(FILE_PATH)
countries = covid19['State'].unique()
dates = covid19['Date'].unique()
last_date = dates.max()
cases_counter = covid19.loc[covid19['Date'] == last_date, 'Confirmed'].sum()
death_counter = covid19.loc[covid19['Date'] == last_date, 'Death'].sum()

# Colors
RED = '#ed1d30'
BLUE = '#2e72ff'
GREY = "#6c757d"
colors = px.colors.qualitative.Plotly
colors = px.colors.qualitative.Plotly * int(len(countries)/len(colors)+1)

EXTERNAL_STYLESHEETS = [dbc.themes.BOOTSTRAP, "assets/main.css"]
app = Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS)
server = app.server


'''-------------------------------------------------------------------------------------------
                                        DASH COMPONENTS
   -------------------------------------------------------------------------------------------
'''

# HEADERS
# -------------------------------------------------------------------------------------------------------
header = dbc.Row(
    children=[dbc.Col(html.H2(id='my_title'), width=8),
              dbc.Col(html.H4(id='my_date'), width=4)],
    align="center",
    justify='between',
    className='m-2')

# FILTERS
# -------------------------------------------------------------------------------------------------------
# slider
marks = {}
for i, date in enumerate(dates):
    if parse(date).day == 1:
        marks[i] = ''
        if parse(date).month == 1:
            marks[i] = format_date(date, '%Y')


slider = dcc.RangeSlider(
    id='date_slider',
    count=1,
    min=0,
    max=len(dates)-1,
    marks=marks,
    value=[0, len(dates) - 1],
    className="my-3")

# dropdown
dropdown = dcc.Dropdown(
    id='country_dropdown',
    options=[{'label': country, 'value': country} for country in countries],
    multi=True,
    value=None,
    placeholder='Choisir un pays',
    className="my-3 mx-2")

# tabs
tabs = dcc.Tabs(
    id="tabs",
    value='Confirmed',
    children=[
        dcc.Tab(
            id='tab_conf',
            label=f'{cases_counter}',
            value='Confirmed',
            style={'color': BLUE},
            className='count-card confirmed-case',
            selected_className='count-selected count-selected-case'
        ),
        dcc.Tab(
            id='tab_death',
            label=f'{death_counter}',
            value='Death',
            style={'color': RED},
            className='count-card confirmed-death',
            selected_className='count-selected count-selected-death')
    ])

# Global filters (tabs + slider + dropdown)
filters = dbc.Row(
    [
        dbc.Col(tabs, className="mr-4"),
        dbc.Col(html.Div([slider, dropdown], style={
                "background-color": "white"}, className="border ml-2"))
    ],
    no_gutters=True,
    className="m-3",
    align="top"),

# FIGURES
# -------------------------------------------------------------------------------------------------------
# Map
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

'''-------------------------------------------------------------------------------------------
                                            LAYOUT
   -------------------------------------------------------------------------------------------
'''

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
    [Input('map_plot', 'clickData'), Input('map_plot', 'selectedData')]
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
        Input('date_slider', 'value'),
        Input('tabs', 'value'),
        Input('country_dropdown', 'value'),
    ]
)
def global_update(slider_date, tabs_type, country_dropdown):
    # 0. DESIGN
    # --------------------------------------------------------
    # date panel (top - right)
    starting_date = covid19['Date'][slider_date[0]]
    ending_date = covid19['Date'][slider_date[1]]
    min_date_panel = format_date(starting_date, '%d %B %Y')
    max_date_panel = format_date(ending_date, '%d %B %Y')

    # color and french legend
    if tabs_type == 'Death':
        other = "Confirmed"
        marker_color = RED
        type_value = 'deaths'
    else:
        other = "Death"
        marker_color = BLUE
        type_value = 'case'

    colorized_elm = html.Span(
        children='COVID-19', style={'color': marker_color})

    # 1. PREPARATION
    # --------------------------------------------------------
    # link clicked country and country dropdown to have a smooth interactive clicking map
    global clicked_country
    clicked_country = country_dropdown
    if not clicked_country:
        clicked_country = []
    # filtre by country
    df = covid19.copy()

    # TODO: delete negative death values

    # filtre by date
    min_range_slider = df.loc[df['Date'] ==
                              starting_date].reset_index(drop=True)
    max_range_slider = df[df['Date'] == ending_date].reset_index(drop=True)

    # table with last slider date
    filtred_df = max_range_slider.copy()
    numeric_column = ['Confirmed', 'Death']
    filtred_df[numeric_column] = max_range_slider[numeric_column] - \
        min_range_slider[numeric_column]

    # table with date between slider date values
    slice_df = df[df['Date'] <= df['Date'][slider_date[1]]]
    slice_df = slice_df[slice_df['Date'] >= slice_df['Date']
                        [slider_date[0]]].reset_index(drop=True)

    # Filtering by the interactive map's selection
    # --------------------------------------------------------
    if country_dropdown:
        filtred_df = filtred_df[filtred_df["State"].isin(country_dropdown)]
        slice_df = slice_df[slice_df["State"].isin(country_dropdown)]
        country_order = filtred_df.groupby(
            'State').sum().sort_values(by=tabs_type).index

    # key values
    cases_counter = filtred_df['Confirmed'].sum()
    death_counter = filtred_df['Death'].sum()

    # 2. MAP
    # --------------------------------------------------------
    df_map = filtred_df.copy()
    df_map["color"] = [BLUE] * \
        len(df_map) if tabs_type == 'Confirmed' else [RED] * len(df_map)

    # hiligh select country
    if country_dropdown:
        df_map["color"] = np.array([GREY] * len(df_map))
        df_map.loc[df_map["State"].isin(
            country_dropdown), "color"] = colors[:len(country_dropdown)]

    # set the marker size
    bubble_size = df_map.set_index('State')[tabs_type]
    bubble_size[bubble_size < 0] = 0
    # plot
    map_plot = go.Figure(
        go.Scattermapbox(
            lat=df_map['Lat'],
            lon=df_map['Long'],
            customdata=np.dstack((df_map['Confirmed'], df_map['Death']))[0],
            text=df_map['State'],
            marker=dict(
                color=df_map["color"],
                size=bubble_size,
                sizemode='area',
                sizemin=2,
                sizeref=2. * max(bubble_size) / (40.**2),
            ),
            hovertemplate='%{customdata[0]:.3s} case<br>' +
            '%{customdata[1]:.3s} deaths<extra> %{text}</extra>'
        )
    )

    # figure design
    map_plot.update_layout(
        margin=DEFAULT_MARGIN,
        mapbox=dict(
            zoom=0.5,
            style='mapbox://styles/axelitorosalito/ckb2erv2q148d1jnp7959xpz0',
            accesstoken=MAPBOX_TOKEN
        ),
        showlegend=False
    )

    # 3. Top 10
    # --------------------------------------------------------
    top10 = filtred_df.groupby(['State', 'Date']).sum().reset_index()
    if country_dropdown:
        top10 = top10.nlargest(len(country_dropdown), tabs_type)
        top10.set_index('State', inplace=True)
        # plot
        top10_plot = go.Figure()
        for c in country_order:
            top10_plot.add_traces(go.Bar(
                x=[top10.loc[c, tabs_type]],
                y=[c],
                hovertemplate='%{x:.3s} ' + type_value + '<extra></extra>'))

    else:
        top10 = top10.nlargest(10, tabs_type)
        top10.sort_values(tabs_type, inplace=True)

        keep_top_3 = [None] * len(top10)
        keep_top_3[-3:] = top10[tabs_type][-3:]
        keep_top_3 = [prettify_number(x) for x in keep_top_3]
        # plot
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

    # 4. Cases over time
    # --------------------------------------------------------
    # filtering by country
    if country_dropdown:
        global_increase = slice_df.groupby(
            ['Date', 'State']).sum().reset_index(level='Date')
        total_case = go.Figure()
        for c in country_order:
            total_case.add_traces(
                go.Scatter(
                    x=global_increase.loc[[c], 'Date'].map(
                        lambda x: format_date(x, '%d %b %y')),
                    y=global_increase.loc[[c], tabs_type],
                    hovertemplate='%{y:.2s} ' + type_value,
                    name=c
                )
            )

    # global cases
    else:
        global_increase = slice_df.groupby('Date').sum().reset_index()
        total_case = go.Figure(
            go.Scatter(
                x=global_increase['Date'].map(
                    lambda x: format_date(x, '%d %b %y')),
                y=global_increase[tabs_type],
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

    # 5. Daily Cases
    # --------------------------------------------------------
    # create 'new_cases' and 'new_deaths'
    daily_cases = slice_df.copy()
    columns = ['Confirmed', 'Death']

    def comput_diff(df, columns=columns):
        return df[columns] - df[columns].shift(1)
    daily_cases[['new_cases', 'new_deaths']] = daily_cases.groupby(
        'State').apply(comput_diff)
    daily_cases.fillna(0, inplace=True)
    new_type = 'new_cases' if tabs_type == 'Confirmed' else 'new_deaths'
    daily_cases['Date'] = pd.to_datetime(daily_cases['Date'])
    daily_cases.set_index('Date', inplace=True)

    # filtering by country
    if country_dropdown:
        new_cases_plot = go.Figure()

        for c in country_order:
            country_daily_cases = daily_cases[daily_cases['State'] == c]
            country_daily_cases = country_daily_cases.resample('7D').sum()
            country_daily_cases = country_daily_cases[:-1]

            new_cases_plot.add_traces(
                go.Scatter(
                    x=country_daily_cases.index,
                    y=country_daily_cases[new_type],
                    name=c,
                    customdata=country_daily_cases[new_type],
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
                y=daily_cases[new_type],
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

    # 6. Output
    # --------------------------------------------------------
    output_tuple = (
        ['Spreading of ', colorized_elm],
        '{} to {}'.format(min_date_panel, max_date_panel),
        f'{prettify_number(cases_counter)}',
        f'{prettify_number(death_counter)}',
        map_plot,
        total_case,
        new_cases_plot,
        top10_plot,
        # f'Evolution du nombre total de {type_value}',
        # f'Taux de nouveau {type_value}'
    )
    return output_tuple


if __name__ == "__main__":
    app.run_server(debug=True)

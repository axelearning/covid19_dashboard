from dash.dependencies import Output, Input, State
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash
import numpy as np

# PLOTLY
import plotly.express as px
import plotly.io as pio
pio.templates.default = "plotly_white"


class Card:
    def __init__(self, Id=None, graph=None, title=None, tooltip=None, zoom=False,  dash_config={'displayModeBar': False, 'showAxisDragHandles': False}):
        #  graph
        self.graph = dcc.Graph(config=dash_config, style={"width": "100%"})
        if Id:
            self.graph.id = Id
        if graph:
            self.graph.figure = graph
        # header
        self.header = []
        self.title = title
        self.tooltip = self.create_tooltip(tooltip) if tooltip else None

        self.zoom = self.create_modal() if zoom else None

        # format
        self.width = True  # default
        self.row_number = None

    def add_title(self):
        self.header.append(dbc.Col(html.H2(
            self.title, className="m-0"), width="auto", align="left"))

    def create_tooltip(self, tooltip):
        return [
            dbc.Button(
                "?",
                className="border rounded-circle",
                id=f"tooltip-target-{self.graph.id}",
                style={"border-color": "grey"}, outline=True,
            ),
            dbc.Tooltip(tooltip, target=f"tooltip-target-{self.graph.id}",
                        placement="left", style={"background-color": "grey"})
        ]

    def add_info(self):
        self.header.append(
            dbc.Col(self.tooltip, align="center",  width="auto"))

    def create_modal(self):
        return html.Div([
            dbc.Button("⇱ ", id=f"{self.graph.id}open-centered",
                       className="border rounded-circle",  outline=True,),
            dbc.Modal([
                dbc.ModalHeader(dbc.Row([
                    dbc.Col(html.H2(self.title), width="auto",
                            className="border", align="center"),
                    dbc.Col(dbc.Button("x", id=f"{self.graph.id}close-centered", outline=True, className="border rounded-circle ml-auto"))],
                    justify="end")),
                dbc.ModalBody(self),
            ],
                id=f"{self.graph.id}modal-centered",
                centered=True),
        ])

    def create_header(self):
        if self.title:
            self.add_title()
        if self.tooltip:
            self.add_info()
        return dbc.Row(self.header, className="d-flex justify-content-between m-2", align="center")

    # create the card
    # ____________________________________________________________
    def create(self):
        return html.Div(
            [
                self.create_header(),
                html.Hr(className="m-0"),
                dbc.Row(self.graph, className="mx-4 my-2")
            ],
            className="border m-3",
            style={"background-color": "white"}
        )

    # position of the card
    # ____________________________________________________________
    def format(self, row_number=1, width=12):
        self.row_number = row_number
        self.width = width


class Header:
    """
        >> ATTRIBUTES <<
        ---------------------------------------------------------------------------------------------
                * title: title of the dashboard
            * elm:  elements inside the side bars
            * header: header 

        >> OUTPUT <<
        -------------------------------------------------------
        Create the header of the dash
    """

    def __init__(self, title, elm=False):
        self.title = title
        self.elm = elm
        self.header = self.create()

    # create header
    def main(self):
        return dbc.Row(dbc.Col(html.H1(self.title, className="ml-3 my-2", style={"color": "white"}), style={"background-color": "#0077b6"}))

    # create a sub header
    def sub(self):
        sub = dbc.Row(
            [], style={"background-color": "white"}, className="border-bottom")
        for filter in self.elm:
            sub.children.append(
                dbc.Col(filter, width=2, className="my-2 ml-3"))
        return sub

    def create(self):
        header = html.Div([self.main()])
        if self.elm:
            header.children.append(self.sub())
        return header


class Container:
    """
        >> ATTRIBUTES <<
        ---------------------------------------------------------------------------------------------
                * cards: a list of card component difine with there row's location (num_row) and there width (width)
                * row_dim: list of string which describe the height of each row
            * margin: set the margin between the cards (0<=int<=5, default=4)
            * backgorund_color: color of the background ( str, default="white")

        >> OUTPUT <<
        -------------------------------------------------------
        Create the panel where we organise all our cards. This is the core of our dashboard
    """

    def __init__(self, cards, header=None, background_color="#fafafa"):
        self.cards = cards
        self.header = header
        self.background_color = background_color

    def info(self):
        print("CONTAINER:")
        print("---------------")
        print(f"background color: {self.background_color}")
        for i, card in enumerate(self.cards):
            print("")
            print(f"CARD #{i}")
            print(f"\ttitle:{card.title.children}")
            print(f"\t width: {card.width}")
            print(f"\t height: {card.height}")
            print(f"\t row's number: {card.row_number}")

    def row(self, n):
        cards = [card for card in self.cards if card.row_number == n]
        row = dbc.Row(
            children=[],
            style={"background-color": self.background_color},
            no_gutters=True,
            # className="border"
        )
        for card in cards:
            row.children.append(dbc.Col(card.create(), width=card.width))
        return row

    def create(self, height="auto"):
        n_row = max([card.row_number for card in self.cards])
        container = html.Div(
            [], style={"height": height, "background-color": self.background_color})
        if self.header:
            container.children.append(self.header)
        for row in range(n_row):
            container.children.append(self.row(row+1))
        return container


if __name__ == '__main__':
    external_stylesheets = [dbc.themes.BOOTSTRAP, "assets/test.css"]
    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    server = app.server

    # create a simple graph
    df = px.data.iris()  # iris is a pandas DataFrame
    fig = px.scatter(df, x="sepal_width", y="sepal_length")
    fig.update_layout(margin=dict(l=20, r=20, t=10, b=10))

    # create cards
    card1 = Card(fig, title="Okay", zoom=True, tooltip="try")
    card1.format(row_number=1, width=5)

    card3 = Card(fig, title="OKO", zoom=True, tooltip="trwe")
    card3.format(row_number=1, width=7)

    card2 = Card(fig, title="attention", zoom=True, tooltip="test")
    card2.format(row_number=2, width=12)

    cards = [card2, card1, card3]

    # header
    # header elements
    dropdown = dcc.Dropdown(
        options=[{'label': 'New York City', 'value': 'NYC'}, {
            'label': 'Montréal', 'value': 'MTL'},  {'label': 'San Francisco', 'value': 'SF'}],
        value='MTL', clearable=False)
    slider = dcc.Slider(id='my-slider', min=0, max=20, step=0.5, value=10),
    header = Header("Crise Covid", elm=[dropdown, dropdown, dropdown])

    # dashboard
    container = Container(header.header, cards)
    app.layout = container.create()

    app.run_server(debug=True)

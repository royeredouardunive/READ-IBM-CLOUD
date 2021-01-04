import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
#import numpy as np
import pycloudmessenger.castor.castorapi as castorapi
import sys
sys.path.append("../..")  # work around to add locally available pycloudmessenger to path
import logging

from dash.dependencies import Input, Output
from plotly import graph_objs as go
from plotly.graph_objs import *
from datetime import datetime as dt


app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}]
)
server = app.server


# # Plotly mapbox public token
# mapbox_access_token = "pk.eyJ1IjoicGxvdGx5bWFwYm94IiwiYSI6ImNrOWJqb2F4djBnMjEzbG50amg0dnJieG4ifQ.Zme1-Uzoi75IaFbieBDl3A"

#Dictionary of important locations in New York
list_of_sites = {
    "Preore (Italy)": "gain_unive_amqp_credentials.json",
    "Lebeche (Spain)": "gain_lebch_amqp_credentials.json" ,

}

#############
# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)-6s %(name)s %(thread)d :: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

LOGGER = logging.getLogger(__package__)

cred_file = 'gain_unive_amqp_credentials.json'
context = castorapi.CastorContext.from_credentials_file(cred_file)
df = pd.DataFrame()

try:
    with castorapi.CastorMessenger(context) as castor:
        message = castor.request_sensor_list()
        reply = castor.invoke_service(message)
        sensor_id = reply['ts_ids']
        #LOGGER.info("\n\nAvailable Sensor IDs: " + str(reply['ts_ids']) + "\n")
        data = pd.DataFrame(reply['ts_ids'], columns = ["ID"])
        data.index.name = "Index"
        data.to_csv("UNIVE dataset.csv")
        list_of_signals =[]
        for i in range(1,len(data)):
            list_of_signals.append({"label": data.iloc[i,0], "value": data.index[i]})

except Exception as err:
    LOGGER.info("Error %r", err)



# Layout of Dash App
app.layout = html.Div(
    children=[
        html.Div(
            className="row",
            children=[
                # Column for user controls
                html.Div(
                    className="four columns div-user-controls",
                    children=[
                        html.Img(
                            className="logo", src=app.get_asset_url("logo_gain.png")
                        ),
                        html.H2("GAIN - READ IBM DATA"),
                        html.P(
                            """This a UNIVE demo interface"""
                        ),
                        html.Div(
                            className="row",
                            children=[
                                html.Div(
                                    className="div-for-dropdown",
                                    children=[
                                        # Dropdown for locations on map
                                        dcc.Dropdown(
                                            id="location-dropdown",
                                            options=[
                                                {"label": i, "value": i}
                                                for i in list_of_sites
                                            ],
                                            placeholder="Select a pilot site",
                                        )
                                    ],
                                ),
                                html.Div(
                                    className="div-for-dropdown",
                                    children=[
                                        # Dropdown to select times
                                        dcc.Dropdown(
                                            id="signal",
                                            options= list_of_signals,
                                            placeholder="Select certain hours",
                                        )
                                    ],
                                ),
                            ],
                        ),
                        html.Div(
                            className="div-for-dropdown",
                            children=[
                                dcc.DatePickerSingle(
                                    id="date-picker-start",
                                    min_date_allowed=dt(2019, 7, 1),
                                    max_date_allowed=dt(2020, 9, 30),
                                    initial_visible_month=dt(2020, 4, 1),
                                    date=dt(2020, 4, 1).date(),
                                    display_format="MMMM D, YYYY",
                                    style={"border": "0px solid black"},
                                ),
                            ],
                        ),
                        html.Div(
                            className="div-for-dropdown",
                            children=[
                                dcc.DatePickerSingle(
                                    id="date-picker-stop",
                                    min_date_allowed=dt(2019, 7, 1),
                                    max_date_allowed=dt(2020, 9, 30),
                                    initial_visible_month=dt(2020, 4, 1),
                                    date=dt(2020, 4, 10).date(),
                                    display_format="MMMM D, YYYY",
                                    style={"border": "0px solid black"},
                                ),
                            ],
                        ),
                        # html.Div([
                        #     html.Button('Display', id='disp_data', n_clicks=0),
                        # ]),
                        # html.P(id="total-rides"),
                        # html.P(id="total-rides-selection"),
                        # html.P(id="date-value"),
                        dcc.Markdown(
                            children=[
                                "Source: [E.Royer](https://www.unive.it/data/people/20943433)"
                            ]
                        ),
                    ],
                ),
                # Column for app graphs and plots
                html.Div(
                    className="eight columns div-for-charts bg-grey",
                    children=[
                        html.Div(
                            className="text-padding",
                            children=[
                                "DATA GRAPH"
                            ],
                            style= {'textAlign':'center'}
                        ),
                        dcc.Graph(id="graph"),
                    ],
                ),
            ],
        )
    ]
)

def request_sensor_data(castor, sensor: str, from_date: str, to_date: str):
    # Function requests data for user defined sensor id and
    # date range
        #Retrieve some time series
    LOGGER.info("Requesting time series for sensor ID '%s'...", sensor)
    message = castor.request_sensor_data(sensor,from_date,to_date)
    reply = castor.invoke_service(message)
    LOGGER.info("\n\nNumber of Time Series Values: %d", reply['count'])
    df = pd.DataFrame(reply['values'],
                    columns=['Timestamp', 'SensorID', 'value','offset'])
    # Convert to pandas timestamp for visualisation
    #print(df['Timestamp'])
    Time = pd.to_datetime(df['Timestamp']).dt.tz_convert('Europe/Zurich')

    df['Timestamp'] = Time.dt.tz_localize(None)
    #df['label'] = sensor # add relevant label
    return df



@app.callback(
    Output("graph", "figure"),
    [Input("signal", "value"), Input("date-picker-start", "date"), Input("date-picker-stop", "date")])
def update_graph(value, start, stop):
    if value is not None:
        print(start)
        print(stop)
        df = pd.DataFrame()

        try:
            with castorapi.CastorMessenger(context) as castor:
                # List the devices
                LOGGER.info("Request sensor data from server")



                # Period definition
                start = "2020-06-28T00:00:00+00:00"
                stop = "2020-11-17T00:00:00+00:00"

                # WEIGHT
                sensor = request_sensor_data(castor, sensor_id[value], start, stop)
                df['Timestampin'] = sensor['Timestamp']
                df['Weigth (g)'] = sensor['value']

                # Output to graph
                fig = px.line(df, x='Timestampin', y='Weigth (g)', title=sensor_id[value])

        except Exception as err:
            LOGGER.info("Error %r", err)

    else:
        df = pd.DataFrame([1,2,3], [1,2,3])
        fig = px.line(df, title="test")

    return fig




if __name__ == "__main__":
    app.run_server(debug=True)

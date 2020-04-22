import os
import sys
import base64
import re
import requests
import json
import pandas as pd
from flask import Flask, request
from google.cloud import pubsub_v1
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

app = Flask(__name__)

##############################################################################
# Define constants
##############################################################################
# Max retyr count
MAX_RETRY_COUNT = 3

##############################################################################
# Functions for corresponding to retry
##############################################################################
def requests_retry_session(
    backoff_factor=0.3, status_forcelist=(500, 502, 504)
):
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRY_COUNT,
        read=MAX_RETRY_COUNT,
        connect=MAX_RETRY_COUNT,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

@app.route("/", methods=["GET"])
def index():
    msg = """
    [How To Use]
    """
    return msg

@app.route("/ticker/get/<location>", methods=["POST"])
def ticker_symbol_get(location):
    try:
        if location == "jp":
            symbol_list = get_ticker_symbol_jp()
        elif location == "us":
            symbol_list = get_ticker_symbol_us()
        else:
            raise ValueError("Not built yet location [{}]".format(location))
        
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(
            os.environ["GOOGLE_CLOUD_PROJECT"],
            os.environ["PUBSUB_TOPIC"]
        )
        for row in symbol_list:
            publisher.publish(
                topic_path,
                data=json.dumps(row).encode("utf-8")
            )
        return "complete to send message", 200
    except Exception as e:
        msg = """
        Occurred error to send message.\n{}
        """.format(str(e))
        print(msg)
        sys.stdout.flush()
        return msg, 500

@app.errorhandler(500)
def server_error(e):
    msg = """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e)
    print(msg)
    sys.stdout.flush()
    return msg, 500


def get_ticker_symbol_jp():
    # Getting symbols from [JPX]
    JPX_BASE_URL = "https://www.jpx.co.jp"
    JPX_SRC_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
    r = requests_retry_session().get(JPX_SRC_URL)
    soup = BeautifulSoup(r.text.encode(r.encoding), "lxml")
    link = soup.find("a", href=re.compile(".*data_j[.]xls"))
    df = pd.read_excel(JPX_BASE_URL + link["href"])
    return df.to_dict(orient="records")

def get_ticker_symbol_us():
    return_list = []
    # Getting symbols from [NYSE]
    NYSE_URL = "https://www.nyse.com/api/quotes/filter"
    # EQUITY                : Stocks
    # EXCHANGE_TRADED_FUND  : ETFs
    # INDEX                 : Indices
    # REIT                  : REITs
    instrument_types = [
        "EQUITY",
        "EXCHANGE_TRADED_FUND",
        "INDEX",
        "REIT"
    ]
    payload = {
        "instrumentType": "",
        "pageNumber": 1,
        "sortColumn": "NORMALIZED_TICKER",
        "sortOrder": "ASC",
        "maxResultsPerPage": 10000,
        "filterToken": ""
    }
    for i_type in instrument_types:
        payload["instrumentType"] = i_type
        r = requests_retry_session().post(NYSE_URL, json=payload)
        r.raise_for_status()
        return_list.extend(r.json())
    return return_list

if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0",port=int(os.environ.get("PORT", 8080)))

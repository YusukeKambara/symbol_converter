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
BASE_URL = "https://www.jpx.co.jp"
SRC_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"

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

@app.route("/get/jp", methods=["POST"])
def get():
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(
            os.environ["GOOGLE_CLOUD_PROJECT"],
            os.environ["PUBSUB_TOPIC"]
        )
        r = requests_retry_session().get(SRC_URL)
        soup = BeautifulSoup(r.text.encode(r.encoding), "lxml")
        r.connection.close()
        link = soup.find("a", href=re.compile(".*data_j[.]xls"))
        df = pd.read_excel(BASE_URL + link["href"])
        for row in df.to_dict(orient="records"):
            publisher.publish(
                topic_path,
                data=json.dumps(row).encode("utf-8")
            )
        return "complete to send message"
    except Exception as e:
        print("Occurred error to send message")
        print(str(e))
        return "Occurred error to send message"

@app.errorhandler(500)
def server_error(e):
    print("An error occurred during a request.")
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500

if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0",port=int(os.environ.get("PORT", 8080)))

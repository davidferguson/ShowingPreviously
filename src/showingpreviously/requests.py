import requests
import os
from datetime import datetime
from requests import *

from showingpreviously.consts import DATA_DIR, URL_LOG_NAME


for name in ['head', 'get', 'post', 'put', 'patch', 'delete']:
    del globals()[name]


def log_url(url: str):
    log_file = datetime.now().strftime(URL_LOG_NAME)
    log_file = os.path.join(DATA_DIR, log_file)
    with open(log_file, 'a') as f:
        f.write('%s\n' % url)


def head(url, **kwargs):
    log_url(url)
    return requests.head(url, kwargs)


def get(url, params=None, **kwargs):
    log_url(url)
    return requests.get(url, params, **kwargs)


def post(url, data=None, json=None, **kwargs):
    log_url(url)
    return requests.post(url, data, json, **kwargs)


def put(url, data=None, **kwargs):
    log_url(url)
    return requests.put(url, data, **kwargs)


def patch(url, data=None, **kwargs):
    log_url(url)
    return requests.patch(url, data, **kwargs)


def delete(url, **kwargs):
    log_url(url)
    return requests.delete(url, **kwargs)

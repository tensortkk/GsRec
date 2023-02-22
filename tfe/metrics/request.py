import sys
import time
from datetime import datetime
from collections import namedtuple

from flask import g, request
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

def calculate_metrics(response):
    if "start_time" not in g:
        return response

    request_duration = (time.time() - g.start_time) * 1000
    endpoint = (request.endpoint or "unknown").replace(".", "_")
    logger.info({
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": request.method,
        "path": request.path,
        "endpoint": endpoint,
        "status": response.status_code,
        "content_type": response.content_type,
        "content_length": response.content_length or -1,
        "duration": request_duration,
        "args": dict(request.args.items())
    })
    return response


MockResponse = namedtuple(
    "MockResponse", ["status_code", "content_type", "content_length"]
)


def calculate_metrics_on_exception(error):
    if error is not None:
        calculate_metrics(MockResponse(500, "?", -1))


def before_request():
    g.start_time = time.time()


def init_app(app):
    app.before_request(before_request)
    app.after_request(calculate_metrics)
    app.teardown_request(calculate_metrics_on_exception)

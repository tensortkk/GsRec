# -*- coding: utf-8 -*-

from flask import Flask
from werkzeug.contrib.fixers import ProxyFix

from . import settings


class Hardware(Flask):
    """A custom Flask app for portal"""

    def __init__(self, *args, **kwargs):
        super(Hardware, self).__init__(__name__, *args, **kwargs)
        # Make sure we get the right referral address even behind proxies like nginx.
        self.wsgi_app = ProxyFix(self.wsgi_app, settings.PROXIES_COUNT)
        # Configure portal using our settings
        self.config.from_object("tfe.settings")


def create_app():
    from . import handlers
    from .metrics import request as request_metrics

    app = Hardware()
    request_metrics.init_app(app)
    handlers.init_app(app)
    return app

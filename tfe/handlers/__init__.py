from .api import api
from .base import routes


def init_app(app):
    app.register_blueprint(routes)
    api.init_app(app)

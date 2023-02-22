import logging

from flask import make_response
from flask_restful import Api
from werkzeug.wrappers import Response

from .all import HomeInfor
from .infer import HardwareSearch
from .base import org_scoped_rule
from tfe.util import json_dumps


logger = logging.getLogger(__name__)


class ApiExt(Api):
    def add_org_resource(self, resource, *urls, **kwargs):
        urls = [org_scoped_rule(url) for url in urls]
        return self.add_resource(resource, *urls, **kwargs)


api = ApiExt()


@api.representation("application/json")
def json_representation(data, code, headers=None):
    if isinstance(data, Response):
        return data
    resp = make_response(json_dumps(data), code)
    resp.headers.extend(headers or {})
    return resp


# index
api.add_org_resource(
    HomeInfor, "/api/index", endpoint="index"
)
# device dataset search
api.add_org_resource(
    HardwareSearch, "/api/match/<mode>", endpoint="hardware_search"
)

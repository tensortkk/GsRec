from .base import BaseHandle, infos
from tfe.settings import hardware_info

from flask import request


class HomeInfor(BaseHandle):
    def __init__(self):
        super(HomeInfor, self).__init__(request)

    def get(self):
        req = list()
        for _mode, _info in hardware_info.items():
            req.append({
                "mode": _mode, "info": _info,
                "count": len(infos.get(_mode))
            })
        return req

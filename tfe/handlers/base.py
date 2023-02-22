import json
from flask import Blueprint, abort
from flask_restful import Resource
import pandas as pd

from tfe import settings
from .mobile.model import MobileDataset
from .client.model import ClientDataset
from tfe.util.utils import takeScore


md, cd = MobileDataset(), ClientDataset()
routes = Blueprint(
    "tfe", __name__, template_folder=settings.fix_assets_path("templates")
)


class BaseHandle(Resource):
    def __init__(self, request, *args):
        self.request = request

    def args(self):
        return dict(self.request.args.items())

    def files(self):
        return self.request.files

    def form(self):
        return dict(self.request.form.items())

    def data(self):
        return json.loads(self.request.data)


def require_fields(req, fields):
    for f in fields:
        if f not in req:
            abort(400, f"{f} required")


def org_scoped_rule(rule):
    if settings.MULTI_ORG:
        return "/<org_slug>{}".format(rule)

    return rule


def h_distinct(hardware_infos):
    score_l, req, gh = list(), list(), [v for _, v in hardware_infos.items()]
    gh.sort(key=takeScore, reverse=True)
    for item in gh:
        if item.get("score") in score_l:
            continue
        score_l.append(item.get("score"))
        req.append(item)
    return req


original_infos = {
    "cpu": cd.original_cpus,
    "gpu": cd.original_gpus,
    "mobile": {**md.original_apple, **md.original_android},
    "mapping": md.merge_mapping
}
infos = dict()
for k, v in original_infos.items():
    if k not in settings.hardware_info.keys():
        continue
    infos[k] = h_distinct(v)


def default_update(alias, score_d, gh_df, cpu_gpu_d):
    add_d = {
        "rank": None,
        "gpu": "",
        "cpu": "",
        "name": alias,
        "gpu_score": None,
        "cpu_score": None,
        "recomd": True,
        "proportion": 0.00
    }
    add_d.update(cpu_gpu_d)
    if None in score_d.values():
        return add_d

    cpu_s, gpu_s = [score_d[_type].get("score") for _type in ["cpu", "gpu"]]
    _df = gh_df.loc[(gh_df["cpu_score"] == cpu_s) & (gh_df["gpu_score"] == gpu_s)]
    if _df.shape[0] > 0:
        add_d.update({
            "rank": _df.iloc[0].at["rank"],
            "cpu_score": cpu_s,
            "gpu_score": gpu_s,
            "proportion": _df.iloc[0].at["proportion"]
        })
    return add_d


def client_merge(gpi, gh, alias):
    req = [item.to_dict(True) for item in gh]
    gh_df = pd.DataFrame.from_dict(req)
    for item in gpi:
        cpu_gpu_d = {k: v for k, v in item.__dict__.items() if k in ["cpu", "gpu"]}
        if "" in cpu_gpu_d.values() or None in cpu_gpu_d.values():
            continue

        score_d = {k: cd.infer(v, k) for k, v in cpu_gpu_d.items()}
        req.insert(0, default_update(alias, score_d, gh_df, cpu_gpu_d))
    return req


def q_infer(args, mode):
    """http / sdk"""
    page = 1 if "page" not in args else int(args.get("page"))
    page_size = 10 if "page_size" not in args else int(args.get("page_size"))
    q = args.get("q")
    if mode in ["cpu", "gpu"]:
        infer_res = cd.infer(q, mode)
    else:
        infer_res = md.infer(q)
    return page, page_size, infer_res


def q_search(args, mode):
    page, page_size, infer_res = q_infer(args, mode)
    if mode == "mobile":
        f_infer_res = md.fuzzy_search(args.get("q"))
    else:
        f_infer_res = cd.fuzzy_search(args.get("q"), mode)

    for item in f_infer_res:
        if infer_res.get("name") == item.get("name"):
            return page, page_size, f_infer_res
    return page, page_size, [infer_res] + f_infer_res

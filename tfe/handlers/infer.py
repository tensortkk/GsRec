from .base import BaseHandle, q_search, md, infos
from tfe.settings import hardware_info

from flask import request, abort


class HardwareSearch(BaseHandle):
    def __init__(self):
        super(HardwareSearch, self).__init__(request)

    def get(self, mode):
        assert mode in hardware_info.keys()
        args = self.args()
        page = 1 if "page" not in args else int(args.get("page"))
        page_size = 10 if "page_size" not in args else int(args.get("page_size"))
        if "q" not in args:
            abort(400)

        if args["q"] == "":
            infer_res = infos.get(mode)
            _infer_res = infer_res[page * page_size - page_size: page * page_size]
            return {"count": len(infer_res), "data": _infer_res}

        page, page_size, infer_res = q_search(args, mode)
        if mode != "mobile":
            infer_res = [x for x in infer_res if "match_query" not in x]
            _infer_res = infer_res[page * page_size - page_size: page * page_size]
            return {"data": _infer_res, "count": len(infer_res)}

        # mobile add mapping of device model
        req = list()
        for item in infer_res:
            if "name" not in item or (item["name"] is None and item["match_query"] is None):
                continue

            _match = md.word_pre(item.get("name"))
            m_df = md.device_mode_df.loc[
                (md.device_mode_df["model"] == _match) | (md.device_mode_df["total_model"] == _match)]
            p_m_df = md.device_mode_df.loc[md.device_mode_df["pre_model_name"] == _match]
            if m_df.shape[0] != 0 or p_m_df.shape[0] != 0:
                if m_df.shape[0] > 0:
                    _df = m_df.copy()
                    item["name"] = item["match_query"] = _df.iloc[0].at["model_name"]
                else:
                    _df = p_m_df.copy()
                device, model = _df.iloc[0].at["model"], _df.iloc[0].at["model_name"]
                item.update({"device": device, "model": model})
            req.append(item)

        infer_res_l = list()
        for x in req:
            if any(str(d.get('name', None)).lower() == str(x['name']).lower() for d in infer_res_l):
                continue

            infer_res_l.append(x)
        _infer_res = infer_res_l[page * page_size - page_size: page * page_size]
        return {"data": _infer_res, "count": len(infer_res_l)}

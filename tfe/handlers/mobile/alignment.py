from model import MobileDataset

import re
import os
import json
import pandas as pd
import numpy as np

from tfe.settings import app_path
from tfe.handlers.mobile import brands

mobile_brand = {}


class geekbench(object):
    def __init__(self):
        self.origin_path = f"{app_path}/json"
        self.data = {}
        self.Mobiles = MobileDataset()

    def convert(self, list_json):
        score = {
            re.sub(
                r"\(.*?\)", "",
                item.get("name").replace("generation", "Gen").lower()).strip(): item.get(
                "multi_core_score")
            for item in list_json
        }
        return score

    def phone_data(self):
        _files = sorted(os.listdir(self.origin_path))
        for _item in _files:
            if "GeekBench" in _item:
                with open(f"{self.origin_path}/{_item}", encoding="utf-8") as f:
                    if len(self.data) != 0:
                        self.data.update(self.convert(json.load(f)))
                    else:
                        self.data = self.convert(json.load(f))
        list_brands = []
        for item in self.data.keys():
            rows = []
            rows.append(item)
            rows.append(self.data.get(item))
            item_brand = "null"
            for brand in brands:
                if brand in item:
                    item_brand = brand
                if "iphone" in item or "ipad" in item:
                    item_brand = "apple"
            rows.append(item_brand)
            passmark_infer = self.Mobiles.infer(item)
            if (passmark_infer.get("details").get("average_cpu_mark")):
                rows.append(passmark_infer.get("details").get("average_cpu_mark"))
                if(passmark_infer.get("details").get("average_cpu_mark")<self.data.get(item)):
                    continue
                list_brands.append(rows)
        score_store = pd.DataFrame(list_brands, columns=["device", "geek_score", "brand", "passscore"])
        score_store = score_store[score_store["passscore"].notna()]
        brand_score = score_store.groupby(["brand"]).agg({"geek_score": sum, "passscore": sum}).reset_index()
        brand_ratio = {}
        for idx, data in brand_score.iterrows():
            #print(idx)
            brand_ratio[data["brand"]] = np.round(data["passscore"]/data["geek_score"], 4)
        with open('brand_ratio.json', 'w') as fp:
            json.dump(brand_ratio, fp)

class phonebench(object):
    def __init__(self):
        self.origin_path = f"{app_path}/json"
        self.data = {}
        self.Mobiles = MobileDataset()

    def convert(self, list_json):
        score = {}
        for item in list_json:
            if "安卓版 PCMark 工作 3.0" in item.get("performance").keys():
                score[re.sub(r"\(.*?\)", "", item.get("name").replace("generation", "Gen").lower()).strip()] = item.get(
                "performance").get("安卓版 PCMark 工作 3.0").get("分数")

        return score

    def phone_data(self):
        _files = sorted(os.listdir(self.origin_path))
        for _item in _files:
            if "PhoneBench" in _item:
                with open(f"{self.origin_path}/{_item}", encoding="utf-8") as f:
                    if len(self.data) != 0:
                        self.data.update(self.convert(json.load(f)))
                    else:
                        self.data = self.convert(json.load(f))
        list_brands = []
        for item in self.data.keys():
            rows = []
            rows.append(item)
            rows.append(int(self.data.get(item)))
            item_brand = "null"
            for brand in brands:
                if brand in item:
                    item_brand = brand
                if "iphone" in item or "ipad" in item:
                    item_brand = "apple"
            rows.append(item_brand)
            passmark_infer = self.Mobiles.infer(item)
            if (passmark_infer.get("details").get("average_cpu_mark")):
                if int(self.data.get(item))/passmark_infer.get("details").get("average_cpu_mark") > 5:
                    continue
                if int(self.data.get(item))/passmark_infer.get("details").get("average_cpu_mark") < 2:
                    continue
                rows.append(passmark_infer.get("details").get("average_cpu_mark"))
            list_brands.append(rows)
        score_store = pd.DataFrame(list_brands, columns=["device", "phone_score", "brand", "passscore"])
        score_store = score_store[score_store["passscore"].notna()]
        brand_score = score_store.groupby(["brand"]).agg({"phone_score": sum, "passscore": sum}).reset_index()
        brand_ratio = {}
        for idx, data in brand_score.iterrows():
            brand_ratio[data["brand"]] = np.round(data["passscore"]/int(data["phone_score"]), 4)
        with open('brand_ratio_phone.json', 'w') as fp:
            json.dump(brand_ratio, fp)


if __name__ == "__main__":
    #geekbench = geekbench()
    #geekbench.phone_data()
    #Mobile = MobileDataset()
    #print(Mobile.infer("Xiaomi Redmi Note 11T 5G"))
    phone = phonebench()
    phone.phone_data()

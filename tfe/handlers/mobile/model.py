import os
import re
import csv
import json
import difflib
import pandas as pd
from itertools import groupby
from operator import itemgetter

import faiss
from bert_serving.client import BertClient

from tfe.settings import app_path, mobile_area
from tfe.handlers.mobile import brands


class Basic(object):
    def __init__(self):
        self.apple, self.original_apple = dict(), dict()
        self.android, self.original_android = dict(), dict()
        self.phonebench, self.original_phonebench = dict(), dict()
        self.geekbench, self.origin_geekbench = dict(), dict()

        self.mapping = list()
        self.origin_path = f"{app_path}/json"
        self.mobile_path = f"{app_path}/handlers/mobile"

        self.device_mode_df = pd.read_csv(
            f"{self.mobile_path}/modelmap/device_model.csv",
            header=0, quotechar='"', quoting=csv.QUOTE_ALL, sep="\t"
        )
        self.device_mode_df["model"] = self.device_mode_df["model"].apply(self.word_pre)
        self.device_mode_df["total_model"] = (
                self.device_mode_df["brand"] + self.device_mode_df["model"]).apply(self.word_pre)
        self.device_mode_df["pre_model_name"] = self.device_mode_df["model_name"].apply(self.word_pre)
        for area in mobile_area:
            _mapping = dict()
            for brand in brands:
                df = self.device_mode_df.loc[(self.device_mode_df["brand"] == brand)]
                if area != "all":
                    df = df.loc[(self.device_mode_df["area"] == area)]
                _mapping[brand] = df.set_index(["model"])["model_name"].to_dict()
            self.mapping.append(_mapping)

        with open(f"{self.mobile_path}/badcase.json", encoding="utf-8") as f:
            self.badcase = json.load(f)
        self._phone_data()

        self.model = BertClient()
        self.index = None
        self.em_input = None
        self.load_embedding()

    @staticmethod
    def merge_dicts(dict_args):
        result = dict()
        for _dict in dict_args:
            result.update(_dict)
        return result

    def convert(self, list_json, _type):
        _json, _original_json = dict(), dict()
        if _type == "apple":
            _json = {
                re.sub(r"\(.*?\)", "", item.get("name").replace(
                    "generation", "").replace("rd Gen", "nd Gen").lower()).strip(): item
                for item in list_json
            }
        else:
            _json = {self.word_pre(item.get("name")): item for item in list_json}
        for item in list_json:
            name, score = item.get("name").replace("generation", ""), item.get("score")
            _item = {"name": name, "score": score, "details": item}
            _original_json[item.get("name")] = _item
        return _json, _original_json

    def _phone_data(self):
        _files = sorted(os.listdir(self.origin_path))
        for _item in _files:
            if "Benchmarks" in _item:
                with open(f"{self.origin_path}/{_item}", encoding="utf-8") as f:
                    self.phonebench, self.original_phonebench = self.convert(json.load(f), "android")
            if "ios" in _item:
                with open(f"{self.origin_path}/{_item}", encoding="utf-8") as f:
                    self.apple, self.original_apple = self.convert(json.load(f), "apple")
            if "android" in _item:
                with open(f"{self.origin_path}/{_item}", encoding="utf-8") as f:
                    self.android, self.original_android = self.convert(json.load(f), "android")
            if "Geek" in _item:
                with open(f"{self.origin_path}/{_item}", encoding="utf-8") as f:
                    if len(self.geekbench) != 0:
                        _geek, _origingeek = self.convert(json.load(f), "android")
                        self.geekbench.update(_geek)
                        self.origin_geekbench.update(_origingeek)
                    else:
                        self.geekbench, self.origin_geekbench = self.convert(json.load(f), "android")

    @staticmethod
    def _return(item, query, brand=None, match_query=None, tag="precise", source="passmark"):
        return {
            "query": query,
            "brand": brand,
            "details": item,
            "match_query": item.get("name") if match_query is None else match_query
        }

    def word_pre(self, word, _type=None, nums=7):
        word = (
            word.lower()
                .replace("\n", "")
                .replace("\t", "")
                .replace("emerald", "")
                .replace("brown", "")
                .replace("edition", "")
                .replace("-", " ")
                .replace("mblu", "")
                .replace("+", " plus")
                .replace("0ghz", "ghz")
                .replace("cpu", "")
                .replace("huawei honor", "honor")
                .replace("entest cloudgame", "")
        )
        word = re.sub(r"\(.*?\)", "", word)
        word = " ".join(map(itemgetter(0), groupby(word.split())))
        for item in brands:
            if item in word:
                word = word.replace(item, f" {item} ")
                break
        word = re.sub("[^0-9a-zA-Z,]+", " ", word)
        word = " ".join(word.split()).strip()

        _word = word.split(" ")
        addr_to = list(set(_word))
        addr_to.sort(key=_word.index)
        word = " ".join(addr_to)
        if "iphone" in word or "ipad" in word:
            word = word.replace(" ", "").replace("apple", "")
        return " ".join(word.split(" ")[:nums])

    @staticmethod
    def find_unchinese(strs):
        pattern = re.compile(r"[\u4e00-\u9fa5]")
        return re.sub(pattern, "", strs)

    def load_embedding(self):
        self.em_input = list(self.original_apple.keys()) + list(self.original_android.keys())
        if os.path.exists(f"{self.origin_path}/phone.index"):
            self.index = faiss.read_index(f"{self.origin_path}/phone.index")
        else:
            embeddings = self.model.encode(self.em_input)
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(embeddings)
            faiss.write_index(self.index, f"{self.origin_path}/phone.index")


class BrandBasic(Basic):
    def __init__(self, query=None, brand=None):
        Basic.__init__(self)
        self.query, self.match_query, self.brand = query, None, brand

    def set(self, query, brand):
        self.query, self.brand = query, brand

    def badcase_filter(self):
        if self.brand not in self.badcase:
            return True

        for item in self.badcase[self.brand]:
            if item in self.query:
                return False
        return True

    def in_mapping(self, area):
        if self.query in self.mapping[0][self.brand]:
            self.match_query = self.query = self.word_pre(
                self.mapping[0][self.brand][self.query])
            return True
        return False

    def in_original(self, area="all", match_query=None):
        if self.brand in self.query:
            b_query = self.word_pre(self.query)
            o_query = b_query.replace(self.brand, "").strip()
        else:
            o_query = self.word_pre(self.query)
            b_query = f"{self.brand} {o_query}"
        query_l = [o_query, b_query]
        for item in [o_query, b_query]:
            tmp = list()
            if "4g" not in item and "5g" not in item:
                tmp = [f"{item} 4g", f"{item} 5g"]
            elif "4g" in item:
                tmp = [item.replace("4g", "5g").strip(), item.replace("4g", "").strip()]
            elif "5g" in item:
                tmp = [item.replace("5g", "4g").strip(), item.replace("5g", "").strip()]
            query_l += tmp

        phone = None
        for source, android in {
            "passmark": self.android,
            "phonebench": self.phonebench,
            "geekbench": self.geekbench
        }.items():
            for _query in query_l:
                if _query in self.mapping[0][self.brand]:
                    match_query = self.mapping[0][self.brand][_query]

                if self.brand == "huawei" and _query in self.mapping[0]["honor"]:
                    self.brand = "honor"
                    match_query = self.mapping[0][self.brand][_query]
                if self.brand == "honor" and _query in self.mapping[0]["huawei"]:
                    self.brand = "huawei"
                    match_query = self.mapping[0][self.brand][_query]

                if _query in android:
                    phone = android[_query]
                if phone is not None and phone.get("score") is not None:
                    return self._return(phone, _query, self.brand, match_query, source=source)
        return self._return(phone, _query, self.brand, match_query, source=source) if phone is not None else None

    def query_pro(self, *args, **kwargs):
        pass

    def regular(self, *args, **kwargs):
        pass

    def compose(self, *args, **kwargs):
        pass


class Xiaomi(BrandBasic):
    def __init__(self):
        BrandBasic.__init__(self)

    def query_pro(self):
        self.query = self.query.replace("premium ed", "")
        for item in ["mix", "max"]:
            if item in self.query:
                self.query = self.query.replace(f"xiaomi {item}", f"mi {item} ")
        for item in ["xiaomi mi", "xiaomi redmi"]:
            if item in self.query:
                self.query = self.query.replace(item, f"{item} ")
        for item in ["pro", "note"]:
            if item in self.query:
                self.query = self.query.replace(item, f" {item} ")
        self.query = self.query.replace(f"{self.brand} ", "")
        self.query = " ".join(self.query.split())

    def regular(self, area):
        if re.match(r"^k[0-9]{2}[is]*$", self.query):
            self.query = f"redmi {self.query}"
        if self.query not in self.mapping[0][self.brand]:
            pattern = r"^[0-9]{1,2}[asxict]?(\s?)[plus|pro|lite]?"
            self.query = (
                "mi " + self.query if re.match(pattern, self.query) else self.query
            )

        self.query = " ".join(self.query.split())
        if (
                self.query.startswith("mi note ")
                and not re.match(r"^mi note [12349]", self.query)
                and not re.match(r"^mi note 1[01]", self.query)
        ):
            return False
        return self.query

    def compose(self, area="all", tag="precise"):
        self.match_query = None
        if not self.badcase_filter():
            return None, self.match_query, tag

        self.query_pro()
        res = self.in_original(area)
        if res is not None:
            return res, self.match_query, tag

        if not self.regular(area):
            return None, self.match_query, tag
        if not self.in_mapping(area):
            tag = "fuzzy"
        return self.query, self.match_query, tag


class Huawei(BrandBasic):
    def __init__(self):
        BrandBasic.__init__(self)

    def query_pro(self):
        if self.query is not None and "view" in self.query:
            self.query = self.query.replace("view", " view ")
        self.query = self.query.replace(f"{self.brand} ", "")

    def regular(self, area="all"):
        if (
                self.query.startswith("bz")
                or (
                self.query.startswith("mediapad m")
                and not re.match(r"^mediapad m[23]", self.query)
        )
                or (
                self.query.startswith("honor play ")
                and not re.match(r"^honor play [2345]", self.query)
        )
                or (
                self.query.startswith("mate ")
                and self.query.endswith(" rs")
                and not re.match(r"^mate [34]0 rs$", self.query)
        )
                or (
                self.query.startswith("honor x")
                and not re.match(r"^honor x9\D?", self.query)
                and not re.match(r"^honor x10\D?", self.query)
        )
        ):
            return False
        return True

    def compose(self, area="all", tag="precise"):
        self.match_query = None
        self.query_pro()
        res = self.in_original(area)
        if res is not None:
            return res, self.match_query, tag

        if not self.in_mapping(area):
            tag = "fuzzy"
        if self.badcase_filter() and self.regular(area):
            return self.query, self.match_query, "precise"
        return None, self.match_query, tag


class Meizu(BrandBasic):
    def __init__(self):
        BrandBasic.__init__(self)

    def query_pro(self):
        for item in ["pro", "plus"]:
            if item in self.query:
                self.query = self.query.replace(item, f" {item} ")
        self.query = self.query.replace(f"{self.brand} ", "")

    def compose(self, area="all", tag="precise"):
        self.match_query = None
        if not self.badcase_filter():
            return None, self.match_query, tag

        self.query_pro()
        res = self.in_original(area)
        if res is not None:
            return res, self.match_query, tag

        if not self.in_mapping(area):
            tag = "fuzzy"
        return self.query, self.match_query, tag


class Samsung(BrandBasic):
    def __init__(self):
        BrandBasic.__init__(self)

    def query_pro(self):
        self.query = self.query.replace(f"{self.brand} ", "")

    def regular(self, area="all"):
        if (
                self.query.startswith("w")
                or self.query.startswith("m")
                or self.query.startswith("galaxy m")
                or self.query.startswith("galaxy j")
                or self.query.startswith("galaxy on")
                or (
                self.query.startswith("nexus")
                and not re.match(r"^nexus [9].*", self.query)
                and not re.match(r"^nexus 10.*", self.query)
        )
        ):
            return False
        return True

    def compose(self, area="all", tag="precise"):
        self.match_query = None
        self.query_pro()
        res = self.in_original(area)
        if res is not None:
            return res, self.match_query, tag

        if not self.in_mapping(area):
            tag = "fuzzy"
        if self.badcase_filter() and self.regular(area):
            return self.query, self.match_query, "precise"
        return self.query, self.match_query, tag


class Oppo(BrandBasic):
    def __init__(self):
        BrandBasic.__init__(self)

    def query_pro(self):
        self.query = (
            self.query.replace("oppo ", "")
                .replace("7201280320", "")
                .replace("opp0", "")
                .replace("r9sk", "r9s")
                .replace("r9m", "r9 plus")
                .replace("r9tm", "r9 plus")
                .replace("r11st", "r11s")
                .replace("plusm a", "")
        )

    def regular(self, area="all"):
        if (
                self.query.startswith("n")
                or self.query.startswith("u")
                or re.match(r"^[0-9]+$", self.query)
                or (
                self.query.startswith("a")
                and "ace" not in self.query
                and not re.match(r"^a[1-9][a-z]?.*", self.query)
                and not re.match(r"^a5[12346789][a-z]?$", self.query)
                and not re.match(r"^a7[123678][a-z]?$", self.query)
                and not re.match(r"^a9[123][a-z]?$", self.query)
                and not re.match(r"^a3[01236789][a-z]{1,2}?$", self.query)
        )
                or (
                self.query.startswith("r")
                and "reno" not in self.query
                and not re.match(r"^r1[01245678][a-z]?.*", self.query)
                and not re.match(r"^r[5-9][a-z]?.*", self.query)
        )
        ):
            return False
        return True

    def compose(self, area="all", tag="precise"):
        self.match_query = None
        self.query_pro()
        if not self.badcase_filter():
            return None, self.match_query, tag

        res = self.in_original(area)
        if res is not None:
            return res, self.match_query, tag

        if not self.in_mapping(area):
            tag = "fuzzy"
        if not self.regular(area):
            return None, self.match_query, "precise"
        return self.query, self.match_query, tag


class Vivo(BrandBasic):
    def __init__(self):
        BrandBasic.__init__(self)

    def query_pro(self, *args, **kwargs):
        for item in ["xplay", "plus"]:
            if item in self.query:
                self.query = self.query.replace(item, f" {item} ")
        self.query = self.query.replace(f"{self.brand} ", "").replace("bbk ", "")
        if re.match(r"^v[1-9]{4}.[0-9]{2}$", self.query):
            self.query = self.query[:5]

    def regular(self, area="all"):
        if (
                (self.query.startswith("u") and not re.match(r"^u2[01]", self.query))
                or self.query.startswith("g")
                or self.query.startswith("iqoo u")
                or (
                self.query.startswith("s")
                and not re.match(r"^s[12567][a-z]?", self.query)
        )
                or (
                self.query.startswith("y")
                and not re.match(r"^y[34567][a-z]?", self.query)
                and not re.match(r"^y2[012389][a-z]?", self.query)
                and not re.match(r"^y3[01245][a-z]?", self.query)
                and not re.match(r"^y5[0-6][a-z]?", self.query)
                and not re.match(r"^y6[5-9][a-z]?", self.query)
                and not re.match(r"^y7[01234589][a-z]?", self.query)
                and not re.match(r"^y8[0123459][a-z]?$", self.query)
                and not re.match(r"^y9[0-7][a-z]?", self.query)
        )
                or (
                self.query.startswith("x")
                and not re.match(r"^x[456789][a-z]?", self.query)
                and not re.match(r"^x2[0123679]", self.query)
                and not re.match(r"^x3[012][a-z]?", self.query)
                and not re.match(r"^x5[012389][a-z]?", self.query)
                and not re.match(r"^x6[012][a-z]?", self.query)
        )
                or (
                self.query.startswith("iqoo neo ")
                and not re.match(r"^iqoo neo [12345]", self.query)
        )
                or (
                self.query.startswith("z")
                and not re.match(r"^z[1-6][a-z]?", self.query)
        )
                or (
                self.query.startswith("v")
                and not re.match(r"^v[2349][a-z]?", self.query)
                and not re.match(r"^v2[01]", self.query)
                and not re.match(r"^v1[01456789]", self.query)
                and not re.match(r"^v[456789]\D", self.query)
        )
        ):
            return False
        return True

    def compose(self, area="all", tag="precise"):
        self.match_query = None
        if not self.badcase_filter():
            return None, self.match_query, tag

        self.query_pro()
        res = self.in_original(area)
        if res is not None:
            return res, self.match_query, tag

        if not self.in_mapping(area):
            tag = "fuzzy"
        if not self.regular(area):
            return None, self.match_query, "precise"
        return self.query, self.match_query, tag


class Google(BrandBasic):
    def __init__(self):
        BrandBasic.__init__(self)

    def query_pro(self):
        self.query = self.query.replace(f"{self.brand} ", "")

    def compose(self, area="all", tag="precise"):
        self.match_query = None
        if not self.badcase_filter():
            return None, self.match_query, tag

        self.query_pro()
        res = self.in_original(area)
        if res is not None:
            return res, self.match_query, tag

        if not self.in_mapping(area):
            tag = "fuzzy"
        if not self.regular(area):
            return None, self.match_query, "precise"
        return self.query, self.match_query, tag


class Oneplus(BrandBasic):
    def __init__(self):
        BrandBasic.__init__(self)

    def query_pro(self):
        self.query = self.query.replace(f"{self.brand} ", "")

    def compose(self, area="all", tag="precise"):
        self.match_query = None
        if not self.badcase_filter():
            return None, self.match_query, tag

        self.query_pro()
        res = self.in_original(area)
        if res is not None:
            return res, self.match_query, tag

        if not self.in_mapping(area):
            tag = "fuzzy"
        return self.query, self.match_query, tag


class Asus(BrandBasic):
    def __init__(self):
        BrandBasic.__init__(self)

    def compose(self, area="all", tag="precise"):
        self.match_query = None
        if not self.badcase_filter():
            return None, self.match_query, tag

        res = self.in_original(area)
        if res is not None:
            return res, self.match_query, tag

        if not self.in_mapping(area):
            tag = "fuzzy"
        return self.query, self.match_query, tag


class Realme(BrandBasic):
    def __init__(self):
        BrandBasic.__init__(self)

    def query_pro(self):
        self.query = self.query.replace(f"{self.brand} ", "")

    def compose(self, area="all", tag="precise"):
        self.match_query = None
        if not self.badcase_filter():
            return None, self.match_query, tag

        self.query_pro()
        res = self.in_original(area)
        if res is not None:
            return res, self.match_query, tag

        if not self.in_mapping(area):
            tag = "fuzzy"
        return self.query, self.match_query, tag


class Motorola(BrandBasic):
    def __init__(self):
        BrandBasic.__init__(self)

    def query_pro(self):
        self.query = self.query.replace(f"{self.brand} ", "")

    def compose(self, area="all", tag="precise"):
        self.match_query = None
        if not self.badcase_filter():
            return None, self.match_query, tag

        self.query_pro()
        res = self.in_original(area)
        if res is not None:
            return res, self.match_query, tag

        if not self.in_mapping(area):
            tag = "fuzzy"
        return self.query, self.match_query, tag


class Match(object):
    def __init__(self):
        self.phone_bench_key = "安卓版 PCMark 工作 3.0"
        self.geek_bench = "multi_core_score"
        with open(f"{self.mobile_path}/brand_ratio.json", encoding="utf-8") as f:
            self.brand_ratio = json.load(f)
        with open(f"{self.mobile_path}/brand_ratio_phone.json", encoding="utf-8") as f:
            self.brand_ratio_phonebench = json.load(f)
        self.mean = 0
        for key in self.brand_ratio_phonebench.keys():
            self.mean += self.brand_ratio_phonebench[key]
        self.mean /= len(self.brand_ratio_phonebench)

    def score_align(self, details, _brand=None):
        if details.get("average_cpu_mark"):
            if "coefficient_flag" not in details.keys():
                if _brand is not None:
                    cpu_mark = self.brand_ratio.get("apple") * details[
                        "average_cpu_mark"] / self.brand_ratio.get(
                        _brand)
                else:
                    cpu_mark = self.brand_ratio.get("apple") * details[
                        "average_cpu_mark"] / self.brand_ratio.get(
                        "null")
                details["score"] = int(cpu_mark + 0.5)
                details["average_cpu_mark"] = details["score"]
                details["coefficient_flag"] = 1
        elif "performance" in details.keys():
            if (
                    self.phone_bench_key in details.get("performance")
                    and "coefficient_flag" not in details.keys()
            ):
                pc_score = int(details.get("performance").get(self.phone_bench_key).get("分数"))
                if _brand is not None:
                    pc_mark = pc_score * self.brand_ratio_phonebench[_brand]
                else:
                    pc_mark = pc_score * self.mean
                details["score"] = int(pc_mark + 0.5)
                details["performance"][self.phone_bench_key]["分数"] = details["score"]
                details["coefficient_flag"] = 1
        elif self.geek_bench in details.keys():
            if "coefficient_flag" not in details.keys():
                geek_score = details.get(self.geek_bench) * self.brand_ratio.get("apple")
                details["score"] = int(geek_score + 0.5)
                details[self.geek_bench] = details["score"]
                details["coefficient_flag"] = 1
        else:
            details["score"] = None
        return details

    def phone_match(
            self, query, dataset, phone_dict, brand,
            match_query=None, score=0.9, tag=None
    ):
        best_score, details = 0.00, dict()
        for _data in dataset:
            _match_query, _query = _data.split("\t")
            _details = phone_dict[_match_query]
            if brand == "apple":
                _match_query_l, _query_l = _match_query.split(" "), _query.strip().split(" ")
                _best_score = len(list(set(_match_query_l) & set(_query_l))) / max(len(_match_query_l), len(_query_l))
            else:
                _best_score = difflib.SequenceMatcher(None, _match_query, _query).quick_ratio()
            if _best_score > best_score:
                best_score, details = _best_score, _details
        if best_score > score:
            details = self.score_align(details)
            return Basic._return(details, query, brand, match_query, "fuzzy")
        return Basic._return({}, query, brand, match_query, tag)


class PhoneModel(Basic, Match):
    def __init__(self):
        Basic.__init__(self)
        Match.__init__(self)
        self.query_compose = {
            "xiaomi": Xiaomi(),
            "huawei": Huawei(),
            "honor": Huawei(),
            "meizu": Meizu(),
            "samsung": Samsung(),
            "oppo": Oppo(),
            "vivo": Vivo(),
            "google": Google(),
            "oneplus": Oneplus(),
            "asus": Asus(),
            "realme": Realme(),
            "motorola": Motorola(),
        }


class MobileDataset(PhoneModel):
    def __init__(self):
        PhoneModel.__init__(self)
        self.badcase_all = [
            "CO., LTD.", "Co., Ltd.", "INC.", "Intel",
            "Sony Corporation", "AMD", "Gigabyte Technolog", "Default string"]
        self.merge_mapping = list()
        for index in range(len(mobile_area)):
            self.merge_mapping.append(self.merge_dicts(
                [_map for _, _map in self.mapping[index].items()]))
        with open(f"{self.mobile_path}/manual_correct.json") as f:
            self.manual_j = json.load(f)

    def pre_infer(self, query):
        _query, match_query = query.lower(), None
        for item in self.badcase_all:
            if item.lower() in _query:
                return self._return({}, query)

        brand_ios, brand_android = 0, 0
        dataset, _brand, tag = list(), "all", "precise"
        if "iphone" in _query or "ipad" in _query:
            _query = _query.replace("iphone iphone", "iphone ").replace("  ", " ")
            _brand, _query = "apple", self.find_unchinese(_query)
            for brand in ["iphone", "ipad"]:
                if brand not in _query:
                    continue
                brand_ios += 1
                if _query in self.mapping[0][_brand]:
                    match_query = _query = self.mapping[0][_brand][_query]

            if brand_ios > 1:
                return self._return({}, query, "apple", match_query)

            _query = _query.lower()
            if match_query is not None and _query not in self.apple:
                for k in self.apple:
                    dataset.append(k + "\t" + _query + "\n")
                return self.phone_match(query, dataset, self.apple, "apple", match_query, 0.5, tag)
            else:
                _query = f"apple {_query}" if "apple" not in _query else _query
                if _query in self.apple:
                    phone = self.apple[_query]
                    if phone.get("average_cpu_mark"):
                        phone["score"] = phone.get("average_cpu_mark")
                    else:
                        phone["score"] = None
                    return self._return(phone, query, "apple", match_query)
        else:
            _query = self.word_pre(query)
            for brand in brands:
                if brand in _query:
                    _brand = brand
                    brand_android += 1
                if brand_android > 1:
                    return self._return({}, query, _brand, match_query)

            if _brand in self.query_compose.keys():
                self.query_compose[_brand].set(_query, _brand)
                _query, match_query, tag = self.query_compose[_brand].compose()
                if isinstance(_query, dict):
                    _query["query"] = query
                    if len(_query.get("details")) == 0:
                        return _query
                    _query["details"] = self.score_align(_query["details"], _brand)
                    return _query
                if match_query is not None:
                    self.query_compose[_brand].set(match_query, _brand)
                    _query, _match_query, tag = self.query_compose[_brand].compose()
                    match_query = match_query if _match_query is None else _match_query
                    if isinstance(_query, dict):
                        _query["query"] = query
                        if len(_query.get("details")) == 0:
                            return _query
                        _query["details"] = self.score_align(_query["details"], _brand)
                        return _query
                if _query is None:
                    return self._return({}, query, _brand, match_query, tag)

        if _query in brands:
            return self._return({}, query, _brand, match_query, tag)

        for k in self.android:
            dataset.append(k + "\t" + query + "\n")
        for q in self.phonebench:
            dataset.append(q + "\t" + query + "\n")
        for t in self.geekbench:
            dataset.append(t + "\t" + query + "\n")
        self.android.update(self.phonebench)
        self.android.update(self.geekbench)
        return self.phone_match(query, dataset, self.android, _brand, match_query, tag=tag)

    def infer(self, query):
        query = query["device"] if not isinstance(query, str) else query

        if query in self.manual_j:
            return self.manual_j[query]
        req = self.pre_infer(query)
        if req.get("name") is None:
            if req.get("match_query") is not None:
                req["name"] = req.get("match_query")

            _q = self.word_pre(query)
            if _q in self.merge_mapping[0]:
                req = self.pre_infer(self.merge_mapping[0][_q])
                req["name"] = req.get("query")
                req["query"] = query
        return req
    
    def fuzzy_search(self, query, topK = 3):
        req_d = dict()
        query = query["device"] if not isinstance(query, str) else query
        for _data, _item in {**self.original_apple, **self.original_android}.items():
            if query.lower() in _data.lower():
                _score = len(query) / len(_data)
                req_d[_score] = _item
        if len(req_d) > 0:
            return [req_d[i] for i in sorted(req_d, reverse=True)]
    
        req = list()
        query = query["device"] if not isinstance(query, str) else query
        search = self.model.encode([query])
        _, I = self.index.search(search, topK)
        output = [self.em_input[i] for i in I[0]]
        for _data in output:
            if _data in self.original_apple:
                req.append(self.original_apple[_data])
            if _data in self.original_android:
                req.append(self.original_android[_data])
        return req

import os
import re
import json
import difflib
from itertools import groupby
from operator import itemgetter

import faiss
from bert_serving.client import BertClient

from tfe.settings import app_path


class Basic(object):
    def __init__(self):
        self.origin_path = f"{app_path}/json"
        self.hardware_name_map = {
            "cpu": "cpu_name",
            "gpu": "videocard_name"
        }
        self.original_cpus, self.original_gpus = dict(), dict()
        self.cpus, self.gpus = dict(), dict()
        self._cpu()
        self._gpus()

        self.model = BertClient()
        self.cpu_index, self.cpu_em = self.load_embedding("cpu")
        self.gpu_index, self.gpu_em = self.load_embedding("gpu")

    def _cpu(self, min_score=1000):
        _files = sorted(os.listdir(self.origin_path))
        for _item in _files:
            if "cpu" not in _item or "index" in _item:
                continue

            with open(f"{self.origin_path}/{_item}") as f:
                original_cpus = json.load(f)

        for item in original_cpus:
            name = item.get(self.hardware_name_map["cpu"])
            item["name"], item["score"] = name, item.get("mark")
            if item["score"] > min_score:
                self.original_cpus[name] = item

            if "Alias" in item.get("detail") and item["score"] > min_score:
                other_name = item["detail"].get("Alias")
                if (
                    re.match(r".*AMD.+R.+ R.+, .+C.+ C.+", other_name)
                    is not None
                ):
                    st, ed = re.match(r".*AMD.+R.+, .+C.+ C.+", other_name).span()
                    other_name = (
                        other_name[:st]
                        + other_name[st:ed].replace(",", ".")
                        + other_name[ed:]
                    )
                name = [name] + other_name.split(", ")
            for _name in name:
                _name = _name.replace("E5-2450 0 @", "E5-2450 @").replace("_", " ")
                _name = self.word_pre(_name, "cpu", 10)
                self.cpus[_name] = item

    def _gpus(self, min_score=1000):
        _files = sorted(os.listdir(self.origin_path))
        for _item in _files:
            if "gpu" not in _item or "index" in _item:
                continue

            with open(f"{self.origin_path}/{_item}", encoding="utf-8") as f:
                original_gpus = json.load(f)

        for item in original_gpus:
            name = item.get(self.hardware_name_map["gpu"])
            for _name in [name] + item.get("alias"):
                _name = _name.replace("%2f", "/").replace("(", "/").replace(")", "/")
                _name = self.word_pre(_name, "gpu", 10)
                item["name"] = _name
                if "score_vcbm_site" in item and item["score_vcbm_site"] > min_score:
                    item["score"] = item.get("score_vcbm_site")
                else:
                    item["score"] = item.get("score_bybusa_site")
                self.gpus[_name] = item
            if item["score"] > min_score:
                self.original_gpus[name] = item

    def word_pre(self, word, _type=None, nums=5):
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
            .replace("00ghz", "ghz")
            .replace("cpu", "")
        )
        word = re.sub(r"\(.*?\)", "", word)
        word = " ".join(map(itemgetter(0), groupby(word.split())))
        word = re.sub("[^0-9a-zA-Z,]+", " ", word)
        word = " ".join(word.split()).strip()

        _word = word.split(" ")
        if _word[-1].startswith("0x"):
            _word = _word[:-1]
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

    def load_embedding(self, flag):
        em_input = list(self.cpus) if flag == "cpu" else list(self.gpus)
        if os.path.exists(f"{self.origin_path}/{flag}.index"):
            index = faiss.read_index(f"{self.origin_path}/{flag}.index")
        else:
            embeddings = self.model.encode(em_input)
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings)
            faiss.write_index(index, f"{self.origin_path}/{flag}.index")
        return index, em_input


class Match(object):

    @staticmethod
    def cpu_gpu_match(dataset, _query, tag="precise"):
        best_score, match_query = 0.00, ""
        for _data in dataset:
            _best_score = difflib.SequenceMatcher(None, _data, _query).quick_ratio()
            if _best_score > best_score:
                best_score, match_query = _best_score, _data
        if best_score > 0.9:
            return match_query, tag
        return None, tag


class ClientModel(Basic, Match):
    def __init__(self):
        Basic.__init__(self)
        Match.__init__(self)


class ClientDataset(ClientModel):
    def __init__(self):
        ClientModel.__init__(self)
        self.mode = None
        self.gpu_badcase = [
            "AMD Radeon(TM) Graphics",
            "Microsoft Basic Render Driver",
            "$DISP_DESC$",
            "NVIDIA TITAN RTX T4",
            "GTX 3060",
            "GTX 3070",
            "GTX 2060",
            "GTX 2070",
            "software adapter"
        ]
        self.cpu_badcase = [
            "0000",
            "Not Available",
            "Intel Core Processor",
            "Westmere",
            "Intel Xeon Processor",
            "Genuine Intel(R) CPU @",
            "I7 9600K",
            "Genuine Intel(R) CPU 0 @",
            "AMD EPYC Processor (with IBPB)",
            "AMD Phenom(tm) II X4 10 Processor",
            "Intel 0000",
            "Unknown"
        ]
        self.cpu_match = list(self.cpus.keys())
        self.gpu_match = list(self.gpus.keys())

    def _pre(self, query, _type):
        if _type == "cpu":
            query = query.split(", ~")[0]
            return self.word_pre(query.strip().replace("_", " ").lower(), "cpu", 10)
        return query.strip().replace("_", " ").lower().strip().replace("(", " ").replace(")", " ").replace("  ", " ")

    def _dataset(self, _query, query):
        _query = self.find_unchinese(self.word_pre(_query, self.mode, 10)).replace(",", "")
        for _q in [_query, self.word_pre(query)]:
            if _q in self.hardware:
                return self._return(self.hardware[_q], query), _q
        return [], _query

    def infer(self, query, mode):
        assert mode in ["cpu", "gpu"]
        self.mode = mode
        query = query["device"] if not isinstance(query, str) else query

        self.hardware, self.badcase, self.match = self.gpus, self.gpu_badcase, self.gpu_match
        if self.mode == "cpu":
            self.hardware, self.badcase, self.match = self.cpus, self.cpu_badcase, self.cpu_match

        _query = self._pre(query, self.mode)
        for badcase in self.badcase:
            if self._pre(badcase, self.mode) in _query:
                return self._return({}, query)

        dataset, _query = self._dataset(_query, query)
        if isinstance(dataset, dict):
            return dataset

        match_query, tag = self.cpu_gpu_match(self.match, _query)
        if match_query is None:
            return self._return({}, query, tag=tag)

        return self._return(self.hardware[match_query], query)

    def fuzzy_search(self, query, mode, topK = 3):
        req_d = dict()
        query = query["device"] if not isinstance(query, str) else query
        hardware = self.original_cpus if mode == "cpu" else self.original_gpus
        for _data, _item in hardware.items():
            if query.lower() in _data.lower():
                _score = len(query) / len(_data)
                req_d[_score] = _item
        if len(req_d) > 0:
            return [req_d[i] for i in sorted(req_d, reverse=True)]

        req = list()
        query = query["device"] if not isinstance(query, str) else query
        hardware = self.original_cpus if mode == "cpu" else self.original_gpus
        search = self.model.encode([query])

        if mode == "cpu":
            _, I = self.cpu_index.search(search, topK)
            output = [self.cpu_em[i] for i in I[0]]
        else:
            _, I = self.gpu_index.search(search, topK)
            output = [self.gpu_em[i] for i in I[0]]

        for _data in output:
            if _data in hardware:
                req.append(hardware[_data])
        return req

    def _return(self, item, query, match_query=None, tag="precise"):
        item = item if isinstance(item, list) else item
        if match_query is None and item is not None:
            match_query = item.get(self.hardware_name_map[self.mode])

        return {
            "tag": tag,
            "query": query,
            "details": item,
            "score": item.get("score"),
            "match_query": match_query
        }

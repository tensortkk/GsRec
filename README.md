## GsRec Search Backend
### INTRODUCTION
The backend of GsRec performs fuzzy CPU, GPU, and mobile searches. Considering the security issues of relevant commercial data, the device data in this project is mainly for the effect display.

### Quick Start
**Bert Embedding Server**
```bash
wget https://storage.googleapis.com/bert_models/2018_10_18/cased_L-12_H-768_A-12.zip
unzip cased_L-12_H-768_A-12.zip
bert-serving-start -model_dir ./cased_L-12_H-768_A-12 -num_worker=1
```

**Backend Server**
```bash
gunicorn -b 0.0.0.0:5001 --name tfe tfe.wsgi:app
```

### HTTP API
- mobile: GET /api/match/mobile?q=
- CPU: GET /api/match/cpu?q=
- GPU: GET /api/match/gpu?q=

### Demo of Device Dataset
**CPU**
```json
{
    "cpu_name": "Intel Core i9-13900K",
    "mark": 58695,
    "detail": {
        "Release": "Q3 2022",
        "Cache Size": "L1: 2176 KB, L2: 32.0 MB, L3: 36 MB",
        "Platform": "Desktop",
        "Efficient Cores": "16 Cores, 16 Threads, 2.2 GHz Base, 4.3 GHz Turbo",
        "Alias": "13th Gen Intel(R) Core(TM) i9-13900K, 13th Gen Intel Core i9-13900K",
        "Performance Cores": "8 Cores, 16 Threads, 3.0 GHz Base, 5.8 GHz Turbo",
        "TDP Up": "253 W",
        "Total Cores": "24 Cores, 32 Threads",
        "Typical TDP": "125 W"
    }
}
```

**GPU**
```json
{
    "videocard_name": "NVIDIA GeForce GTX 1080 Ti",
    "core_clock": "1481 MHz",
    "max_memory": "11264 MB",
    "memory_clock": "1376 MHz11008 MHz effective",
    "alias": [
        "GeForce GTX 1080 Ti",
        "NVIDIA GeForce (R) GTX 1080 Ti",
        "NVIDIA GeForce® GTX 1080 Ti",
        "GeForce (R) GTX 1080 Ti",
        "GeForce® GTX 1080 Ti",
        "GTX 1080 Ti",
        "GTX-1080-Ti",
        "NVIDIA GTX 1080 Ti",
        "NVIDIA-GTX-1080-Ti"
    ],
    "display_memory_size": 11264,
    "score_bybusa_site": 17385,
    "score_gpucheck_site": "65/100",
    "score_vcbm_site": 18392,
    "dx": "12",
    "support_dx": [
        "12","11","10", "9"
    ],
    "platform": "Desktop Graphics",
    "release_year": "2017"
}
```

**Mobile**
```json
{
    "name": "Apple iPad Pro 11.0 3rd Gen",
    "score": 45086,
    "total_ram": "15673.2 MB",
    "average_cpu_mark": 15142,
    "mem_mark": 59434,
    "dist_mark": 43507,
    "2d_mark": 51995,
    "3d_mark": 22556
}
```

### Develop
**Pip Whl**
```bash
bash pack.sh
```

**Docker Image (Recommend)**
```bash
bash build.sh
```

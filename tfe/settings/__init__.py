import os
from .helpers import parse_boolean, fix_assets_path


app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROXIES_COUNT = int(os.environ.get("TFE_PROXIES_COUNT", "1"))
MULTI_ORG = parse_boolean(os.environ.get("TFE_MULTI_ORG", "false"))

mobile_area = ["all", "cn", "en"]
hardware_info = {
    "cpu": """
    Intel: i3/i5/i7/i9 series and Intel Core 2 generation; 
    AMD: all series including Athlon X2 since 2009.""",
    "gpu": """
    NVIDIA: TITAN and GeForce GTX/RTX series;
    AMD: R/RX series since 2012 including HD 7950.""",
    "mobile": """
    Apple mainly covers iPhone 6, iPad 4 and newer;
    Huawei covers Mate 8, P8 and newer;
    Samsung covers Galaxy S3, Galaxy note2 and newer;
    Xiaomi covers mi 3, redmi note 2 and newer."""
}


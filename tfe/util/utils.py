import datetime


def dt_str(days_ago=30):
    now = datetime.datetime.now()
    ago = now - datetime.timedelta(days=days_ago)
    return ago.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")


def takeScore(item):
    return 0 if item.get("score") is None else int(item.get("score"))


def hardware_retain(hardware_l):
    return max(hardware_l, key=len, default="")

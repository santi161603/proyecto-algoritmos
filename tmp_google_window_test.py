import re
import requests

for w in [None, "1D", "5D", "1M", "6M", "YTD", "1Y", "5Y", "MAX"]:
    if w is None:
        url = "https://www.google.com/finance/quote/SPY:NYSE"
    else:
        url = f"https://www.google.com/finance/quote/SPY:NYSE?window={w}"
    text = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
    m = re.search(r"AF_initDataCallback\(\{key: 'ds:6'.*?\}\);</script>", text, re.DOTALL)
    if not m:
        print(w, "no ds:6")
        continue
    b = m.group(0)
    ts_count = len(re.findall(r"\b1[5-9]\d{8}\b", b))
    print(w, "len", len(b), "ts", ts_count)

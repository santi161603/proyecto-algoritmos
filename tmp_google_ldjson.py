import json
import re
import requests

text = requests.get(
    "https://www.google.com/finance/quote/SPY:NYSE",
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0"},
).text

matches = list(re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.DOTALL))
print("matches", len(matches))
for m in matches:
    s = m.group(1)
    print("len", len(s))
    try:
        obj = json.loads(s)
        print("type", type(obj))
        if isinstance(obj, dict):
            print("keys", list(obj.keys())[:20])
            print(obj)
    except Exception as e:
        print("json err", e)

import re
import requests

url = "https://www.google.com/finance/quote/SPY:NYSE"
text = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text

keys = re.findall(r"AF_initDataCallback\(\{key: '([^']+)'", text)
print("nkeys", len(keys))
print(keys[:40])

for k in keys[:10]:
    i = text.find(f"key: '{k}'")
    print("---", k, i)
    print(text[i:i+300])

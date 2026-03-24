import re
import requests

url = "https://www.google.com/finance/quote/SPY:NYSE"
text = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text

pattern = re.compile(r"AF_initDataCallback\((\{.*?\})\);</script>", re.DOTALL)
blocks = pattern.findall(text)
print("blocks:", len(blocks))

for i, b in enumerate(blocks):
    key_m = re.search(r"key:\s*'([^']+)'", b)
    key = key_m.group(1) if key_m else f"idx-{i}"
    print("\n===", key, "===")
    print("len", len(b))
    print("has timestamp-like", bool(re.search(r"\b1[5-9]\d{8}\b", b)))
    print("has ohlc-ish", bool(re.search(r"open|high|low|close", b, re.IGNORECASE)))
    print("head", b[:220].replace("\n", " "))

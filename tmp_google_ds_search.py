import re
import requests

text = requests.get("https://www.google.com/finance/quote/SPY:NYSE", timeout=30, headers={"User-Agent": "Mozilla/5.0"}).text
blocks = re.findall(r"AF_initDataCallback\((\{.*?\})\);</script>", text, re.DOTALL)

for b in blocks:
    key_m = re.search(r"key:\s*'([^']+)'", b)
    key = key_m.group(1) if key_m else "?"
    if "SPY" in b or "NYSEARCA" in b or "State Street" in b:
        print("\n===", key, "len", len(b), "===")
        print("contains SPY", "SPY" in b)
        print("contains NYSEARCA", "NYSEARCA" in b)
        print("contains timestamp patterns", len(re.findall(r"\b1[5-9]\d{8}\b", b)))
        print(b[:1200])

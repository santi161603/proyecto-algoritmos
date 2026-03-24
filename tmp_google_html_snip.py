import requests

text = requests.get(
    "https://www.google.com/finance/quote/SPY:NYSE",
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0"},
).text

for token in [">Open<", ">High<", ">Low<", ">Prev close<", ">Mkt cap<", "data-last-price", "YMlKec fxKbKc"]:
    idx = text.find(token)
    print(token, idx)
    if idx != -1:
        s = max(0, idx - 250)
        e = min(len(text), idx + 350)
        print(text[s:e])
        print("---")

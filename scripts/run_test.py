import json

def print_data(tckr: str):
    with open(f"scripts/big_cache/{tckr}.json") as f:
        data = json.load(f)

    usgaap = data["facts"]["us-gaap"]
    print(len(usgaap))

    account = usgaap["CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]
    print(account["label"])

    records = account["units"]["USD"]
    print(len(records))
    most_recent = records[-1]
    val = records[-1]["val"]
    print(records[-1])

    print(val)

print_data("GOOG")
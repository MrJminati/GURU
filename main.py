import requests
import time
import os
import json

# ===== CONFIG =====
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MIN_ETH = 50
SMART_WALLETS_FILE = "smart_wallets.json"

# ===== EXCHANGE WALLETS =====
EXCHANGE_WALLETS = {
    "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance
    "0x503828976d22510aad0201ac7ec88293211d23da"   # Coinbase
}

EXCHANGE_NAMES = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance",
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase"
}

# ===== MEMORY =====
wallet_scores = {}
seen_signals = set()

# ===== TELEGRAM =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)

# ===== ETH PRICE =====
def get_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        res = requests.get(url).json()
        return res["ethereum"]["usd"]
    except:
        return 3000

# ===== BLOCK DATA (ETHERSCAN V2) =====
def get_latest_block():
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": 1,
        "module": "proxy",
        "action": "eth_blockNumber",
        "apikey": ETHERSCAN_API_KEY
    }

    res = requests.get(url, params=params).json()

    if "result" not in res:
        print("API Error:", res)
        return 0

    return int(res["result"], 16)


def get_block_transactions(block_number):
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": 1,
        "module": "proxy",
        "action": "eth_getBlockByNumber",
        "tag": hex(block_number),
        "boolean": "true",
        "apikey": ETHERSCAN_API_KEY
    }

    res = requests.get(url, params=params).json()

    if "result" not in res:
        print("API Error:", res)
        return []

    return res["result"]["transactions"]

# ===== TOKEN TRANSFERS =====
def get_token_transfers(wallet):
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": 1,
        "module": "account",
        "action": "tokentx",
        "address": wallet,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }
    res = requests.get(url, params=params).json()
    return res.get("result", [])[:10]

# ===== SCORE SYSTEM =====
def update_score(wallet, value_eth):
    if wallet not in wallet_scores:
        wallet_scores[wallet] = 0
    wallet_scores[wallet] += value_eth

def save_smart_wallets():
    smart_wallets = [
        w for w, score in wallet_scores.items()
        if score > 200
    ]
    with open(SMART_WALLETS_FILE, "w") as f:
        json.dump(smart_wallets, f)

def load_smart_wallets():
    try:
        with open(SMART_WALLETS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

# ===== SIGNAL FILTER =====
def is_new_signal(key):
    if key in seen_signals:
        return False
    seen_signals.add(key)
    return True

# ===== ENTRY SIGNAL =====
def detect_entry(wallet):
    txs = get_token_transfers(wallet)

    for tx in txs:
        try:
            value = int(tx["value"]) / (10 ** int(tx["tokenDecimal"]))
            token = tx["tokenSymbol"]

            if value > 100000:
                key = wallet + token + "BUY"

                if is_new_signal(key):
                    msg = f"""
🟢 *ENTRY SIGNAL*

Wallet: `{wallet}`
Token: *{token}*
Amount: {value:.2f}

Smart money accumulating 🚀
"""
                    send_telegram(msg)
        except:
            continue

# ===== EXIT SIGNAL =====
def detect_exit(wallet):
    txs = get_token_transfers(wallet)

    for tx in txs:
        try:
            to_addr = tx["to"].lower()
            token = tx["tokenSymbol"]

            if to_addr in EXCHANGE_WALLETS:
                key = wallet + token + "SELL"

                if is_new_signal(key):
                    exchange = EXCHANGE_NAMES.get(to_addr, "Exchange")

                    msg = f"""
🔴 *EXIT SIGNAL*

Wallet: `{wallet}`
Token: *{token}*

🏦 {exchange}
Possible dump incoming ⚠️
"""
                    send_telegram(msg)
        except:
            continue

# ===== TRACK SMART WALLETS =====
def track_smart_wallets():
    wallets = load_smart_wallets()

    for wallet in wallets:
        detect_entry(wallet)
        detect_exit(wallet)

# ===== MAIN LOOP =====
print("🚀 Bot Started...")

last_block = get_latest_block()

while True:
    try:
        current_block = get_latest_block()

        if current_block > last_block:
            print(f"New block: {current_block}")

            txs = get_block_transactions(current_block)

            for tx in txs:
                value_eth = int(tx["value"], 16) / 10**18

                if value_eth >= MIN_ETH:
                    from_addr = tx["from"].lower()
                    to_addr = tx["to"].lower() if tx["to"] else "unknown"
                    tx_hash = tx["hash"]

                    eth_price = get_eth_price()
                    usd_value = value_eth * eth_price

                    signal = "Neutral"
                    exchange = None

                    if to_addr in EXCHANGE_WALLETS:
                        signal = "🔴 SELL PRESSURE"
                        exchange = EXCHANGE_NAMES.get(to_addr)

                    elif from_addr in EXCHANGE_WALLETS:
                        signal = "🟢 BUY PRESSURE"
                        exchange = EXCHANGE_NAMES.get(from_addr)

                    tag = "🐋 Whale"
                    if usd_value > 500000:
                        tag = "🔥 Mega Whale"

                    key = tx_hash

                    if is_new_signal(key):
                        msg = f"""
{tag} *ALERT*

💰 ${usd_value:,.0f} ({value_eth:.2f} ETH)
📊 Signal: {signal}
"""

                        if exchange:
                            msg += f"\n🏦 Exchange: *{exchange}*\n"

                        msg += f"""
👤 [From](https://etherscan.io/address/{from_addr})
➡️ [To](https://etherscan.io/address/{to_addr})

🔗 [View Transaction](https://etherscan.io/tx/{tx_hash})
"""

                        send_telegram(msg)

                    update_score(from_addr, value_eth)
                    update_score(to_addr, value_eth)

            save_smart_wallets()
            last_block = current_block

        track_smart_wallets()

        time.sleep(20)

    except Exception as e:
        print("Error:", e)
        time.sleep(10)

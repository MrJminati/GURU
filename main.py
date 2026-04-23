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
WALLET_STATS_FILE = "wallet_stats.json"

# ===== EXCHANGE WALLETS =====
EXCHANGE_WALLETS = {
    "0x28c6c06298d514db089934071355e5743bf21d60",
    "0x503828976d22510aad0201ac7ec88293211d23da"
}

EXCHANGE_NAMES = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance",
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase"
}

# ===== MEMORY =====
wallet_scores = {}
wallet_stats = {}
wallet_trades = {}
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

# ===== TOKEN PRICE (DEXSCREENER) =====
def get_token_price(contract_address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{contract_address}"
        res = requests.get(url).json()

        pairs = res.get("pairs", [])
        if not pairs:
            return None

        return float(pairs[0]["priceUsd"])
    except:
        return None

# ===== STORAGE =====
def save_wallet_stats():
    with open(WALLET_STATS_FILE, "w") as f:
        json.dump(wallet_stats, f)

def load_wallet_stats():
    global wallet_stats
    try:
        with open(WALLET_STATS_FILE, "r") as f:
            wallet_stats = json.load(f)
    except:
        wallet_stats = {}

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

# ===== WIN RATE =====
def get_wallet_score(wallet):
    stats = wallet_stats.get(wallet, {"wins": 0, "losses": 0})
    total = stats["wins"] + stats["losses"]

    if total == 0:
        return 0

    return stats["wins"] / total

# ===== ETHERSCAN V2 =====
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

# ===== ENTRY SIGNAL =====
def detect_entry(wallet):
    txs = get_token_transfers(wallet)

    for tx in txs:
        try:
            value = int(tx["value"]) / (10 ** int(tx["tokenDecimal"]))
            token = tx["tokenSymbol"]
            contract = tx["contractAddress"]

            if value > 100000:
                price = get_token_price(contract)
                if price is None:
                    continue

                if wallet not in wallet_trades:
                    wallet_trades[wallet] = {}

                wallet_trades[wallet][contract] = {
                    "token": token,
                    "entry_price": price
                }

                key = wallet + contract + "BUY"

                if is_new_signal(key):
                    msg = f"""
🟢 *ENTRY SIGNAL*

Wallet: `{wallet}`
Token: *{token}*

💰 Price: ${price:.6f}

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
            contract = tx["contractAddress"]

            if to_addr in EXCHANGE_WALLETS:

                price = get_token_price(contract)
                if price is None:
                    continue

                if wallet in wallet_trades and contract in wallet_trades[wallet]:
                    entry_data = wallet_trades[wallet][contract]
                    entry_price = entry_data["entry_price"]
                    exit_price = price

                    roi = ((exit_price - entry_price) / entry_price) * 100

                    if wallet not in wallet_stats:
                        wallet_stats[wallet] = {"wins": 0, "losses": 0}

                    if roi > 0:
                        wallet_stats[wallet]["wins"] += 1
                    else:
                        wallet_stats[wallet]["losses"] += 1

                    exchange = EXCHANGE_NAMES.get(to_addr, "Exchange")

                    key = wallet + contract + "SELL"

                    if is_new_signal(key):
                        msg = f"""
🔴 *EXIT SIGNAL*

Wallet: `{wallet}`
Token: *{token}*

📊 ROI: {roi:.2f}%
🏦 {exchange}

Smart money exit ⚠️
"""
                        send_telegram(msg)

        except:
            continue

# ===== TRACK SMART WALLETS =====
def track_smart_wallets():
    wallets = load_smart_wallets()

    for wallet in wallets:
        score = get_wallet_score(wallet)

        if score >= 0.6:
            detect_entry(wallet)
            detect_exit(wallet)

# ===== MAIN =====
print("🚀 Bot Started...")

load_wallet_stats()

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
                    try:
                        requests.post("https://studious-acorn-45vr9p9wqvxhqr95-8000.app.github.dev/add_signal", json={
                            "wallet": from_address,
                            "amount": usd_value,
                            "type": signal_type,   # BUY / SELL / TRANSFER
                            "time": "just now"
                        })
                    except Exception as e:
                    print("API Error:", e)

                    wallet_scores[from_addr] = wallet_scores.get(from_addr, 0) + value_eth
                    wallet_scores[to_addr] = wallet_scores.get(to_addr, 0) + value_eth

            save_smart_wallets()
            save_wallet_stats()
            last_block = current_block

        track_smart_wallets()
        
         except Exception as e:
        print("API Error:", e)
        time.sleep(20)

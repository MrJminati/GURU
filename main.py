import requests
import time
import os
import json

# ===== CONFIG =====
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ===== API CONFIG =====
API_URL = os.getenv("API_URL") or "https://guru-production-1424.up.railway.app"

# ===== API SEND =====
def send_to_api(data):
    try:
        url = f"{API_URL}/add_signal"

        print("📡 Sending to API:", url)

        res = requests.post(
            url,
            json=data,
            timeout=5
        )

        print("✅ API Status:", res.status_code)

        if res.status_code != 200:
            print("❌ API Response:", res.text)

    except Exception as e:
        print("🚨 API Error:", e)

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
seen_signals = set()

# ===== TELEGRAM =====
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

# ===== ETH PRICE =====
def get_eth_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        res = requests.get(url, timeout=10).json()
        return res["ethereum"]["usd"]
    except:
        return 3000

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
    smart_wallets = [w for w, score in wallet_scores.items() if score > 200]
    with open(SMART_WALLETS_FILE, "w") as f:
        json.dump(smart_wallets, f)

# ===== SIGNAL FILTER =====
def is_new_signal(key):
    if key in seen_signals:
        return False
    seen_signals.add(key)
    return True

# ===== ETHERSCAN =====
def get_latest_block():
    try:
        url = "https://api.etherscan.io/v2/api"
        params = {
            "chainid": 1,
            "module": "proxy",
            "action": "eth_blockNumber",
            "apikey": ETHERSCAN_API_KEY
        }
        res = requests.get(url, params=params, timeout=10).json()
        return int(res.get("result", "0x0"), 16)
    except Exception as e:
        print("Block Error:", e)
        return 0

def get_block_transactions(block_number):
    try:
        url = "https://api.etherscan.io/v2/api"
        params = {
            "chainid": 1,
            "module": "proxy",
            "action": "eth_getBlockByNumber",
            "tag": hex(block_number),
            "boolean": "true",
            "apikey": ETHERSCAN_API_KEY
        }
        res = requests.get(url, params=params, timeout=10).json()
        return res.get("result", {}).get("transactions", [])
    except Exception as e:
        print("TX Error:", e)
        return []

# ===== API SEND =====
def send_to_api(data):
    if not API_URL:
        print("⚠️ API_URL not set")
        return

    try:
        res = requests.post(
            f"{API_URL}/add_signal",
            json=data,
            timeout=5
        )

        if res.status_code != 200:
            print("API Failed:", res.text)

    except Exception as e:
        print("API Error:", e)

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
                try:
                    value_eth = int(tx["value"], 16) / 10**18

                    if value_eth >= MIN_ETH:
                        from_addr = tx["from"].lower()
                        to_addr = tx["to"].lower() if tx["to"] else "unknown"
                        tx_hash = tx["hash"]

                        eth_price = get_eth_price()
                        usd_value = value_eth * eth_price

                        signal = "TRANSFER"

                        if to_addr in EXCHANGE_WALLETS:
                            signal = "SELL"
                        elif from_addr in EXCHANGE_WALLETS:
                            signal = "BUY"

                        tag = "🐋 Whale"
                        if usd_value > 500000:
                            tag = "🔥 Mega Whale"

                        if is_new_signal(tx_hash):
                            msg = f"""
{tag} *ALERT*

💰 ${usd_value:,.0f} ({value_eth:.2f} ETH)
📊 Signal: {signal}

👤 [From](https://etherscan.io/address/{from_addr})
➡️ [To](https://etherscan.io/address/{to_addr})

🔗 [View Transaction](https://etherscan.io/tx/{tx_hash})
"""

                            send_telegram(msg)

                            # 🔥 SEND TO WEBSITE
                            send_to_api({
                                "wallet": from_addr,
                                "amount": usd_value,
                                "type": signal,
                                "time": "just now"
                            })

                        wallet_scores[from_addr] = wallet_scores.get(from_addr, 0) + value_eth
                        wallet_scores[to_addr] = wallet_scores.get(to_addr, 0) + value_eth

                except Exception as e:
                    print("TX Process Error:", e)

            save_smart_wallets()
            save_wallet_stats()
            last_block = current_block

        time.sleep(20)

    except Exception as e:
        print("Main Loop Error:", e)
        time.sleep(10)

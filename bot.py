import requests
import time
import os

# ===== CONFIG =====
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Wallets to track (add more)
wallets = [
    "0x28C6c06298d514Db089934071355E5743bf21d60",  # Binance
    "0x71660c4005ba85c37ccec55d0c4493e6fe775d3a",  # Coinbase
    "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",  # Bitfinex whale
    "0x66f820a414680b5bcda5eeca5dea238543f42054",  # known active whale
]
MIN_ETH = 5  # minimum ETH for whale

# ===== SHARED DATA (FOR API) =====
shared_whales = []
seen_tx = set()

# ===== TELEGRAM FUNCTION =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg
    }
    try:
        requests.post(url, data=data)
    except:
        pass

# ===== GET TRANSACTIONS =====
def get_transactions(wallet):
    url = "https://api.etherscan.io/v2/api"

    params = {
        "chainid": 1,
        "module": "account",
        "action": "txlist",
        "address": wallet,
        "startblock": 0,
        "endblock": 99999999,
         "offset": 10,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }

    res = requests.get(url, params=params).json()

    if res.get("status") != "1":
        print("Etherscan error:", res)
        return []

    return res["result"][:5]

# ===== MAIN BOT FUNCTION =====
def start_bot():
    print("🚀 Bot Started...")

    while True:
        try:
            for wallet in wallets:
                print(f"Checking wallet: {wallet}")

                txs = get_transactions(wallet)

                for tx in txs:
                    tx_hash = tx["hash"]

                    if tx_hash in seen_tx:
                        continue

                    seen_tx.add(tx_hash)

                    value_eth = int(tx["value"]) / 10**18

                    if value_eth >= MIN_ETH:
                        from_addr = tx["from"]
                        to_addr = tx["to"]

                        # signal logic
                        if wallet.lower() == from_addr.lower():
                            signal = "🔴 SELL (Outflow)"
                        else:
                            signal = "🟢 BUY (Inflow)"
                            
                        # ===== STORE FOR API =====
                        whale_data = {
                            "type": "Whale",
                            "amount": round(value_eth, 2),
                            "from": from_addr,
                            "to": to_addr,
                            "signal": signal,
                            "tx": f"https://etherscan.io/tx/{tx_hash}"
                        }

                        shared_whales.append(whale_data)
                        shared_whales[:] = shared_whales[-50:]

                        # ===== TELEGRAM ALERT =====
                        message = f"""
🐋 Whale Transaction

{signal}
Amount: {value_eth:.2f} ETH

From: {from_addr}
To: {to_addr}

Tx: https://etherscan.io/tx/{tx_hash}
"""
                        send_telegram(message)
                        
                        supabase.table("signals").insert({
                                "wallet": from_addr,
                                "amount": usd_value,
                                "signal": signal
                            }).execute()

            time.sleep(60)

        except Exception as e:
            print("Error:", e)
            time.sleep(10)

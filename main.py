import requests
import time

# ===== CONFIG =====
ETHERSCAN_API_KEY = "QSVQMA9ZW6IR63DKICSUGIVS3JWTVNF97J"
TELEGRAM_BOT_TOKEN = "8550461382:AAG17tQfCcEcmFL4Yz2te70EhaWxwJwQzkU"
TELEGRAM_CHAT_ID = "-1003830537991"

EXCHANGES = {
    "binance": [
        "0x28C6c06298d514Db089934071355E5743bf21d60",
    ],
    "coinbase": [
        "0x71660c4005ba85c37ccec55d0c4493e66fe775d3",
    ]
}

# Wallets to track
wallets = [
    "0x6cd66DbdFe289ab83d7311B668ADA83A12447e21",  # Add whale wallet here
    "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8",
    "0xAFCD96e580138CFa2332C632E66308eACD45C5dA",
    "0xE92d1A43df510F82C66382592a047d288f85226f",
    "0x9f1799Fb47b1514f453BcEbbC37ecFe883756e83",
    "0xF977814e90dA44bFA03b6295A0616a897441aceC",
    "0x8103683202aa8DA10536036EDef04CDd865C225E",
    "0x2B6eD29A95753C3Ad948348e3e7b1A251080Ffb9",
    "0x091D1C972cb1648537a2Ba78eaBa371b1cE18336"
]

# Minimum value in USD (approx)
MIN_ETH = 1  # adjust (50 ETH ≈ big move)

global_score = 0   #global score to track overall market sentiment based on whale activity

while True:
    # ===== FUNCTIONS =====

    def send_telegram(msg):
        url = f"https://api.telegram.org/bot8550461382:AAG17tQfCcEcmFL4Yz2te70EhaWxwJwQzkU/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg
        }
        requests.post(url, data=data)

    def get_transactions(wallet):
        url = "https://api.etherscan.io/v2/api"

        params = {
            "chainid": 1,
            "module": "account",
            "action": "txlist",
            "address": wallet,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "desc",
            "apikey": ETHERSCAN_API_KEY
        }

        res = requests.get(url, params=params).json()

        if res["status"] != "1":
            print("Error:", res["message"], res["result"])
            return []

        return res["result"][:5]


    # ===== MAIN LOOP =====

    seen_tx = set()


    while True:
        for wallet in wallets:
            txs = get_transactions(wallet)
            print(f"Checking wallet: {wallet}")
            print(f"Transactions found: {len(txs)}")
            
            for tx in txs:
                tx_hash = tx["hash"]
                if tx_hash in seen_tx:
                    continue

                seen_tx.add(tx_hash)

                value_eth = int(tx["value"]) / 10**18

                if value_eth >= MIN_ETH:
                    to_addr = tx["to"]
                    from_addr = tx["from"]
                    
                    # Signal logic
                    def is_exchange(address):
                        for ex in EXCHANGES.values():
                            if address.lower() in [a.lower() for a in ex]:
                                return True
                        return False

                    if wallet.lower() == from_addr.lower():
                        if is_exchange(to_addr):
                            signal = "🔴 STRONG SELL (Whale → Exchange)"
                        else:
                            signal = "🟡 Transfer Out"
                    else:
                        if is_exchange(from_addr):
                            signal = "🟢 STRONG BUY (Exchange → Whale)"
                        else:
                            signal = "🟡 Transfer In"

                    score = 0

                    if "STRONG BUY" in signal:
                        score += 3
                    elif "STRONG SELL" in signal:
                        score -= 3

                    # Bigger transactions = stronger signal
                    if value_eth > 100:
                        score += 2
                    elif value_eth > 50:
                        score += 1

                    global_score += score

                    message = f"""
    {signal}

    Wallet: {wallet}
    Amount: {value_eth:.2f} ETH
    Score: {score}

    Tx: https://etherscan.io/tx/{tx_hash}
    """

                    send_telegram(message)
            
            if global_score > 2:
                send_telegram("🟢 MARKET BULLISH (Whales Buying)")
            elif global_score < -2:
                send_telegram("🔴 MARKET BEARISH (Whales Selling)")

            global_score = 0
        
            time.sleep(60)  # check every 1 min


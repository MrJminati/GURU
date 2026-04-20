from fastapi import FastAPI
import threading
from bot import start_bot, shared_whales

app = FastAPI()

# ===== START BOT IN BACKGROUND =====
@app.on_event("startup")
def run_bot():
    thread = threading.Thread(target=start_bot)
    thread.daemon = True
    thread.start()

# ===== API ROUTES =====
@app.get("/")
def home():
    return {"status": "running"}

@app.get("/whale-alerts")
def whale_alerts():
    return shared_whales[::-1]

@app.get("/top-wallets")
def top_wallets():
    return [
        {
            "address": "0x28C6...Binance",
            "win_rate": 0.78,
            "trades": 45,
            "roi": 120
        }
    ]

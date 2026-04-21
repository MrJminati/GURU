from fastapi import FastAPI
import threading
from bot import start_bot, shared_whales

app = FastAPI()

# 🚀 Start bot when server starts
@app.on_event("startup")
def run_bot():
    thread = threading.Thread(target=start_bot)
    thread.daemon = True
    thread.start()

@app.get("/")
def home():
    return {"status": "running"}

@app.get("/whale-alerts")
def whale_alerts():
    return shared_whales[::-1]  # latest first

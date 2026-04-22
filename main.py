from fastapi import FastAPI
import threading
from bot import start_bot, shared_whales

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all (for now)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

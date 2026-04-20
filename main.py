from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "running"}

@app.get("/top-wallets")
def top_wallets():
    return [
        {
            "address": "0xabc123",
            "win_rate": 0.78,
            "trades": 45,
            "roi": 120
        }
    ]

@app.get("/whale-alerts")
def whale_alerts():
    return [
        {
            "type": "Whale",
            "amount": 780000,
            "signal": "BUY"
        }
    ]

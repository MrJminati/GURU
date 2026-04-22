from fastapi import FastAPI
from supabase import create_client
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend to access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase connection
SUPABASE_URL = "YOUR_URL"
SUPABASE_KEY = "YOUR_KEY"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# API endpoint
@app.get("/signals")
def get_signals():
    res = supabase.table("signals") \
        .select("*") \
        .order("id", desc=True) \
        .limit(50) \
        .execute()

    return res.data

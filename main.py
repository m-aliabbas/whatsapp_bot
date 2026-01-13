import os
import time
import threading
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from neonize.client import NewClient
from neonize.events import ConnectedEv, MessageEv, PairStatusEv, event
from neonize.utils import build_jid

# 1. SETUP LOGGING & ENVIRONMENT
# Force logs to appear immediately in Leapcell
logging.basicConfig(level=logging.INFO)
os.environ["PYTHONUNBUFFERED"] = "1"

app = FastAPI(title="WhatsApp Bot API")

# 2. GLOBAL STATE
connection_status = {
    "connected": False,
    "message": "Initializing...",
    "pairing_code": None
}

# 3. DATABASE PATH (Must be /tmp for Leapcell)
DB_PATH = "/tmp/my_bot_session.db"
client = NewClient(DB_PATH)

# 4. MODELS
class SendMessageRequest(BaseModel):
    phone_number: str
    message: str

class ConnectionStatus(BaseModel):
    connected: bool
    message: str
    pairing_code: Optional[str] = None

# 5. EVENT HANDLERS
@client.event(ConnectedEv)
def on_connected(client: NewClient, _: ConnectedEv):
    logging.info("✅ Connection Established!")
    connection_status["connected"] = True
    connection_status["message"] = "Connected successfully"
    connection_status["pairing_code"] = None

@client.event(PairStatusEv)
def on_pair_status(client: NewClient, pair: PairStatusEv):
    if pair.ID.User:
        logging.info(f"✅ Logged in as: {pair.ID.User}")
        connection_status["connected"] = True

@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    # Logs incoming messages to Leapcell console
    if message.message.conversation:
        logging.info(f"📩 Msg from {message.info.sender}: {message.message.conversation}")

# 6. BACKGROUND WORKER (The "Logic" Fix)
def run_whatsapp_client():
    try:
        logging.info("⏳ Step 1: Connecting WebSocket...")
        # We must connect BEFORE requesting a pairing code
        client.connect()
        
        # Give the WebSocket time to handshake (The "Anti-Panic" Sleep)
        time.sleep(10)
        
        if not connection_status["connected"]:
            phone_number = os.getenv("WHATSAPP_PHONE", "923171585452")
            logging.info(f"⏳ Step 2: Requesting Pairing Code for {phone_number}")
            
            # Requesting the code
            code = client.PairPhone(phone_number, show_push_notification=True)
            connection_status["pairing_code"] = code
            connection_status["message"] = f"Enter code on phone: {code}"
            
            print("\n" + "="*30, flush=True)
            print(f"🔑 PAIRING CODE: {code}", flush=True)
            print("="*30 + "\n", flush=True)
            
    except Exception as e:
        logging.error(f"❌ WhatsApp Loop Error: {e}")
        connection_status["message"] = f"Error: {str(e)}"

# 7. API ENDPOINTS
@app.on_event("startup")
async def startup_event():
    # Start WhatsApp in a background thread
    thread = threading.Thread(target=run_whatsapp_client, daemon=True)
    thread.start()

@app.get("/")
async def root():
    return {"status": "online", "bot_connected": connection_status["connected"]}

# Catching BOTH spellings of the Leapcell healthcheck
@app.get("/kaithhealthcheck")
@app.get("/kaithheathcheck")
async def health_check():
    return {"status": "ok"}

@app.get("/status", response_model=ConnectionStatus)
async def get_status():
    return connection_status

@app.post("/send")
async def send_message(request: SendMessageRequest):
    if not connection_status["connected"]:
        raise HTTPException(status_code=503, detail="Bot not connected")
    try:
        jid = build_jid(request.phone_number)
        client.send_message(jid, request.message)
        return {"status": "sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Leapcell usually uses uvicorn directly, but this is here for local testing
    uvicorn.run(app, host="0.0.0.0", port=8080)
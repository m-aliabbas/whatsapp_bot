import logging
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
from neonize.client import NewClient
from neonize.events import ConnectedEv, MessageEv, PairStatusEv, event
from neonize.utils import build_jid
import threading

# Initialize FastAPI app
app = FastAPI(
    title="WhatsApp Bot API",
    description="FastAPI wrapper for Neonize WhatsApp Bot",
    version="1.0.0"
)

# Initialize the WhatsApp client
client = NewClient("/tmp/my_bot_session.db")

# Global state
connection_status = {
    "connected": False,
    "message": "Not connected yet",
    "pairing_code": None
}

# Pydantic models for request/response
class SendMessageRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., 923171585452)")
    message: str = Field(..., description="Message to send")

class SendMessageResponse(BaseModel):
    status: str
    message: str
    phone_number: str

class ConnectionStatus(BaseModel):
    connected: bool
    message: str
    pairing_code: Optional[str] = None

class MessageInfo(BaseModel):
    from_number: Optional[str] = None
    message_text: Optional[str] = None
    timestamp: Optional[str] = None

# Event handlers
@client.event(ConnectedEv)
def on_connected(client: NewClient, _: ConnectedEv):
    print("✅ Connection Established! You are now online.")
    connection_status["connected"] = True
    connection_status["message"] = "Connected successfully"
    connection_status["pairing_code"] = None

@client.event(PairStatusEv)
def on_pair_status(client: NewClient, pair: PairStatusEv):
    if pair.ID.User:
        print(f"✅ Logged in as: {pair.ID.User}")
        connection_status["connected"] = True
        connection_status["message"] = f"Logged in as: {pair.ID.User}"

@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    # Basic auto-reply logic
    if message:
        print(f"📩 New message from {message}")

# Background task to run the WhatsApp client
def run_whatsapp_client():
    try:
        # Get phone number from environment variable or use default
        phone_number = os.getenv("WHATSAPP_PHONE", "923025114945")
        
        # Request pairing code for your phone number (PairPhone with capital letters)
        pairing_code = client.PairPhone(
            phone_number,
            show_push_notification=True
        )
        
        connection_status["pairing_code"] = pairing_code
        connection_status["message"] = f"Use pairing code: {pairing_code}"
        
        print(f"🔑 Your pairing code: {pairing_code}")
        print("Enter this code in WhatsApp → Linked Devices → Link with phone number")
        
        # Connect after pairing
        client.connect()
    except Exception as e:
        print(f"Error connecting WhatsApp client: {e}")
        connection_status["connected"] = False
        connection_status["message"] = f"Connection error: {str(e)}"

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Start the WhatsApp client in a background thread when the API starts"""
    thread = threading.Thread(target=run_whatsapp_client, daemon=True)
    thread.start()
    print("🚀 WhatsApp client started in background")

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check"""
    return {
        "status": "running",
        "service": "WhatsApp Bot API",
        "version": "1.0.0"
    }

@app.get("/kaithhealthcheck", tags=["Health"])
async def kaith_health_check():
    """Kaith health check endpoint"""
    return {
        "status": "ok",
        "service": "whatsapp-bot",
        "connected": connection_status["connected"]
    }

@app.get("/status", response_model=ConnectionStatius, tags=["Status"])
async def get_status():
    """Get the current connection status of the WhatsApp bot"""
    return connection_status

@app.post("/send", response_model=SendMessageResponse, tags=["Messages"])
async def send_message(request: SendMessageRequest):
    """
    
    - **phone_number**: Phone number with country code (no + or spaces)
    - **message**: The message text to send
    """
    if not connection_status["connected"]:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot is not connected. Please wait for connection or scan QR code."
        )
    
    try:
        # Build JID and send message
        jid = build_jid(request.phone_number)
        client.send_message(jid, request.message)
        
        return SendMessageResponse(
            status="success",
            message="Message sent successfully",
            phone_number=request.phone_number
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )

@app.post("/send-bulk", tags=["Messages"])
async def send_bulk_messages(
    phone_numbers: list[str],
    message: str
):
    """
    Send the same message to multiple phone numbers
    
    - **phone_numbers**: List of phone numbers with country codes
    - **message**: The message text to send to all numbers
    """
    if not connection_status["connected"]:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot is not connected. Please wait for connection or scan QR code."
        )
    
    results = []
    for phone in phone_numbers:
        try:
            jid = build_jid(phone)
            client.send_message(jid, message)
            results.append({
                "phone_number": phone,
                "status": "success",
                "message": "Message sent"
            })
        except Exception as e:
            results.append({
                "phone_number": phone,
                "status": "error",
                "message": str(e)
            })
    
    return {
        "total": len(phone_numbers),
        "results": results
    }

@app.post("/disconnect", tags=["Connection"])
async def disconnect():
    """Disconnect the WhatsApp bot"""
    try:
        # Note: You may need to implement a proper disconnect method
        # depending on the Neonize client capabilities
        connection_status["connected"] = False
        connection_status["message"] = "Disconnected by user"
        return {"status": "success", "message": "Disconnected successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect: {str(e)}"
        )

if __name__ == "__main__":
    print("🚀 Starting WhatsApp Bot API...")
    print("📱 If not authenticated, scan the QR code in the terminal")
    print("📡 Using pairing code authentication")
    print("🔐 Pairing code will be displayed in terminal and available via /status endpoint")
    print("📡 API will be available at http://localhost:8000")
    print("📚 API docs available at http://localhost:8000/docs")
    print(f"📞 Phone number: {os.getenv('WHATSAPP_PHONE', '923171585452')}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

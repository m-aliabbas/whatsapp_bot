import logging
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
from neonize.client import NewClient
from neonize.events import ConnectedEv, MessageEv, PairStatusEv, LoggedOutEv, event
from neonize.utils import build_jid
import threading
import time
import datetime
import sys
import asyncio

def get_today_date_time_pakistan_time():
    """Get today's date and time in Pakistan timezone"""
    pakistan_tz = datetime.timezone(datetime.timedelta(hours=5))
    now = datetime.datetime.now(pakistan_tz)
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

# Initialize FastAPI app
app = FastAPI(
    title="WhatsApp Bot API",
    description="FastAPI wrapper for Neonize WhiatsApp Bot",
    version="1.0.0"
)

# Initialize the WhatsApp client
client = NewClient("my_bot_session.db")

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

class SendImageRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., 923171585452)")
    image_url: str = Field(..., description="URL of the image to send")
    caption: Optional[str] = Field(None, description="Optional caption for the image")

class SendAudioRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., 923171585452)")
    audio_url: str = Field(..., description="URL of the audio file to send")

class SendDocumentRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., 923171585452)")
    document_url: str = Field(..., description="URL of the document to send")
    caption: Optional[str] = Field(None, description="Optional caption for the document")
    filename: Optional[str] = Field(None, description="Optional filename for the document")

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

@client.event(LoggedOutEv)
def on_logged_out(client: NewClient, evt: LoggedOutEv):
    print(f"❌ Disconnected: {evt.Reason}")
    connection_status["connected"] = False
    connection_status["message"] = f"Disconnected: {evt.Reason}"
    connection_status["pairing_code"] = None

@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    # Basic auto-reply logic
    if message:
        # print(f"📩 New message from {message}")
        sender = str(message.Info.MessageSource.Sender.User)
        # type = str(message.Type)
        print(f"📩 New message from {sender} ")
        # print(message)
        if message.Message.extendedTextMessage:
            text = message.Message.extendedTextMessage.text

            if 'report' in text.lower():
                date_tme = get_today_date_time_pakistan_time()
                time.sleep(2)  # Simulate processing delay
                reply = "This is dummy report. Total sales: $1000. {} Date: {}, Time: {}".format("POS123", date_tme[0], date_tme[1])
                client.reply_message(reply, message)
        

    

# Background task to run the WhatsApp client
def run_whatsapp_client():
    try:
        # Get phone number from environment variable or use default
        phone_number = os.getenv("WHATSAPP_PHONE", "923025114945")
        
        # Check if we should use QR code (set USE_QR=1 to skip pairing)
        use_qr = os.getenv("USE_QR", "0") == "1"
        
        if use_qr:
            print("📱 Using QR Code authentication (USE_QR enabled)")
            print("📱 Scan the QR code below with WhatsApp:")
            print("")
            client.connect()
            connection_status["message"] = "Using QR code authentication"
        else:
            print(f"📞 Attempting pairing code authentication for: {phone_number}")
            print("💡 Tip: If you get rate limited, restart with: USE_QR=1 python main.py")
            
            try:
                # Try pairing code first
                pairing_code = client.PairPhone(
                    phone_number,
                    show_push_notification=True
                )
                
                print(f"🔑 Your pairing code: {pairing_code}")
                print("Enter this code in WhatsApp → Linked Devices → Link with phone number")
                
                # Connect after pairing
                client.connect()
                
            except Exception as pair_error:
                error_msg = str(pair_error)
                
                # Check if it's a rate limit error
                if "429" in error_msg or "rate" in error_msg.lower() or "overlimit" in error_msg.lower():
                    print("")
                    print("⚠️  Rate limit detected! Falling back to QR Code authentication...")
                    print("📱 Scan the QR code below with WhatsApp:")
                    print("")
                    
                    # Fall back to QR code
                    client.connect()
                    connection_status["message"] = "Using QR code authentication (rate limited on pairing)"
                else:
                    # Re-raise if it's not a rate limit error
                    raise pair_error
                
    except Exception as e:
        print(f"❌ Error connecting WhatsApp client: {e}")
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

@app.get("/status", response_model=ConnectionStatus, tags=["Status"])
async def get_status():
    """Get the current connection status of the WhatsApp bot"""
    return connection_status

@app.get("/connected", tags=["Status"])
async def is_connected():
    """Check if WhatsApp is currently connected (real-time status)"""
    # Check actual client connection state
    is_actually_connected = connection_status["connected"] and client.is_logged_in
    
    if not is_actually_connected and connection_status["connected"]:
        connection_status["connected"] = False
        connection_status["message"] = "Connection lost"
    
    return {
        "connected": is_actually_connected,
        "timestamp": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5))).isoformat()
    }

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

@app.post("/send-image", response_model=SendMessageResponse, tags=["Messages"])
async def send_image(request: SendImageRequest):
    """
    Send an image to a WhatsApp number
    
    - **phone_number**: Phone number with country code (no + or spaces)
    - **image_url**: URL of the image to send
    - **caption**: Optional caption for the image
    """
    if not connection_status["connected"]:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot is not connected. Please wait for connection or scan QR code."
        )
    
    try:
        # Build JID and send image
        jid = build_jid(request.phone_number)
        client.send_image(
            jid,
            request.image_url,
            caption=request.caption or ""
        )
        
        return SendMessageResponse(
            status="success",
            message="Image sent successfully",
            phone_number=request.phone_number
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send image: {str(e)}"
        )

@app.post("/send-audio", response_model=SendMessageResponse, tags=["Messages"])
async def send_audio(request: SendAudioRequest):
    """
    Send an audio file to a WhatsApp number
    
    - **phone_number**: Phone number with country code (no + or spaces)
    - **audio_url**: URL of the audio file to send
    """
    if not connection_status["connected"]:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot is not connected. Please wait for connection or scan QR code."
        )
    
    try:
        # Build JID and send audio
        jid = build_jid(request.phone_number)
        client.send_audio(
            jid,
            request.audio_url
        )
        
        return SendMessageResponse(
            status="success",
            message="Audio sent successfully",
            phone_number=request.phone_number
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send audio: {str(e)}"
        )

@app.post("/send-document", response_model=SendMessageResponse, tags=["Messages"])
async def send_document(request: SendDocumentRequest):
    """
    Send a document to a WhatsApp number
    
    - **phone_number**: Phone number with country code (no + or spaces)
    - **document_url**: URL of the document to send
    - **caption**: Optional caption for the document
    - **filename**: Optional filename for the document
    """
    if not connection_status["connected"]:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp bot is not connected. Please wait for connection or scan QR code."
        )
    
    try:
        # Build JID and send document
        jid = build_jid(request.phone_number)
        client.send_document(
            jid,
            request.document_url,
            caption=request.caption or "",
            filename=request.filename or ""
        )
        
        return SendMessageResponse(
            status="success",
            message="Document sent successfully",
            phone_number=request.phone_number
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send document: {str(e)}"
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

@app.post("/restart", tags=["Connection"])
async def restart_server():
    """Restart the WhatsApp bot server"""
    try:
        connection_status["message"] = "Restarting server..."
        
        # Restart the application using os.execv
        def do_restart():
            time.sleep(1)  # Give time for response to be sent
            python = sys.executable
            os.execv(python, [python] + sys.argv)
        
        # Run restart in background thread
        restart_thread = threading.Thread(target=do_restart, daemon=True)
        restart_thread.start()
        
        return {
            "status": "success",
            "message": "Server is restarting..."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart: {str(e)}"
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
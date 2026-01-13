# WhatsApp Bot FastAPI Wrapper

A FastAPI wrapper around the Neonize WhatsApp bot for easy integration via REST API.

## Installation

```bash
pip install -r requirements.txt
```

## Running the API

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Health Check
- `GET /` - Check if API is running
- `GET /status` - Get WhatsApp connection status

### Send Messages
- `POST /send` - Send a message to a single phone number
- `POST /send-bulk` - Send the same message to multiple phone numbers

### Connection Management
- `POST /disconnect` - Disconnect the WhatsApp bot

## Usage Examples

### Check Connection Status
```bash
curl http://localhost:8000/status
```

### Send a Message
```bash
curl -X POST http://localhost:8000/send \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "923171585452",
    "message": "Hello from FastAPI! 🚀"
  }'
```

### Send Bulk Messages
```bash
curl -X POST http://localhost:8000/send-bulk \
  -H "Content-Type: application/json" \
  -d '{
    "phone_numbers": ["923171585452", "923001234567"],
    "message": "Bulk message test!"
  }'
```

## Interactive API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## First Time Setup

When you run the API for the first time, a QR code will be displayed in the terminal. Scan it with your WhatsApp mobile app to authenticate the bot.

## Notes

- Phone numbers should include country code without '+' or spaces (e.g., 923171585452)
- The bot must be connected before sending messages
- Session is saved in `my_bot_session.db` file

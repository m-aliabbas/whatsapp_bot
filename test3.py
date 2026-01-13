import logging
from neonize.client import NewClient
from neonize.events import ConnectedEv, MessageEv, event
from neonize.utils import build_jid

# 1. Initialize the client with a session file name
# This file will store your 'keys' after the first scan.
client = NewClient("my_bot_session.db")

@client.event(ConnectedEv)
def on_connected(client: NewClient, _: ConnectedEv):
    print("✅ Connection Established! You are now online.")

@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    # Basic auto-reply logic
    if message:
        print(f"📩 New message from {message}")
    client.send_message(build_jid("923171585452"), "Hello from Neonize! 🚀")
    # client.send_message()

# 2. This command checks if a session exists. 
# If not, it will print a QR code in your terminal.
client.connect()
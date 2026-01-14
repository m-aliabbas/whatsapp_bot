#!/bin/bash

# Build standalone executable
pip install pyinstaller
pyinstaller --onefile --name whatsapp-bot --hidden-import uvicorn main.py

echo "Executable created in dist/whatsapp-bot"

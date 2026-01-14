#!/bin/bash

# Install pyarmor
pip install pyarmor

# Obfuscate the code
pyarmor gen main.py

echo "Obfuscated code created in dist/ folder"
echo "Distribute the dist/ folder to clients"

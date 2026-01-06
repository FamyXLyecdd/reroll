#!/bin/bash

echo "========================================"
echo "  Termux Orchestrator Setup"
echo "========================================"

echo "[*] Updating packages..."
pkg update -y

echo "[*] Installing Python & ADB..."
pkg install python android-tools -y

echo "[*] Installing Python dependencies..."
pip install requests

echo "[*] Granting storage permission (if needed)..."
termux-setup-storage

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo "To start the orchestrator:"
echo "1. Enable Wireless Debugging on your phone"
echo "2. Run: python termux_manager.py"
echo "========================================"

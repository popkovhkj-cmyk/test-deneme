#!/bin/bash

# Termux Full Storage Dump Kurulum Betiği

echo "Termux paketlerini güncelliyor..."
pkg update -y

echo "Gerekli Termux paketlerini kuruyor (python, git, termux-api)..."
pkg install python -y
pkg install git -y
pkg install termux-api -y

echo "Python kütüphanelerini kuruyor..."
pip install -r requirements.txt

echo "Depolama erişimini ayarlıyor..."
termux-setup-storage

echo "Kurulum tamamlandı. Betiği çalıştırmak için: python main.py"

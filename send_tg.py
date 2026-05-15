#!/usr/bin/env python3
"""Send files to Telegram bot."""
import sys, requests

TOKEN = "8777124489:AAHlYl_EiS2JiIQB3Y6l7-nRe94abAWMOCw"
CHAT_ID = "8616425991"
PROXY = "http://127.0.0.1:15732"

def send_file(filepath):
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    proxies = {"http": PROXY, "https": PROXY} if PROXY else None
    with open(filepath, "rb") as f:
        resp = requests.post(url, files={"document": f}, data={"chat_id": CHAT_ID}, proxies=proxies)
    if resp.status_code == 200:
        print(f"  Sent: {filepath}")
    else:
        print(f"  Failed: {filepath} — {resp.text[:200]}")

for fp in sys.argv[1:]:
    send_file(fp)

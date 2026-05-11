#!/usr/bin/env python3
"""Send files to Telegram bot."""
import os, sys, requests

TOKEN = "8777124489:AAHlYl_EiS2JiIQB3Y6l7-nRe94abAWMOCw"
CHAT_ID = "8616425991"
PROXY = "http://127.0.0.1:15732"

def send_file(filepath, caption=""):
    """Send a document via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"

    proxies = None
    if PROXY:
        proxies = {"http": PROXY, "https": PROXY}

    fname = os.path.basename(filepath)
    try:
        with open(filepath, "rb") as f:
            resp = requests.post(
                url,
                data={"chat_id": CHAT_ID, "caption": caption or fname},
                files={"document": (fname, f)},
                proxies=proxies,
                timeout=30,
            )
        result = resp.json()
        if result.get("ok"):
            print(f"  Sent: {fname}")
        else:
            print(f"  Failed: {fname} — {result.get('description')}")
        return result.get("ok", False)
    except Exception as e:
        print(f"  Error: {fname} — {e}")
        return False

def send_message(text):
    """Send a text message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    proxies = {"http": PROXY, "https": PROXY} if PROXY else None
    try:
        resp = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"},
            proxies=proxies,
            timeout=15,
        )
        return resp.json().get("ok", False)
    except Exception as e:
        print(f"  Message error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 send_tg.py <file> [file2] ...")
        print("   or: python3 send_tg.py --msg \"text\"")
        sys.exit(1)

    if sys.argv[1] == "--msg":
        send_message(sys.argv[2])
    else:
        for f in sys.argv[1:]:
            if os.path.exists(f):
                send_file(f)
            else:
                print(f"  Not found: {f}")

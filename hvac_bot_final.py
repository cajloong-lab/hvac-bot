# -*- coding: utf-8 -*-
import os
import json
import time
import html
import requests
import xml.etree.ElementTree as ET

# --- CẤU HÌNH THÔNG TIN ---
TELEGRAM_BOT_TOKEN = "9112810435:AAFutn9YliqCddPo2V1d-EjMVAZWQ_LkA8o"
TELEGRAM_CHAT_ID = "877586198"

# Lọc tin tức thị trường điều hòa / máy lạnh tại Việt Nam
RSS_URL = "https://news.google.com/rss/search?q=(%22điều+hòa%22+OR+%22máy+lạnh%22)+thị+trường+Việt+Nam+when:3d&hl=vi&gl=VN&ceid=VN:vi"
SEEN_FILE = "seen_articles.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_seen(seen_list):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_list[-200:], f, ensure_ascii=False, indent=2)

def fetch_rss_news():
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(RSS_URL, headers=headers, timeout=15)
    root = ET.fromstring(resp.content)
    items = []
    for item in root.findall("./channel/item"):
        title = item.find("title").text if item.find("title") is not None else ""
        link = item.find("link").text if item.find("link") is not None else ""
        items.append({"title": title, "link": link})
    return items

def send_telegram_message(title, link):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Thoát ký tự HTML an toàn
    safe_title = html.escape(title)
    
    message_text = (
        f"❄️ <b>BẢN TIN THỊ TRƯỜNG ĐIỀU HÒA VN</b>\n\n"
        f"📰 <b>{safe_title}</b>\n\n"
        f"🔗 <a href='{link}'>Bấm vào đây để đọc bài viết</a>"
    )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(url, json=payload, timeout=15)
        if res.status_code == 200:
            print(f"[OK] Đã gửi: {title}")
        else:
            print(f"[Lỗi Telegram] {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[Lỗi kết nối Telegram]: {e}")

def run_job():
    print(f"Đang quét tin tức thị trường điều hòa cho chat ID {TELEGRAM_CHAT_ID}...")
    articles = fetch_rss_news()
    seen = load_seen()
    new_seen = list(seen)

    for item in articles[:5]:
        link = item["link"]
        if link in seen:
            continue
        print(f"-> Xử lý và gửi: {item['title']}")
        send_telegram_message(item["title"], link)
        new_seen.append(link)
        time.sleep(1)

    save_seen(new_seen)
    print("Hoàn thành chu kỳ quét.")

if __name__ == "__main__":
    run_job()

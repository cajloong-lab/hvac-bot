# -*- coding: utf-8 -*-
import os
import json
import time
import html
import requests
import xml.etree.ElementTree as ET

# --- CẤU HÌNH THÔNG TIN ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9112810435:AAFutn9YliqCddPo2V1d-EjMVAZWQ_LkA8o")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6LBHujRi4lqEHiGFlULjWJiHszEhxIWkn-9PPbNDEgR3g")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "877586198")

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
        desc = item.find("description").text if item.find("description") is not None else ""
        items.append({"title": title, "link": link, "desc": desc})
    return items

def summarize_with_gemini(title, summary_raw):
    """Gọi trực tiếp REST API của Gemini hỗ trợ cả API Key lẫn Auth Token"""
    prompt_text = f"""Bạn là chuyên gia phân tích thị trường điện máy & điều hòa không khí Việt Nam.
Hãy đọc thông tin sau và tóm tắt ngắn gọn:

Tiêu đề: {title}
Nội dung ban đầu: {summary_raw}

Yêu cầu định dạng (tối đa 3 dòng, không dùng thẻ html):
- Trọng tâm: Tóm lược sự kiện (doanh số, chính sách hãng, giá cả, thời tiết...)
- Hãng/Thương hiệu: Tên hãng hoặc chuỗi liên quan (Daikin, Casper, Panasonic, MediaMart...)
- Tác động nhanh: Nhận định nhanh ảnh hưởng tới thị trường."""

    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }

    # Phương án 1: Thử gọi qua URL query param thông thường
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        
        # Phương án 2: Nếu bị chặn do token type, dùng Authorization Header
        if res.status_code == 401 or res.status_code == 400:
            auth_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
            auth_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GEMINI_API_KEY}"
            }
            res = requests.post(auth_url, headers=auth_headers, json=payload, timeout=20)

        if res.status_code == 200:
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        print(f"Lỗi phản hồi Gemini ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"Lỗi kết nối Gemini: {e}")

    return "Xem chi tiết tin tức tại đường link bên dưới."

def send_telegram_message(title, summary, link):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    safe_title = html.escape(title)
    safe_summary = html.escape(summary)
    
    message_text = (
        f"❄️ <b>BẢN TIN THỊ TRƯỜNG ĐIỀU HÒA VN</b>\n\n"
        f"📰 <b>{safe_title}</b>\n\n"
        f"💡 <b>Tóm tắt AI:</b>\n{safe_summary}\n\n"
        f"🔗 <a href='{link}'>Đọc toàn bộ bài viết</a>"
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
        print(f"-> Xử lý: {item['title']}")
        ai_summary = summarize_with_gemini(item["title"], item["desc"])
        send_telegram_message(item["title"], ai_summary, link)
        new_seen.append(link)
        time.sleep(2)

    save_seen(new_seen)
    print("Hoàn thành chu kỳ quét.")

if __name__ == "__main__":
    run_job()

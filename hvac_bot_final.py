# -*- coding: utf-8 -*-
import os
import json
import time
import requests
import xml.etree.ElementTree as ET
from google import genai

# --- CẤU HÌNH THÔNG TIN ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "9112810435:AAFutn9YliqCddPo2V1d-EjMVAZWQ_LkA8o")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6Lds-9Izvd5Nq8wlBe7PkV9Bl7NLmmIt2X_w69kLXtc6A")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@acmaketwatchbot")

RSS_URL = "https://news.google.com/rss/search?q=điều+hòa+thị+trường+Việt+Nam+when:2d&hl=vi&gl=VN&ceid=VN:vi"
SEEN_FILE = "seen_articles.json"

client = genai.Client(api_key=GEMINI_API_KEY)

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
    prompt = f"""Bạn là chuyên gia phân tích thị trường điện máy & HVAC (điều hòa không khí) Việt Nam.
Hãy đọc thông tin sau và tóm tắt ngắn gọn cho bản tin Telegram:

Tiêu đề: {title}
Tóm tắt ban đầu: {summary_raw}

Yêu cầu định dạng (tối đa 3 dòng):
- Trọng tâm: Tóm lược sự kiện (doanh số, chính sách hãng, giá cả, thời tiết...)
- Hãng/Thương hiệu: Tên hãng hoặc chuỗi liên quan (Daikin, Casper, Panasonic, MediaMart...)
- Tác động nhanh: Nhận định nhanh ảnh hưởng tới thị trường."""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"Lỗi gọi Gemini API: {e}")
        return summary_raw[:200] + "..." if summary_raw else "Xem chi tiết tại link."

def send_telegram_message(title, summary, link):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    message_text = (
        f"❄️ <b>BẢN TIN THỊ TRƯỜNG ĐIỀU HÒA VN</b>\n\n"
        f"📰 <b>{title}</b>\n\n"
        f"💡 <b>Tóm tắt AI:</b>\n{summary}\n\n"
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
    print(f"Đang quét tin tức và gửi tới {TELEGRAM_CHAT_ID}...")
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

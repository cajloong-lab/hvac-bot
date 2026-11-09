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

# 1. Luồng tin tức báo chí & thị trường điện máy/HVAC
RSS_NEWS_URL = (
    "https://news.google.com/rss/search?q="
    "(%22điều+hòa%22+OR+%22máy+lạnh%22+OR+%22Daikin%22+OR+%22Panasonic%22+OR+%22Casper%22+OR+"
    "%22Nagakawa%22+OR+%22Funiki%22+OR+%22gas+R32%22+OR+%22Điện+Máy+Xanh%22)"
    "+when:3d&hl=vi&gl=VN&ceid=VN:vi"
)

# 2. Luồng quét thảo luận cộng đồng, thợ kỹ thuật & người tiêu dùng (Facebook, Diễn đàn)
RSS_COMMUNITY_URL = (
    "https://news.google.com/rss/search?q="
    "(site:facebook.com+OR+site:otofun.net+OR+site:tinhte.vn+OR+site:voz.vn)+"
    "(%22thợ+điện+lạnh%22+OR+%22lỗi+Daikin%22+OR+%22điều+hòa+Casper%22+OR+%22máy+lạnh+Panasonic%22+OR+%22hỏng+bo+mạch%22+OR+%22xì+gas%22)"
    "+when:7d&hl=vi&gl=VN&ceid=VN:vi"
)

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
        json.dump(seen_list[-250:], f, ensure_ascii=False, indent=2)

def fetch_rss_feed(url, source_type="BÁO CHÍ & THỊ TRƯỜNG"):
    headers = {"User-Agent": "Mozilla/5.0"}
    items = []
    junk_words = ["đường sắt", "metro", "toa tàu", "toa xe", "chung cư", "nhà ở xã hội", "outlander", "ô tô"]
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        root = ET.fromstring(resp.content)
        for item in root.findall("./channel/item"):
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            desc = item.find("description").text if item.find("description") is not None else ""
            
            if any(jw in title.lower() for jw in junk_words):
                continue
                
            items.append({
                "title": title,
                "link": link,
                "desc": desc,
                "source_type": source_type
            })
    except Exception as e:
        print(f"Lỗi khi đọc feed ({source_type}): {e}")
        
    return items

def analyze_market_for_daikin(title, summary_raw, source_type):
    prompt_text = f"""Bạn là Giám đốc Chiến lược & Phân tích Thị trường của DAIKIN Việt Nam.
Hãy đọc thông tin sau (Nguồn: {source_type}) và trích xuất nhận định chiến lược:

Tiêu đề: {title}
Nội dung: {summary_raw}

Yêu cầu định dạng báo cáo (Viết súc tích, sắc bén, không dùng thẻ html):
1. Tóm tắt cốt lõi: (Đối với báo chí: động thái đối thủ Casper/Panasonic, giá cả, khuyến mãi chuỗi bán lẻ. Đối với cộng đồng/Facebook: phản ánh thực tế của thợ kỹ thuật, lỗi hay gặp, đánh giá chất lượng máy, độ bền bo mạch, phản hồi của người dùng).
2. Tác động tới Daikin: (Đánh giá ảnh hưởng đến thị phần, hình ảnh thương hiệu hoặc uy tín kỹ thuật của Daikin).
3. Action Plan đề xuất: (1-2 việc cụ thể Daikin nên triển khai ngay: chính sách bán hàng, hỗ trợ kỹ thuật cho thợ, kho linh kiện, hay đào tạo trạm bảo hành)."""

    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        
        if res.status_code in [400, 401]:
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

    return "Không thể phân tích AI. Vui lòng bấm link gốc để đọc chi tiết."

def send_telegram_message(title, analysis, link, source_type):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    safe_title = html.escape(title)
    safe_analysis = html.escape(analysis)
    
    tag_icon = "📢 [COMMUNITY & THỢ]" if "FACEBOOK" in source_type else "📰 [BÁO CHÍ & ĐỐI THỦ]"
    
    message_text = (
        f"🎯 <b>INTEL THỊ TRƯỜNG HVAC - DAIKIN VIETNAM</b>\n"
        f"<b>Phân loại:</b> {tag_icon}\n\n"
        f"📌 <b>Nội dung:</b> {safe_title}\n\n"
        f"📊 <b>PHÂN TÍCH & ACTION PLAN:</b>\n{safe_analysis}\n\n"
        f"🔗 <a href='{link}'>Xem nguồn gốc bài viết</a>"
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
    print(f"Đang quét dữ liệu báo chí & thảo luận thợ điện lạnh cho Daikin...")
    
    news_items = fetch_rss_feed(RSS_NEWS_URL, source_type="BÁO CHÍ & THỊ TRƯỜNG")
    community_items = fetch_rss_feed(RSS_COMMUNITY_URL, source_type="FACEBOOK & DIỄN ĐÀN THỢ")
    
    all_articles = (community_items[:3] + news_items[:3])
    seen = load_seen()
    new_seen = list(seen)

    for item in all_articles:
        link = item["link"]
        if link in seen:
            continue
            
        print(f"-> Phân tích ({item['source_type']}): {item['title']}")
        analysis = analyze_market_for_daikin(item["title"], item["desc"], item["source_type"])
        send_telegram_message(item["title"], analysis, link, item["source_type"])
        new_seen.append(link)
        time.sleep(2)

    save_seen(new_seen)
    print("Hoàn thành chu kỳ quét.")

if __name__ == "__main__":
    run_job()

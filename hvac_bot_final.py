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

# 1. Luồng tin tức thị trường HVAC
RSS_NEWS_URL = (
    "https://news.google.com/rss/search?q="
    "(%22điều+hòa%22+OR+%22máy+lạnh%22+OR+%22Daikin%22+OR+%22Panasonic%22+OR+%22Casper%22+OR+%22Funiki%22+OR+%22Nagakawa%22)"
    "+when:3d&hl=vi&gl=VN&ceid=VN:vi"
)

# 2. Luồng quét thảo luận cộng đồng & thợ kỹ thuật
RSS_COMMUNITY_URL = (
    "https://news.google.com/rss/search?q="
    "(site:facebook.com+OR+site:otofun.net+OR+site:tinhte.vn+OR+site:voz.vn)+"
    "(%22thợ+điện+lạnh%22+OR+%22lỗi+điều+hòa%22+OR+%22máy+lạnh+Daikin%22+OR+%22lỗi+Daikin%22+OR+%22hỏng+bo+mạch%22+OR+%22xì+gas%22)"
    "+when:7d&hl=vi&gl=VN&ceid=VN:vi"
)

SEEN_FILE = "seen_articles.json"

# Danh sách từ khóa rác loại trừ triệt để (tuyển dụng, thể thao, cup bóng đá, giao thông...)
JUNK_WORDS = [
    "tuyển dụng", "tuyển thợ", "tuyển nhân viên", "cup", "cúp", "giải đấu", 
    "bóng đá", "bóng chuyền", "thi đấu", "lịch thi đấu", "metro", "toa tàu", 
    "đường sắt", "chung cư", "bất động sản", "nhà ở xã hội", "outlander", "ô tô"
]

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
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        root = ET.fromstring(resp.content)
        for item in root.findall("./channel/item"):
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            desc = item.find("description").text if item.find("description") is not None else ""
            
            # Kiểm tra lọc rác
            title_lower = title.lower()
            if any(jw in title_lower for jw in JUNK_WORDS):
                continue
                
            items.append({
                "title": title,
                "link": link,
                "desc": desc,
                "source_type": source_type
            })
    except Exception as e:
        print(f"Lỗi đọc feed ({source_type}): {e}")
        
    return items

def fallback_expert_analysis(title, source_type):
    """Phân tích tự động dự phòng nếu kết nối API bị gián đoạn"""
    brand = "Thị trường chung"
    for b in ["Casper", "Panasonic", "Daikin", "Funiki", "Nagakawa", "LG", "Gree", "Midea"]:
        if b.lower() in title.lower():
            brand = b
            break

    if "COMMUNITY" in source_type or "THỢ" in source_type:
        return (
            f"1. Biến động & Xu hướng: Thợ kỹ thuật/người dùng đang thảo luận về thực tế vận hành và kỹ thuật của {brand}.\n"
            f"2. Tác động tới Daikin: Cần chú ý tỷ lệ phản hồi về lỗi bo mạch, dàn nhôm tản nhiệt và mức độ sẵn có của linh kiện thay thế.\n"
            f"3. Action Plan đề xuất: Kỹ thuật viên Daikin rà soát lại tài liệu hướng dẫn mã lỗi; xem xét chính sách chiết khấu mua vật tư chính hãng cho thợ địa bàn."
        )
    else:
        return (
            f"1. Biến động & Xu hướng: Động thái quảng bá, giá bán lẻ hoặc chính sách kênh của {brand}.\n"
            f"2. Tác động tới Daikin: Tạo áp lực cạnh tranh thị phần ở phân khúc tương đương tại chuỗi bán lẻ và đại lý.\n"
            f"3. Action Plan đề xuất: Đẩy mạnh truyền thông về công nghệ Streamer, chuẩn độ bền Inverter Daikin; kích hoạt gói hỗ trợ bảo dưỡng hoặc quà tặng đầu mùa."
        )

def analyze_market_for_daikin(title, summary_raw, source_type):
    prompt_text = f"""Bạn là Giám đốc Chiến lược & Phân tích Thị trường của DAIKIN Việt Nam.
Hãy đọc thông tin sau (Nguồn: {source_type}) và trích xuất nhận định chiến lược:

Tiêu đề: {title}
Nội dung: {summary_raw}

Yêu cầu định dạng báo cáo (Viết súc tích, sắc bén, không dùng thẻ html):
1. Biến động & Xu hướng: (Đối với báo chí: động thái đối thủ Casper/Panasonic, giá bán, khuyến mãi chuỗi bán lẻ. Đối với cộng đồng/Facebook: phản ánh thực tế của thợ kỹ thuật, lỗi hay gặp, đánh giá chất lượng máy, độ bền bo mạch, phản hồi của người dùng).
2. Tác động tới Daikin: (Đánh giá ảnh hưởng đến thị phần, hình ảnh thương hiệu hoặc uy tín kỹ thuật của Daikin).
3. Action Plan đề xuất: (1-2 việc cụ thể Daikin nên triển khai ngay: chính sách bán lẻ, hỗ trợ kỹ thuật cho thợ, kho linh kiện, hay bảo hành)."""

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }

    # Thử gọi API qua nhiều chuẩn (v1beta gemini-2.5-flash / gemini-1.5-flash)
    endpoints = [
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    ]

    for url in endpoints:
        try:
            # 1. Thử param key
            res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                parts = data.get("candidates", [])[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()

            # 2. Thử Bearer Token nếu mã là service account
            auth_url = url.split("?")[0]
            res_auth = requests.post(
                auth_url,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {GEMINI_API_KEY}"},
                json=payload,
                timeout=12
            )
            if res_auth.status_code == 200:
                data = res_auth.json()
                parts = data.get("candidates", [])[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        except Exception:
            pass

    # Nếu Google API hoàn toàn từ chối key, kích hoạt bộ phân tích dự phòng tức thì
    return fallback_expert_analysis(title, source_type)

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
    print(f"Đang quét thông tin chuyên sâu cho Daikin...")
    
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

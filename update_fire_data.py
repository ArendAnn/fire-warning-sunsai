import os
import json
import requests
from datetime import datetime

# 1. ดึง API Key จาก GitHub Secrets
GISTDA_API_KEY = os.environ.get("GISTDA_API_KEY", "").strip()
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
LINE_TARGET_ID = os.environ.get("LINE_TARGET_ID", "").strip()

# ขอบเขตพิกัดอำเภอสันทราย จ.เชียงใหม่ (Bounding Box)
SANSAI_BOUNDS = {"min_lat": 18.80, "max_lat": 19.15, "min_lon": 98.94, "max_lon": 99.15}

def fetch_wind_data():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 19.015,
        "longitude": 99.035,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
        "timezone": "Asia/Bangkok"
    }
    try:
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200:
            return res.json().get("current", {})
    except Exception as e:
        print(f"Warning - Wind API error: {e}")
    return {}

def fetch_gistda_viirs():
    if not GISTDA_API_KEY or GISTDA_API_KEY == "DEMO_KEY":
        print("Notice: GISTDA_API_KEY not configured or using DEMO_KEY. Skipping GISTDA fetch.")
        return []

    url = "https://api-gateway.gistda.or.th/api/2.0/resources/features/viirs/1day"
    headers = {"API-Key": GISTDA_API_KEY, "Accept": "application/json"}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code != 200:
            print(f"Warning - GISTDA returned status {res.status_code}")
            return []
        features = res.json().get("features", [])
        sansai_hotspots = []
        for f in features:
            coords = f.get("geometry", {}).get("coordinates", [0, 0])
            if len(coords) >= 2:
                lon, lat = coords[0], coords[1]
                if (SANSAI_BOUNDS["min_lat"] <= lat <= SANSAI_BOUNDS["max_lat"] and
                    SANSAI_BOUNDS["min_lon"] <= lon <= SANSAI_BOUNDS["max_lon"]):
                    sansai_hotspots.append(f)
        return sansai_hotspots
    except Exception as e:
        print(f"Warning - GISTDA API error: {e}")
        return []

def send_line_alert(hotspots, wind):
    if not LINE_TOKEN:
        print("Notice: LINE_CHANNEL_ACCESS_TOKEN not configured. Skipping LINE alert.")
        return

# if not hotspots:
#     return

    wind_speed = wind.get("wind_speed_10m", 0)
    wind_dir = wind.get("wind_direction_10m", 0)
    temp = wind.get("temperature_2m", 0)
    
    msg = f"🔥 แจ้งเตือนจุดความร้อน GISTDA ใน อ.สันทราย!\n"
    msg += f"พบจุดความร้อนใหม่จำนวน {len(hotspots)} จุด\n"
    msg += f"🌡 อุณหภูมิ: {temp}°C | ลม: {wind_speed} กม./ชม. (ทิศ {wind_dir}°)\n\n"
    
    for idx, f in enumerate(hotspots[:3], 1):
        coords = f.get("geometry", {}).get("coordinates", [0, 0])
        lat, lon = coords[1], coords[0]
        msg += f"จุดที่ {idx}: พิกัด {lat:.5f}, {lon:.5f}\n"
        msg += f"📍 Google Maps: https://maps.google.com/?q={lat},{lon}\n"

    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    payload = {
        "messages": [{"type": "text", "text": msg.strip()}]
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            print("ส่งแจ้งเตือนเข้ากลุ่ม LINE สำเร็จ!")
        else:
            print(f"Warning - LINE API error: {res.status_code} {res.text}")
    except Exception as e:
        print(f"Warning - LINE request error: {e}")

if __name__ == "__main__":
    wind = fetch_wind_data()
    hotspots = fetch_gistda_viirs()
    
    output = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "wind_sansai": wind,
        "active_hotspots_count": len(hotspots),
        "active_hotspots": hotspots
    }
    
    with open("sansai_live_status.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        
    print(f"อัปเดตสำเร็จ: พบจุดความร้อนใน อ.สันทราย {len(hotspots)} จุด")
    
    # หากพบจุดความร้อน ให้ส่งแจ้งเตือนเข้า LINE
    if len(hotspots) > 0:
        send_line_alert(hotspots, wind)

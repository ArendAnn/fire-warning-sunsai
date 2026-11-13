import os
import json
import requests
from datetime import datetime

# 1. ดึง API Key จาก GitHub Secrets
GISTDA_API_KEY = os.environ.get("GISTDA_API_KEY")

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
    res = requests.get(url, params=params, timeout=15)
    return res.json().get("current", {})

def fetch_gistda_viirs():
    url = "https://api-gateway.gistda.or.th/api/2.0/resources/features/viirs/1day"
    headers = {"API-Key": GISTDA_API_KEY, "Accept": "application/json"}
    res = requests.get(url, headers=headers, timeout=20)
    if res.status_code != 200:
        return []
    features = res.json().get("features", [])
    sansai_hotspots = []
    for f in features:
        coords = f.get("geometry", {}).get("coordinates", [0, 0])
        lon, lat = coords[0], coords[1]
        if (SANSAI_BOUNDS["min_lat"] <= lat <= SANSAI_BOUNDS["max_lat"] and
            SANSAI_BOUNDS["min_lon"] <= lon <= SANSAI_BOUNDS["max_lon"]):
            sansai_hotspots.append(f)
    return sansai_hotspots

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

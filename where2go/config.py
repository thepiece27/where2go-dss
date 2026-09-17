from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Path(os.getenv("WHERE2GO_CATALOG", str(ROOT / "data/catalog.sqlite")))
OSRM_URL = os.getenv("OSRM_URL", "http://127.0.0.1:5001").rstrip("/")
CRITERIA = ("preference_match", "drive_time", "data_confidence")
GAMMA = 1.2
CANDIDATE_LIMIT = 40
SNAP_LIMIT_METERS = 300
DURATIONS = {"museum": 60, "historic": 45, "attraction": 60,
             "viewpoint": 30, "park": 60, "beach": 90, "temple": 45,
             "gallery": 45, "zoo": 90, "theme_park": 120}
CATEGORY_TEXT = {
    "museum": "bảo tàng văn hóa lịch sử museum culture history",
    "historic": "di tích lịch sử văn hóa historic history culture",
    "attraction": "tham quan du lịch văn hóa attraction culture",
    "viewpoint": "ngắm cảnh thiên nhiên viewpoint nature",
    "park": "công viên thiên nhiên thư giãn park nature",
    "beach": "biển bãi biển thiên nhiên beach nature",
    "temple": "chùa đền tâm linh văn hóa lịch sử temple culture history",
    "gallery": "nghệ thuật triển lãm văn hóa gallery art culture",
    "zoo": "động vật thiên nhiên gia đình zoo nature family",
    "theme_park": "vui chơi gia đình theme park family",
}

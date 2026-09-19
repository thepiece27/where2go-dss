"""Geographic and thematic policy for the Da Nang / Hoi An campaign."""
from functools import lru_cache
import json
import re

from shapely.geometry import Point, shape

from where2go.config import ROOT
from where2go.ranking import normalize
from .taxonomy import canonical_category

SCOPE_PATH = ROOT / "data/curation/danang_hoian_scope.geojson"
SCOPE_ID = "danang_hoian"
EXCLUDED = {"temple", "cafe", "restaurant", "food_street", "performance_venue"}
TOPICS = {
    "coast": ("bãi biển bãi tắm", "beach bay", "ghềnh đá mũi biển", "sunrise viewpoint"),
    "parks": ("công viên vườn tượng", "park playground", "quảng trường đường dạo", "garden waterfront promenade"),
    "entertainment": ("khu vui chơi khu du lịch", "theme park water park", "vườn thú thủy cung", "zoo aquarium tourist attraction"),
    "nature": ("thác suối hồ hang động", "waterfall cave lake", "núi đèo điểm ngắm cảnh", "viewpoint hiking trail campground"),
    "culture": ("bảo tàng di tích nhà cổ", "museum historic house", "làng nghề phòng trưng bày", "craft village art gallery"),
    "urban": ("cầu tham quan phố đi bộ", "bridge pedestrian street", "phố cổ chợ truyền thống chợ đêm", "old town night market"),
}


@lru_cache(maxsize=1)
def regions():
    data = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    return [(f["properties"], shape(f["geometry"])) for f in data["features"]]


@lru_cache(maxsize=100000)
def region_for(latitude, longitude):
    if latitude is None or longitude is None:
        return None
    point = Point(longitude, latitude)
    for props, geometry in regions():
        if geometry.covers(point):
            return props
    return None


def requires_boat(poi):
    region = region_for(poi.get("latitude"), poi.get("longitude"))
    return bool(region and region.get("requires_boat"))


def exclusion_reason(name, raw_category=""):
    name, raw = normalize(name), normalize(raw_category)
    worship = r"\b(chua|pagoda|temple|shrine|monastery|church|mosque|nha tho|thanh that|tinh xa|tu vien|dinh lang|mieu|den tho|place of worship)\b"
    if re.search(worship, name + " " + raw):
        return "place_of_worship"
    if re.search(r"\b(coffee|cafe|ca phe|restaurant|nha hang|spa|massage|pub|bar|hotel|resort|travel agency|tour operator|homestay|parking|bathroom|public bath|department|government office|association|organization|housing development|disco|night club|beach club|gun club|video arcade|shopping mall|supplier)\b", raw):
        return "excluded_service"
    if re.search(r"\b(bai do xe|bai giu xe|ban quan li|ban quan ly|nha ve sinh|dich vu tam nuoc ngot)\b", name):
        return "excluded_infrastructure"
    if canonical_category(raw_category, name) in EXCLUDED:
        return "excluded_category"
    return None


def matches_scope(poi, scope="", tourism_only=False):
    if scope and not region_for(poi.get("latitude"), poi.get("longitude")):
        return False
    if tourism_only and (poi.get("category") in EXCLUDED or exclusion_reason(poi.get("name", ""), poi.get("google_category_raw", ""))):
        return False
    return True

"""Canonical categories and experience tags used by every v2 component."""
from where2go.ranking import normalize


CATEGORIES = {
    "museum": "Bảo tàng",
    "historic": "Di tích",
    "attraction": "Điểm tham quan",
    "viewpoint": "Điểm ngắm cảnh",
    "park": "Công viên",
    "beach": "Bãi biển",
    "temple": "Đền, chùa và nơi thờ tự",
    "gallery": "Phòng trưng bày",
    "zoo": "Vườn thú và thủy cung",
    "theme_park": "Khu vui chơi lớn",
    "old_quarter": "Phố cổ và khu di sản đô thị",
    "craft_village": "Làng nghề",
    "market": "Chợ",
    "nature_area": "Khu thiên nhiên",
    "performance_venue": "Điểm biểu diễn văn hóa",
    "restaurant": "Nhà hàng",
    "cafe": "Cà phê",
    "food_street": "Khu ẩm thực",
    "water_park": "Công viên nước",
    "playground": "Sân chơi",
    "walking_street": "Phố đi bộ và đường dạo",
    "bridge": "Cầu tham quan",
    "cave": "Hang động",
    "waterfall": "Thác nước",
    "campground": "Khu cắm trại",
    "trailhead": "Điểm bắt đầu đường mòn",
}

FOOD_CATEGORIES = frozenset({"restaurant", "cafe", "food_street"})
ATTRACTION_CATEGORIES = frozenset(CATEGORIES) - FOOD_CATEGORIES

CATEGORY_TAGS = {
    "museum": ("lịch sử", "văn hóa", "nghệ thuật", "trong nhà"),
    "historic": ("lịch sử", "văn hóa", "chụp ảnh"),
    "attraction": ("văn hóa", "chụp ảnh"),
    "viewpoint": ("thiên nhiên", "ngoài trời", "chụp ảnh"),
    "park": ("thiên nhiên", "ngoài trời", "gia đình", "thư giãn"),
    "beach": ("thiên nhiên", "ngoài trời", "gia đình", "thư giãn"),
    "temple": ("tâm linh", "văn hóa", "lịch sử"),
    "gallery": ("nghệ thuật", "văn hóa", "trong nhà"),
    "zoo": ("thiên nhiên", "gia đình", "ngoài trời"),
    "theme_park": ("gia đình", "ngoài trời"),
    "old_quarter": ("lịch sử", "văn hóa", "ẩm thực", "chụp ảnh"),
    "craft_village": ("văn hóa", "nghệ thuật", "chụp ảnh"),
    "market": ("văn hóa", "ẩm thực", "mua sắm"),
    "nature_area": ("thiên nhiên", "ngoài trời", "chụp ảnh"),
    "performance_venue": ("văn hóa", "nghệ thuật", "trong nhà"),
    "restaurant": ("ẩm thực", "trong nhà"),
    "cafe": ("ẩm thực", "thư giãn"),
    "food_street": ("ẩm thực", "văn hóa"),
    "water_park": ("gia đình", "vui chơi", "ngoài trời"),
    "playground": ("gia đình", "vui chơi", "ngoài trời"),
    "walking_street": ("văn hóa", "đi bộ", "ngoài trời"),
    "bridge": ("chụp ảnh", "ngắm cảnh", "ngoài trời"),
    "cave": ("thiên nhiên", "khám phá"),
    "waterfall": ("thiên nhiên", "ngoài trời"),
    "campground": ("thiên nhiên", "cắm trại", "ngoài trời"),
    "trailhead": ("thiên nhiên", "đi bộ", "ngoài trời"),
}

_RULES = (
    ("water_park", ("water park", "cong vien nuoc")),
    ("playground", ("playground", "san choi")),
    ("walking_street", ("pedestrian", "walking street", "promenade", "pho di bo", "duong dao")),
    ("bridge", ("bridge", "cau rong", "cau tinh yeu", "cau vang", "cau song han", "cau tran thi ly")),
    ("cave", ("cave", "cavern", "hang dong")),
    ("waterfall", ("waterfall", "thac nuoc")),
    ("campground", ("campground", "camping", "cam trai")),
    ("trailhead", ("trailhead", "hiking area", "hiking trail", "duong mon")),
    ("cafe", ("cafe", "coffee shop", "coffee")),
    ("restaurant", ("restaurant", "food court", "fast food")),
    ("food_street", ("food street", "khu am thuc")),
    ("market", ("market", "marketplace", "cho ")),
    ("museum", ("museum", "bao tang")),
    ("gallery", ("gallery", "art gallery", "trien lam")),
    ("theme_park", ("theme park", "amusement park", "amusement center")),
    ("zoo", ("zoo", "aquarium")),
    ("temple", ("temple", "pagoda", "church", "place of worship", "shrine", "chua ", "nha tho", "tu vien")),
    ("beach", ("beach", "bai bien", "bai tam")),
    ("nature_area", ("nature reserve", "nature preserve", "national park", "mountain", "lake", "ho dong xanh", "ho hoa trung")),
    ("old_quarter", ("old quarter", "old town", "ancient town", "pho co")),
    ("craft_village", ("craft village", "lang nghe", "pottery village", "carpentry village", "lang gom", "lang moc")),
    ("park", ("park", "garden", "cong vien", "vuon tuong", "quang truong")),
    ("historic", ("historical", "heritage", "monument", "memorial", "ruins", "historic")),
    ("viewpoint", ("observation", "viewpoint", "scenic spot")),
    ("performance_venue", ("theater", "theatre", "performing", "opera")),
    ("attraction", ("tourist attraction", "visitor center")),
)


def canonical_category(raw, name=""):
    """Map a source label conservatively; return None instead of guessing."""
    if raw in CATEGORIES:
        return raw
    text = normalize(f"{raw or ''} {name or ''}")
    for category, phrases in _RULES:
        if any(normalize(phrase) in text for phrase in phrases):
            return category
    return None


def refine_category(existing, name="", description=""):
    """Refine broad source categories using explicit source text, conservatively."""
    text = normalize(f"{name or ''} {description or ''}")
    refinements = (
        ("food_street", ("pho am thuc", "food street")),
        ("old_quarter", ("pho co", "old quarter", "ancient town", "old town")),
        ("craft_village", ("lang nghe", "craft village", "pottery village", "carpentry village",
                           "lang gom", "lang moc", "lang da my nghe", "lang duc dong")),
        ("performance_venue", ("nha hat", "bieu dien", "theater", "theatre", "opera house",
                               "performance house")),
    )
    for category, phrases in refinements:
        if any(normalize(phrase) in text for phrase in phrases):
            return category
    return existing


def tags_for(category):
    return list(CATEGORY_TAGS.get(category, ()))

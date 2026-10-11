"""Versioned, conservative interpretation of declared travel needs."""

from dataclasses import dataclass
import re

from where2go.ranking import normalize
from .taxonomy import CATEGORIES, CATEGORY_TAGS


INTENT_POLICY_VERSION = "poi-intent-1.0"
EXPERIENCE_TOPICS = (
    "văn hóa",
    "lịch sử",
    "thiên nhiên",
    "gia đình",
    "ẩm thực",
    "thư giãn",
    "nghệ thuật",
    "chụp ảnh",
    "tâm linh",
    "biển",
)

CONCEPT_ALIASES = {
    "văn hóa": ("van hoa", "di san", "truyen thong"),
    "lịch sử": ("lich su", "di tich", "co xua"),
    "thiên nhiên": ("thien nhien", "ngoai troi", "cay xanh"),
    "gia đình": ("gia dinh", "tre em", "tre nho"),
    "ẩm thực": ("am thuc", "mon an", "an uong", "dac san"),
    "thư giãn": ("thu gian", "nghi ngoi", "yen tinh"),
    "nghệ thuật": ("nghe thuat", "trien lam", "my thuat"),
    "chụp ảnh": ("chup anh", "check in"),
    "tâm linh": ("tam linh", "chua", "den tho", "nha tho", "noi tho tu"),
    "biển": ("bien", "bai bien", "bai tam", "ngam canh bien", "ven bien"),
}

CONCEPT_CATEGORIES = {
    concept: frozenset(
        category
        for category, tags in CATEGORY_TAGS.items()
        if concept in tags
    )
    for concept in EXPERIENCE_TOPICS
}
CONCEPT_CATEGORIES["biển"] = frozenset({"beach"})
CONCEPT_CATEGORIES["tâm linh"] = frozenset({"temple"})

_CATEGORY_ALIASES = {
    "museum": ("bao tang",),
    "historic": ("di tich", "di san lich su"),
    "attraction": ("diem tham quan",),
    "viewpoint": ("diem ngam canh",),
    "park": ("cong vien",),
    "beach": ("bai bien", "bai tam"),
    "temple": ("tam linh", "chua", "den tho", "noi tho tu"),
    "gallery": ("phong trung bay", "bao tang nghe thuat"),
    "zoo": ("vuon thu", "thuy cung"),
    "theme_park": ("khu vui choi", "cong vien giai tri"),
    "old_quarter": ("pho co", "do thi co"),
    "craft_village": ("lang nghe",),
    "market": ("cho",),
    "nature_area": ("khu thien nhien", "khu bao ton"),
    "performance_venue": ("diem bieu dien", "nha hat"),
    "restaurant": ("nha hang",),
    "cafe": ("ca phe", "quan cafe"),
    "food_street": ("khu am thuc", "pho am thuc"),
    "water_park": ("cong vien nuoc",),
    "playground": ("san choi",),
    "walking_street": ("pho di bo", "duong dao"),
    "bridge": ("cau tham quan",),
    "cave": ("hang dong",),
    "waterfall": ("thac nuoc",),
    "campground": ("khu cam trai", "cam trai"),
    "trailhead": ("duong mon", "di bo duong dai"),
}
for _category, _label in CATEGORIES.items():
    _CATEGORY_ALIASES[_category] = tuple(
        dict.fromkeys((*_CATEGORY_ALIASES.get(_category, ()), normalize(_label)))
    )

_NEGATION = re.compile(r"^(?:khong\s+thich|khong\s+muon|khong|tranh|loai\s+tru)\s+")
_ONLY = re.compile(r"^(?:chi\s+tim|chi\s+muon|chi)\s+")


def _contains(text, phrase):
    return bool(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text))


def _concepts(text):
    return {
        concept
        for concept, aliases in CONCEPT_ALIASES.items()
        if any(_contains(text, alias) for alias in aliases)
    }


def _categories(text):
    return {
        category
        for category, aliases in _CATEGORY_ALIASES.items()
        if any(_contains(text, alias) for alias in aliases)
    }


@dataclass(frozen=True)
class InterpretedIntent:
    positive_concepts: tuple[str, ...]
    negative_concepts: tuple[str, ...]
    preferred_categories: tuple[str, ...]
    excluded_categories: tuple[str, ...]
    category_mode: str
    query_texts: tuple[str, ...]
    unmapped_texts: tuple[str, ...]
    unsupported_negations: tuple[str, ...]

    @property
    def has_positive_intent(self):
        return bool(self.positive_concepts or self.preferred_categories or self.query_texts)

    def as_dict(self):
        return {
            "policy_version": INTENT_POLICY_VERSION,
            "positive_concepts": list(self.positive_concepts),
            "negative_concepts": list(self.negative_concepts),
            "preferred_categories": list(self.preferred_categories),
            "excluded_categories": list(self.excluded_categories),
            "category_mode": self.category_mode,
            "query_texts": list(self.query_texts),
            "unmapped_texts": list(self.unmapped_texts),
            "unsupported_negations": list(self.unsupported_negations),
        }


def interpret_intent(
    interests=(),
    experience_topics=(),
    preferred_categories=(),
    excluded_categories=(),
    category_mode="preferred",
):
    """Interpret only supported phrases; never turn an unknown negation positive."""
    positive = set(experience_topics)
    negative = set()
    preferred = set(preferred_categories)
    excluded = set(excluded_categories)
    query_texts, unmapped, unsupported = [], [], []
    effective_mode = category_mode

    for raw in interests:
        text = normalize(raw).strip()
        if not text:
            continue
        negated = _NEGATION.match(text)
        exclusive = _ONLY.match(text)
        body = (
            _NEGATION.sub("", text, count=1)
            if negated
            else _ONLY.sub("", text, count=1)
            if exclusive
            else text
        )
        concepts, categories = _concepts(body), _categories(body)
        if negated:
            if not concepts and not categories:
                unsupported.append(raw)
                continue
            negative.update(concepts)
            excluded.update(categories)
            for concept in concepts:
                excluded.update(CONCEPT_CATEGORIES[concept])
            continue
        if exclusive:
            if not categories:
                unsupported.append(raw)
                continue
            effective_mode = "only"
        positive.update(concepts)
        preferred.update(categories)
        query_texts.append(body)
        if not concepts and not categories:
            unmapped.append(body)

    conflicts = preferred & excluded
    if conflicts:
        labels = ", ".join(CATEGORIES[value] for value in sorted(conflicts))
        raise ValueError(f"Loại hình vừa được chọn vừa bị loại trừ: {labels}")
    if positive & negative:
        labels = ", ".join(sorted(positive & negative))
        raise ValueError(f"Chủ đề vừa được chọn vừa bị phủ định: {labels}")
    if effective_mode == "only" and not preferred:
        raise ValueError("Chế độ chỉ tìm loại hình đã chọn cần ít nhất một loại hình")

    return InterpretedIntent(
        tuple(sorted(positive)),
        tuple(sorted(negative)),
        tuple(sorted(preferred)),
        tuple(sorted(excluded)),
        effective_mode,
        tuple(query_texts),
        tuple(unmapped),
        tuple(unsupported),
    )


def interpret_request(request):
    return interpret_intent(
        getattr(request, "interests", ()),
        getattr(request, "experience_topics", ()),
        getattr(request, "preferred_categories", ()),
        getattr(request, "excluded_categories", ()),
        getattr(request, "category_mode", "preferred"),
    )


def poi_concepts(poi):
    """Return concept evidence once, without counting default tags twice."""
    category = poi.get("category")
    source_text = normalize(
        " ".join(
            [
                poi.get("name", ""),
                *poi.get("aliases", []),
                poi.get("description", ""),
                *poi.get("tags", []),
            ]
        )
    )
    return {
        concept
        for concept, aliases in CONCEPT_ALIASES.items()
        if category in CONCEPT_CATEGORIES[concept]
        or any(_contains(source_text, alias) for alias in aliases)
    }

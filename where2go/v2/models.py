"""Validated public request models for API v2."""
from datetime import date, time
from typing import Literal
from pydantic import Field, model_validator

from where2go.models import Coordinate, StrictModel
from .taxonomy import ATTRACTION_CATEGORIES, CATEGORIES


CRITERIA = ("preference_match", "place_quality", "drive_time", "data_confidence")
DEFAULT_WEIGHTS = (0.40, 0.30, 0.20, 0.10)
DEFAULT_COMPARISONS = [DEFAULT_WEIGHTS[i] / DEFAULT_WEIGHTS[j] for i in range(4) for j in range(i + 1, 4)]


class AHPPreferences(StrictModel):
    criteria_order: list[str] = Field(default_factory=lambda: list(CRITERIA), min_length=4, max_length=4)
    comparisons: list[float] = Field(default_factory=lambda: DEFAULT_COMPARISONS.copy(), min_length=6, max_length=6)
    uncertainty: list[float] = Field(default_factory=lambda: [1.2] * 6, min_length=6, max_length=6)

    @model_validator(mode="after")
    def validate_judgments(self):
        if tuple(self.criteria_order) != CRITERIA:
            raise ValueError("criteria_order phải đúng hợp đồng API v2")
        if any(not 1 / 9 <= value <= 9 for value in self.comparisons):
            raise ValueError("Mỗi phán đoán AHP phải thuộc [1/9, 9]")
        if any(not 1 <= value <= 2 for value in self.uncertainty):
            raise ValueError("Mỗi hệ số bất định phải thuộc [1, 2]")
        from .ranking import ahp_weights
        ahp_weights(self.comparisons, self.uncertainty)
        return self


class ItineraryRequestV2(StrictModel):
    start: Coordinate
    date: date
    start_time: time = time(8)
    end_time: time = time(18)
    location: str = Field(default="", max_length=100)
    interests: list[str] = Field(default_factory=list, max_length=12)
    preferred_categories: list[str] = Field(default_factory=list, max_length=18)
    excluded_categories: list[str] = Field(default_factory=list, max_length=18)
    category_mode: Literal["preferred", "only"] = "preferred"
    pace: Literal["quick", "balanced", "relaxed"] = "balanced"
    include_meals: bool = True
    include_coffee_break: bool = False
    radius_km: float = Field(default=30, ge=1, le=80)
    required_poi_ids: list[str] = Field(default_factory=list, max_length=5)
    duration_overrides: dict[str, int] = Field(default_factory=dict, max_length=60)
    ahp: AHPPreferences = Field(default_factory=AHPPreferences)

    @model_validator(mode="after")
    def validate_request(self):
        if self.start_time.tzinfo or self.end_time.tzinfo or self.start_time >= self.end_time:
            raise ValueError("Khung giờ địa phương phải trong cùng ngày và giờ về sau giờ đi")
        if any(value.second or value.microsecond for value in (self.start_time, self.end_time)):
            raise ValueError("Thời gian chỉ hỗ trợ độ chính xác phút")
        supported = set(CATEGORIES)
        preferred, excluded = set(self.preferred_categories), set(self.excluded_categories)
        if (preferred | excluded) - supported:
            raise ValueError("Có category chưa được taxonomy v2 hỗ trợ")
        if preferred - set(ATTRACTION_CATEGORIES):
            raise ValueError("preferred_categories chỉ dành cho điểm tham quan; ăn/nghỉ có tùy chọn riêng")
        if preferred & excluded:
            raise ValueError("Một category không thể vừa ưu tiên vừa bị loại")
        if self.category_mode == "only" and not preferred:
            raise ValueError("Chế độ chuyên đề cần ít nhất một category")
        if len(set(self.required_poi_ids)) != len(self.required_poi_ids):
            raise ValueError("required_poi_ids bị lặp")
        if any(not 5 <= value <= 720 for value in self.duration_overrides.values()):
            raise ValueError("Thời lượng người dùng phải từ 5 đến 720 phút")
        if any(len(text) > 100 for text in self.interests):
            raise ValueError("Mỗi sở thích tối đa 100 ký tự")
        return self


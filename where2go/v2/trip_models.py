"""Consumer trip contracts; ranking policy stays on the server."""
from datetime import date, time
from typing import Annotated, Literal

from pydantic import Field, model_validator
from where2go.models import Coordinate, StrictModel
from .models import AHPPreferences
from .taxonomy import CATEGORIES


class TripContext(StrictModel):
    start: Coordinate
    date: date
    location: Literal["Hà Nội", "Đà Nẵng"]
    selected_poi_ids: list[str] = Field(default_factory=list, max_length=12)
    interests: list[Annotated[str, Field(max_length=100)]] = Field(default_factory=list, max_length=12)
    preferred_categories: list[str] = Field(default_factory=list, max_length=18)

    @property
    def ahp(self):
        return AHPPreferences()

    @model_validator(mode="after")
    def validate_context(self):
        if len(set(self.selected_poi_ids)) != len(self.selected_poi_ids):
            raise ValueError("Mỗi địa điểm chỉ được chọn một lần")
        if any(not ident or len(ident) > 200 for ident in self.selected_poi_ids):
            raise ValueError("Mã địa điểm không hợp lệ")
        if set(self.preferred_categories) - set(CATEGORIES):
            raise ValueError("Loại hình địa điểm chưa được hỗ trợ")
        return self


class TripSuggestionRequest(TripContext):
    start_time: time = time(8)
    end_time: time = time(18)
    must_visit_poi_ids: list[str] = Field(default_factory=list, max_length=12)
    duration_overrides: dict[str, Annotated[int, Field(strict=True, ge=5, le=720)]] = Field(default_factory=dict, max_length=12)
    manual_order: list[str] | None = Field(default=None, max_length=12)
    include_meals: bool = True
    include_coffee_break: bool = False
    auto_add: bool = False
    try_other_windows: bool = False

    @model_validator(mode="after")
    def validate_trip(self):
        selected = set(self.selected_poi_ids)
        if not set(self.must_visit_poi_ids) <= selected or len(set(self.must_visit_poi_ids)) != len(self.must_visit_poi_ids):
            raise ValueError("Những nơi nhất định phải ghé phải nằm trong danh sách đã chọn và không được lặp")
        if not set(self.duration_overrides) <= selected:
            raise ValueError("Chỉ sửa thời lượng của địa điểm đã chọn")
        if self.manual_order is not None and (set(self.manual_order) != selected or len(self.manual_order) != len(selected)):
            raise ValueError("Thứ tự chỉnh tay phải chứa đúng mỗi địa điểm đã chọn một lần")
        if self.manual_order is not None and self.auto_add:
            raise ValueError("Tắt tự bổ sung khi dùng thứ tự chỉnh tay")
        if self.start_time.tzinfo or self.end_time.tzinfo or self.start_time >= self.end_time:
            raise ValueError("Giờ đi và giờ về phải trong cùng ngày; giờ về sau giờ đi")
        if any(t.second or t.microsecond for t in (self.start_time, self.end_time)):
            raise ValueError("Giờ đi và giờ về chỉ hỗ trợ độ chính xác phút")
        return self

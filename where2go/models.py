from datetime import date, time
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Coordinate(StrictModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Pairwise(StrictModel):
    preference_over_drive_time: float = Field(default=1, ge=1/9, le=9)
    preference_over_data_confidence: float = Field(default=1, ge=1/9, le=9)
    drive_time_over_data_confidence: float = Field(default=1, ge=1/9, le=9)


class ItineraryRequest(StrictModel):
    start: Coordinate
    date: date
    start_time: time = time(8)
    end_time: time = time(18)
    interests: list[str] = Field(default_factory=list, max_length=12)
    categories: list[str] = Field(default_factory=list, max_length=12)
    location: str = Field(default="", max_length=100)
    query: str = Field(default="", max_length=200)
    radius_km: float = Field(default=30, ge=1, le=80)
    pairwise_preferences: Pairwise = Field(default_factory=Pairwise)

    @model_validator(mode="after")
    def validate_schedule(self):
        from .ranking import weights
        from .config import DURATIONS
        if self.start_time.tzinfo or self.end_time.tzinfo:
            raise ValueError("Use local Asia/Ho_Chi_Minh time without an offset")
        if self.start_time >= self.end_time:
            raise ValueError("Giờ kết thúc phải sau giờ bắt đầu trong cùng ngày")
        if self.start_time.second or self.end_time.second or self.start_time.microsecond or self.end_time.microsecond:
            raise ValueError("Chỉ hỗ trợ độ chính xác phút")
        if any(len(s) > 100 for s in self.interests):
            raise ValueError("Sở thích quá dài")
        if set(self.categories) - set(DURATIONS):
            raise ValueError("Loại hình không được hỗ trợ")
        weights(self.pairwise_preferences)
        return self

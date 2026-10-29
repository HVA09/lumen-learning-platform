from datetime import datetime

from pydantic import BaseModel


class AchievementOut(BaseModel):
    key: str
    title_ar: str
    description_ar: str
    unlocked_at: datetime | None  # None يعني معرّف لكن لسه ما تحقق


class LeaderboardEntryOut(BaseModel):
    user_id: int
    display_name: str
    score: int
    rank: int
    is_me: bool = False


class MyStatsOut(BaseModel):
    score: int
    rank: int | None  # None لو ما عنده نقاط بعد
    streak_days: int
    studied_today: bool

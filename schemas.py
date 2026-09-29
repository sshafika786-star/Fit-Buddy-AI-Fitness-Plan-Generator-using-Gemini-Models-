from typing import Literal

from pydantic import BaseModel, Field, field_validator


Intensity = Literal["low", "medium", "high"]


class UserInput(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    user_id: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    age: int = Field(ge=13, le=100)
    weight_kg: float | None = Field(default=None, gt=0, le=300)
    goal: str = Field(min_length=2, max_length=100)
    intensity: Intensity

    @field_validator("username", "goal")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value


class FeedbackRequest(BaseModel):
    user_id: str = Field(min_length=2, max_length=64)
    feedback: str = Field(min_length=3, max_length=2000)


class Exercise(BaseModel):
    name: str
    sets: str
    reps_or_duration: str
    rest: str


class WorkoutDay(BaseModel):
    day: str
    focus: str
    warm_up: str
    main_workout: list[Exercise]
    cooldown: str
    notes: str


class WorkoutPlan(BaseModel):
    title: str
    goal: str
    intensity: str
    safety_note: str
    days: list[WorkoutDay]


class NutritionTip(BaseModel):
    title: str
    tip: str
    recovery: str
    safety_note: str

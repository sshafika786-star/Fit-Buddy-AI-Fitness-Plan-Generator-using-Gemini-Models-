import json

from ..config import get_settings
from .gemini_client import GeminiServiceError, generate_json
from ..schemas import UserInput, WorkoutPlan


def _demo_plan(data: UserInput) -> WorkoutPlan:
    focus = {
        "weight loss": "Full-body movement",
        "muscle gain": "Strength fundamentals",
        "flexibility": "Mobility and flexibility",
        "general wellness": "Balanced fitness",
    }.get(data.goal.lower(), "Balanced fitness")

    days = []
    focuses = [
        focus, "Lower body", "Cardio and mobility", "Upper body",
        "Core and balance", "Light full body", "Recovery and flexibility",
    ]
    for i, day_focus in enumerate(focuses, 1):
        days.append({
            "day": f"Day {i}",
            "focus": day_focus,
            "warm_up": "5–10 minutes of easy walking and gentle mobility.",
            "main_workout": [
                {"name": "Bodyweight squat", "sets": "2", "reps_or_duration": "8–12 reps",
                 "rest": "60–90 seconds"},
                {"name": "Wall push-up", "sets": "2", "reps_or_duration": "8–12 reps",
                 "rest": "60–90 seconds"},
            ],
            "cooldown": "5 minutes of comfortable stretching and easy breathing.",
            "notes": "Keep the effort comfortable and stop if you feel pain, dizziness, or unusual symptoms.",
        })
    return WorkoutPlan(
        title="FitBuddy 7-Day Starter Plan",
        goal=data.goal,
        intensity=data.intensity,
        safety_note="This is general wellness information, not medical care. Adjust activity to your ability.",
        days=days,
    )


def generate_workout_gemini(data: UserInput) -> WorkoutPlan:
    settings = get_settings()
    if settings.demo_mode or not settings.gemini_api_key:
        return _demo_plan(data)

    prompt = f"""
You are FitBuddy, a cautious fitness-planning assistant.
Create a structured 7-day general fitness plan for:
Name: {data.username}
Age: {data.age}
Weight (kg, optional): {data.weight_kg}
Goal: {data.goal}
Preferred intensity: {data.intensity}

Return ONLY valid JSON matching the supplied schema.
Include exactly 7 days. Each day must have a focus, a 5–10 minute warm-up,
a practical main workout with exercise name, sets, reps/duration and rest,
a cooldown, and a short note.

Safety rules:
- This is general wellness guidance, not diagnosis or medical treatment.
- Never recommend dangerous challenges, extreme exercise, fasting, dehydration,
  or unprescribed supplements.
- Do not prescribe calorie targets or restrictive eating.
- If age is under 18, do not frame the plan around changing body weight or body size;
  focus on enjoyable movement, skill, strength, mobility, rest, and gradual progression.
- Keep high-intensity work conservative and include recovery.
- Tell the user to stop if they feel pain, dizziness, faintness, chest pain, or other
  concerning symptoms and to seek appropriate adult/medical guidance when needed.
"""
    try:
        raw = generate_json(settings.workout_model, prompt, WorkoutPlan.model_json_schema())
        return WorkoutPlan.model_validate(json.loads(raw))
    except GeminiServiceError:
        return _demo_plan(data)
    except Exception as exc:
        raise GeminiServiceError(f"Gemini returned invalid workout JSON: {exc}") from exc

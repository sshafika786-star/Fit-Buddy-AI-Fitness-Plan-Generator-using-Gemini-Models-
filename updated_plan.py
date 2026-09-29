import json

from ..config import get_settings
from .gemini_client import GeminiServiceError, generate_json
from ..schemas import UserInput, WorkoutPlan


def update_workout_plan(original_plan: str, feedback: str, user: UserInput) -> WorkoutPlan:
    settings = get_settings()

    if settings.demo_mode or not settings.gemini_api_key:
        plan = WorkoutPlan.model_validate_json(original_plan)
        plan.safety_note = (
            "Demo update applied. Keep activity comfortable and adjust with qualified guidance when needed."
        )
        if feedback.strip():
            plan.days[0].notes = f"Updated based on feedback: {feedback.strip()[:300]}"
        return plan

    prompt = f"""
Update this FitBuddy 7-day workout plan using the user's feedback.

User:
Age: {user.age}
Goal: {user.goal}
Intensity: {user.intensity}

Original plan:
{original_plan}

Feedback:
{feedback}

Return ONLY valid JSON matching the supplied schema.
Preserve the 7-day structure but make reasonable changes that directly address the feedback.

Safety rules:
- Never create dangerous challenges, extreme exercise, fasting, dehydration, or supplement dosing.
- Do not prescribe calorie targets or restrictive eating.
- If age is under 18, do not frame changes around weight loss or body size.
- Keep recovery and gradual progression.
"""
    try:
        raw = generate_json(settings.workout_model, prompt, WorkoutPlan.model_json_schema())
        return WorkoutPlan.model_validate(json.loads(raw))
    except GeminiServiceError:
        plan = WorkoutPlan.model_validate_json(original_plan)
        plan.safety_note = (
            "Demo update applied because the Gemini service is unavailable. Keep activity comfortable and adjust with qualified guidance when needed."
        )
        if feedback.strip():
            plan.days[0].notes = f"Updated based on feedback: {feedback.strip()[:300]}"
        return plan
    except Exception as exc:
        raise GeminiServiceError(f"Gemini returned invalid updated-plan JSON: {exc}") from exc

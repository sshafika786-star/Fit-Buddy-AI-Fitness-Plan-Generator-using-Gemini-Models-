import json

from ..config import get_settings
from .gemini_client import GeminiServiceError, generate_json
from ..schemas import NutritionTip, UserInput


def _demo_tip(data: UserInput) -> NutritionTip:
    return NutritionTip(
        title="Everyday nutrition & recovery",
        tip="Build regular meals around a variety of foods, include a protein source, and drink water regularly.",
        recovery="Prioritize sleep, rest days, and gentle movement between harder sessions.",
        safety_note="Avoid restrictive diets or supplements unless advised by a qualified professional.",
    )


def generate_nutrition_tip_with_flash(data: UserInput) -> NutritionTip:
    settings = get_settings()
    if settings.demo_mode or not settings.gemini_api_key:
        return _demo_tip(data)

    prompt = f"""
You are FitBuddy's nutrition and recovery assistant.
User age: {data.age}
Goal: {data.goal}
Workout intensity: {data.intensity}

Return ONLY valid JSON matching the supplied schema.
Give one concise, practical nutrition/recovery suggestion that supports healthy,
regular eating and recovery.

Safety rules:
- Do not provide calorie targets, crash diets, fasting instructions, dehydration advice,
  or supplement dosing.
- If age is under 18, avoid weight-loss/body-composition advice and focus on balanced
  meals, hydration, sleep, and enjoyable activity.
- Do not claim to diagnose or treat medical conditions.
"""
    try:
        raw = generate_json(settings.nutrition_model, prompt, NutritionTip.model_json_schema())
        return NutritionTip.model_validate(json.loads(raw))
    except GeminiServiceError:
        return _demo_tip(data)
    except Exception as exc:
        raise GeminiServiceError(f"Gemini returned invalid nutrition JSON: {exc}") from exc

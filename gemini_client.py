from functools import lru_cache

from ..config import get_settings


class GeminiServiceError(RuntimeError):
    """Raised when the Gemini service cannot generate a response."""


@lru_cache
def get_client():
    settings = get_settings()
    if not settings.gemini_api_key:
        return None

    # Lazy import keeps local/demo tests usable even before dependencies are installed.
    from google import genai
    return genai.Client(api_key=settings.gemini_api_key)


def generate_json(model: str, prompt: str, response_schema: dict) -> str:
    settings = get_settings()
    if settings.demo_mode:
        raise GeminiServiceError("DEMO_MODE is enabled; use the demo generator path.")

    client = get_client()
    if client is None:
        raise GeminiServiceError(
            "Gemini API key is not configured. Add GEMINI_API_KEY to your .env file."
        )

    try:
        from google.genai import types

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=response_schema,
                temperature=0.6,
            ),
        )
        if not response.text:
            raise GeminiServiceError("Gemini returned an empty response.")
        return response.text
    except GeminiServiceError:
        raise
    except Exception as exc:
        raise GeminiServiceError(f"Gemini request failed: {exc}") from exc

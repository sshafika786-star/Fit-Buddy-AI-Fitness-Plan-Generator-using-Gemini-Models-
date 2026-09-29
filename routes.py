import json
import secrets

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import User, get_db
from .ai.gemini_client import GeminiServiceError
from .ai.gemini_flash_generator import generate_nutrition_tip_with_flash
from .ai.gemini_generator import generate_workout_gemini
from .schemas import FeedbackRequest, UserInput
from .ai.updated_plan import update_workout_plan

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "template"))


def _serialize_plan(plan) -> str:
    return json.dumps(plan.model_dump(), ensure_ascii=False, indent=2)


def _find_user(db: Session, user_id: str) -> User | None:
    return db.scalar(select(User).where(User.user_id == user_id))


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"error": None},
    )


@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout(
    request: Request,
    username: str = Form(...),
    user_id: str = Form(...),
    age: int = Form(...),
    weight_kg: float | None = Form(None),
    goal: str = Form(...),
    intensity: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        data = UserInput(
            username=username,
            user_id=user_id,
            age=age,
            weight_kg=weight_kg,
            goal=goal,
            intensity=intensity.lower(),
        )
        plan = generate_workout_gemini(data)
        tip = generate_nutrition_tip_with_flash(data)

        user = _find_user(db, data.user_id)
        if user is None:
            user = User(user_id=data.user_id)
            db.add(user)

        user.username = data.username
        user.age = data.age
        user.weight_kg = data.weight_kg
        user.goal = data.goal
        user.intensity = data.intensity
        user.original_plan = _serialize_plan(plan)
        user.updated_plan = None
        user.feedback = None
        user.nutrition_tip = json.dumps(tip.model_dump(), ensure_ascii=False, indent=2)
        db.commit()
        db.refresh(user)

        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "user": user,
                "plan": plan,
                "tip": tip,
                "message": "Your 7-day plan has been generated.",
                "error": None,
            },
        )
    except (ValueError, GeminiServiceError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"error": str(exc)},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback(
    request: Request,
    user_id: str = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db),
):
    user = _find_user(db, user_id)
    if user is None or not user.original_plan:
        raise HTTPException(status_code=404, detail="User or original plan not found.")

    try:
        data = UserInput(
            username=user.username,
            user_id=user.user_id,
            age=user.age,
            weight_kg=user.weight_kg,
            goal=user.goal,
            intensity=user.intensity,
        )
        updated = update_workout_plan(user.original_plan, feedback, data)
        tip = generate_nutrition_tip_with_flash(data)

        user.updated_plan = _serialize_plan(updated)
        user.feedback = feedback.strip()
        user.nutrition_tip = json.dumps(tip.model_dump(), ensure_ascii=False, indent=2)
        db.commit()
        db.refresh(user)

        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "user": user,
                "plan": updated,
                "tip": tip,
                "message": "Your plan was updated using your feedback.",
                "error": None,
            },
        )
    except (ValueError, GeminiServiceError) as exc:
        original = json.loads(user.original_plan)
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "user": user,
                "plan": original,
                "tip": json.loads(user.nutrition_tip or "{}"),
                "message": None,
                "error": str(exc),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request, token: str = "", db: Session = Depends(get_db)):
    settings = get_settings()
    if not secrets.compare_digest(token, settings.admin_token):
        raise HTTPException(status_code=403, detail="Invalid admin token.")
    users = list(db.scalars(select(User).order_by(User.created_at.desc())))
    return templates.TemplateResponse(
        request=request,
        name="all_users.html",
        context={"users": users, "admin_token": token},
    )


@router.get("/api/health")
def health():
    return {"status": "ok", "service": "FitBuddy"}


@router.post("/api/generate-workout")
def api_generate_workout(payload: UserInput, db: Session = Depends(get_db)):
    try:
        plan = generate_workout_gemini(payload)
        tip = generate_nutrition_tip_with_flash(payload)
    except GeminiServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    user = _find_user(db, payload.user_id)
    if user is None:
        user = User(user_id=payload.user_id)
        db.add(user)
    user.username = payload.username
    user.age = payload.age
    user.weight_kg = payload.weight_kg
    user.goal = payload.goal
    user.intensity = payload.intensity
    user.original_plan = _serialize_plan(plan)
    user.updated_plan = None
    user.feedback = None
    user.nutrition_tip = json.dumps(tip.model_dump(), ensure_ascii=False)
    db.commit()

    return {"user": payload.model_dump(), "workout_plan": plan.model_dump(), "nutrition_tip": tip.model_dump()}


@router.post("/api/submit-feedback")
def api_submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)):
    user = _find_user(db, payload.user_id)
    if user is None or not user.original_plan:
        raise HTTPException(status_code=404, detail="User or original plan not found.")

    data = UserInput(
        username=user.username,
        user_id=user.user_id,
        age=user.age,
        weight_kg=user.weight_kg,
        goal=user.goal,
        intensity=user.intensity,
    )
    try:
        updated = update_workout_plan(user.original_plan, payload.feedback, data)
        tip = generate_nutrition_tip_with_flash(data)
    except GeminiServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    user.updated_plan = _serialize_plan(updated)
    user.feedback = payload.feedback.strip()
    user.nutrition_tip = json.dumps(tip.model_dump(), ensure_ascii=False)
    db.commit()

    return {"updated_plan": updated.model_dump(), "nutrition_tip": tip.model_dump()}

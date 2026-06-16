import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import create_access_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import RegistrationControl, User, UserRole
from ..schemas import LoginRequest, Token, UserPublic, UserRegister


router = APIRouter(tags=["Authentication"])


@router.post("/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    control = db.get(RegistrationControl, 1)
    if control and not control.is_open and payload.role != UserRole.meal_manager:
        raise HTTPException(status_code=403, detail=control.message or "Registration is currently closed")
    if control and control.max_registrations and payload.role != UserRole.meal_manager:
        current_registrations = db.scalar(select(func.count()).select_from(User).where(User.role != UserRole.meal_manager)) or 0
        if current_registrations >= control.max_registrations:
            raise HTTPException(status_code=403, detail="Registration limit has been reached")
    if payload.role == UserRole.meal_manager:
        expected_code = os.getenv("MANAGER_REGISTRATION_CODE")
        provided_code = (payload.manager_registration_code or "").strip()
        if not expected_code or provided_code != expected_code.strip():
            raise HTTPException(status_code=403, detail="A valid manager registration code is required")
    existing = db.scalar(select(User).where(User.whatsapp_number == payload.whatsapp_number))
    if existing:
        raise HTTPException(status_code=409, detail="An account already uses this WhatsApp number")
    user = User(
        member_type=payload.member_type,
        full_name=payload.full_name.strip(),
        room_number=(payload.room_number or "").strip(),
        address_or_identity_note=payload.address_or_identity_note.strip() if payload.address_or_identity_note else None,
        whatsapp_number=payload.whatsapp_number,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_meal_member=payload.role == UserRole.meal_manager,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return Token(access_token=create_access_token(user.id), user=user)


@router.post("/auth/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.whatsapp_number == payload.whatsapp_number))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect WhatsApp number or password")
    return Token(access_token=create_access_token(user.id), user=user)


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/auth/me", response_model=UserPublic, include_in_schema=False)
def auth_me(current_user: User = Depends(get_current_user)):
    return current_user

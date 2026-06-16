from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_meal_manager
from ..database import get_db
from ..models import Notice, TodayMenu, User, WeeklyNotice
from .hostel import active_cycle
from ..schemas import MenuPublic, MenuUpdate
from ..utils.time import dhaka_today


router = APIRouter(tags=["Menu & notices"])


def serialize_menu(db: Session, menu: TodayMenu | None) -> MenuPublic:
    notice = db.scalar(select(WeeklyNotice).order_by(WeeklyNotice.created_at.desc()).limit(1))
    if notice is None:
        notice = db.scalar(select(Notice).order_by(Notice.created_at.desc()).limit(1))
    return MenuPublic(
        date=dhaka_today(),
        lunch_menu=menu.lunch_menu if menu else "Menu has not been published yet.",
        dinner_menu=menu.dinner_menu if menu else "Menu has not been published yet.",
        notice=notice.message if notice else None,
        updated_at=menu.updated_at if menu else None,
    )


@router.get("/menu/today", response_model=MenuPublic)
def get_today_menu(db: Session = Depends(get_db)):
    menu = db.scalar(select(TodayMenu).where(TodayMenu.date == dhaka_today()))
    return serialize_menu(db, menu)


@router.post("/manager/menu", response_model=MenuPublic)
def update_today_menu(
    payload: MenuUpdate,
    manager: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    today = dhaka_today()
    menu = db.scalar(select(TodayMenu).where(TodayMenu.date == today))
    if menu is None:
        menu = TodayMenu(date=today, updated_by=manager.id)
        db.add(menu)
    menu.lunch_menu = payload.lunch_menu.strip()
    menu.dinner_menu = payload.dinner_menu.strip()
    menu.updated_by = manager.id
    if payload.notice and payload.notice.strip():
        cycle = active_cycle(db)
        db.add(WeeklyNotice(
            message=payload.notice.strip(), created_by=manager.id,
            cycle_id=cycle.id if cycle else None,
        ))
    db.commit()
    db.refresh(menu)
    return serialize_menu(db, menu)


@router.get("/menu", response_model=MenuPublic, include_in_schema=False)
def get_menu_alias(db: Session = Depends(get_db)):
    return get_today_menu(db)


@router.post("/menu", response_model=MenuPublic, include_in_schema=False)
def update_menu_alias(
    payload: MenuUpdate,
    manager: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    return update_today_menu(payload, manager, db)

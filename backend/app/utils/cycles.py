from datetime import timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..models import (
    Attendance,
    BazarExpense,
    CycleStatus,
    MealPost,
    Payment,
    User,
    UserRole,
    WeeklyCycle,
    WeeklyNotice,
    WeeklySkip,
)
from .time import dhaka_today


def create_cycle(db: Session, assigned_manager: User, initiated_by: int) -> WeeklyCycle:
    previous = db.scalar(select(WeeklyCycle).where(WeeklyCycle.status == CycleStatus.active))
    if previous and previous.manager_id != assigned_manager.id:
        previous_manager = db.get(User, previous.manager_id)
        if previous_manager:
            previous_manager.role = UserRole.student
    assigned_manager.role = UserRole.meal_manager
    assigned_manager.is_meal_member = True
    db.execute(update(WeeklyCycle).where(WeeklyCycle.status == CycleStatus.active).values(status=CycleStatus.closed))
    for model in (MealPost, Attendance, Payment, WeeklyNotice, WeeklySkip, BazarExpense):
        db.execute(delete(model))
    today = dhaka_today()
    cycle = WeeklyCycle(
        start_date=today,
        end_date=today + timedelta(days=6),
        manager_id=assigned_manager.id,
        status=CycleStatus.active,
    )
    db.add(cycle)
    db.flush()
    for user in db.scalars(select(User).where(User.is_meal_member.is_(True))).all():
        db.add(Payment(user_id=user.id, cycle_id=cycle.id, updated_by=initiated_by))
    db.commit()
    return cycle


def rotate_expired_cycle(db: Session) -> WeeklyCycle | None:
    cycle = db.scalar(select(WeeklyCycle).where(WeeklyCycle.status == CycleStatus.active))
    if cycle is None or cycle.end_date >= dhaka_today():
        return None
    members = db.scalars(select(User).where(User.is_meal_member.is_(True)).order_by(User.id)).all()
    if not members:
        return None
    next_manager = next((user for user in members if user.id > cycle.manager_id), members[0])
    return create_cycle(db, next_manager, cycle.manager_id)

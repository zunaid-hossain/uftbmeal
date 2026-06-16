from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..models import Attendance, BazarExpense, MealPost, Payment, WeeklyNotice, WeeklySkip


def cleanup_old_meal_posts(db: Session) -> tuple[int, datetime]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    result = db.execute(delete(MealPost).where(MealPost.created_at < cutoff))
    db.commit()
    return result.rowcount or 0, cutoff


def cleanup_weekly_data(db: Session) -> tuple[int, datetime]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    deleted = 0
    for model in (MealPost, WeeklyNotice, WeeklySkip, BazarExpense):
        result = db.execute(delete(model).where(model.created_at < cutoff))
        deleted += result.rowcount or 0
    result = db.execute(delete(Payment).where(Payment.updated_at < cutoff))
    deleted += result.rowcount or 0
    attendance_cutoff = cutoff.date()
    result = db.execute(delete(Attendance).where(Attendance.date < attendance_cutoff))
    deleted += result.rowcount or 0
    db.commit()
    return deleted, cutoff

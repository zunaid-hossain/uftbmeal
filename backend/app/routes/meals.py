from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user
from ..database import get_db
from ..models import MealPost, MealStatus, MealType, User
from ..schemas import MealCreate, MealPublic
from ..utils.time import dhaka_today


router = APIRouter(prefix="/meals", tags=["Meals"])


def meal_query():
    return select(MealPost).options(selectinload(MealPost.seller)).order_by(MealPost.date, MealPost.created_at.desc())


@router.post("", response_model=MealPublic, status_code=status.HTTP_201_CREATED)
def create_meal(payload: MealCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_meal_member:
        raise HTTPException(status_code=403, detail="Only active meal members can sell meals")
    meal = MealPost(seller_id=current_user.id, **payload.model_dump())
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return db.scalar(meal_query().where(MealPost.id == meal.id))


@router.get("", response_model=list[MealPublic])
def list_meals(
    meal_type: MealType | None = None,
    status_filter: MealStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    query = meal_query()
    if meal_type:
        query = query.where(MealPost.meal_type == meal_type)
    if status_filter:
        query = query.where(MealPost.status == status_filter)
    return db.scalars(query).all()


@router.get("/today", response_model=list[MealPublic])
def today_meals(db: Session = Depends(get_db)):
    query = meal_query().where(MealPost.date == dhaka_today(), MealPost.status == MealStatus.available)
    return db.scalars(query).all()


@router.patch("/{meal_id}/mark-sold", response_model=MealPublic)
def mark_sold(meal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    meal = db.get(MealPost, meal_id)
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal post not found")
    if meal.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the seller can mark this meal as sold")
    meal.status = MealStatus.sold
    db.commit()
    return db.scalar(meal_query().where(MealPost.id == meal.id))


@router.patch("/{meal_id}/sold", response_model=MealPublic, include_in_schema=False)
def mark_sold_alias(meal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return mark_sold(meal_id, current_user, db)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(meal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    meal = db.get(MealPost, meal_id)
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal post not found")
    if meal.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the seller can delete this meal post")
    db.delete(meal)
    db.commit()

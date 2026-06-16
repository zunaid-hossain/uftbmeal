from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_user, require_meal_manager
from ..database import get_db
from ..models import (
    Attendance,
    BazarExpense,
    BroadcastNotification,
    CycleStatus,
    MealMember,
    MealPost,
    MealStatus,
    Notice,
    NotificationRecipient,
    Payment,
    PaymentStatus,
    PushSubscription,
    RegistrationControl,
    TodayMenu,
    User,
    UserRole,
    WeeklyCycle,
    WeeklyNotice,
    WeeklySkip,
)
from ..schemas import (
    AttendancePublic,
    AttendanceDashboardRow,
    BazarExpenseCreate,
    BazarExpensePublic,
    BazarSummary,
    BulkReminderResult,
    CycleCreate,
    CyclePublic,
    DashboardStats,
    MealProvidedNotificationCreate,
    MemberPublic,
    MemberUpdate,
    NotificationPublic,
    ManagerUserPublic,
    ManagerUserUpdate,
    PaymentPublic,
    PaymentUpdate,
    PushPublicConfig,
    PushSubscriptionCreate,
    RegistrationControlPublic,
    RegistrationControlUpdate,
    RemainingAttendance,
    RemainingMember,
    WeeklySkipCreate,
    WeeklyActiveUpdate,
    WeeklyStatusPublic,
)
from ..utils.time import dhaka_today
from ..utils.cycles import create_cycle
from ..utils.push import push_config, push_enabled, send_push_to_all, send_push_to_users


router = APIRouter(tags=["Hostel meal system"])


def active_cycle(db: Session) -> WeeklyCycle | None:
    return db.scalar(
        select(WeeklyCycle)
        .options(selectinload(WeeklyCycle.manager))
        .where(WeeklyCycle.status == CycleStatus.active)
        .order_by(WeeklyCycle.start_date.desc())
    )


def current_payment(db: Session, user_id: int, cycle_id: int | None) -> Payment | None:
    query = select(Payment).where(Payment.user_id == user_id)
    query = query.where(Payment.cycle_id == cycle_id) if cycle_id else query.where(Payment.cycle_id.is_(None))
    return db.scalar(query)


def current_skip(db: Session, user_id: int, cycle_id: int | None) -> WeeklySkip | None:
    query = select(WeeklySkip).where(WeeklySkip.user_id == user_id)
    query = query.where(WeeklySkip.cycle_id == cycle_id) if cycle_id else query.where(WeeklySkip.cycle_id.is_(None))
    return db.scalar(query)


def skipped_user_ids(db: Session, cycle_id: int | None) -> set[int]:
    query = select(WeeklySkip.user_id)
    query = query.where(WeeklySkip.cycle_id == cycle_id) if cycle_id else query.where(WeeklySkip.cycle_id.is_(None))
    return set(db.scalars(query).all())


def unpaid_active_members(db: Session) -> list[User]:
    cycle = active_cycle(db)
    cycle_id = cycle.id if cycle else None
    skip_ids = skipped_user_ids(db, cycle_id)
    users = db.scalars(
        select(User)
        .where(User.is_meal_member.is_(True))
        .order_by(User.room_number, User.full_name)
    ).all()
    unpaid = []
    for user in users:
        if user.id in skip_ids:
            continue
        payment = current_payment(db, user.id, cycle_id)
        if payment is None or payment.status == PaymentStatus.unpaid:
            unpaid.append(user)
    return unpaid


def registration_payload(db: Session, control: RegistrationControl) -> RegistrationControlPublic:
    current = db.scalar(select(func.count()).select_from(User).where(User.role != UserRole.meal_manager)) or 0
    remaining = max(control.max_registrations - current, 0) if control.max_registrations else None
    return RegistrationControlPublic(
        is_open=control.is_open,
        message=control.message,
        max_registrations=control.max_registrations,
        current_registrations=current,
        remaining_slots=remaining,
        updated_at=control.updated_at,
    )


@router.get("/members", response_model=list[MemberPublic])
def members(db: Session = Depends(get_db)):
    cycle = active_cycle(db)
    skip_ids = skipped_user_ids(db, cycle.id if cycle else None)
    users = db.scalars(select(User).where(User.is_meal_member.is_(True)).order_by(User.room_number)).all()
    return [
        MemberPublic(
            id=user.id,
            member_type=user.member_type,
            full_name=user.full_name,
            room_number=user.room_number,
            address_or_identity_note=user.address_or_identity_note,
            is_meal_member=True,
            payment_status=(current_payment(db, user.id, cycle.id if cycle else None) or Payment(status=PaymentStatus.unpaid)).status,
            skipped_this_week=user.id in skip_ids,
        )
        for user in users
    ]


@router.get("/manager/users", response_model=list[ManagerUserPublic])
def manager_users(_: User = Depends(require_meal_manager), db: Session = Depends(get_db)):
    cycle = active_cycle(db)
    skip_ids = skipped_user_ids(db, cycle.id if cycle else None)
    result = []
    for user in db.scalars(select(User).order_by(User.room_number)).all():
        payment = current_payment(db, user.id, cycle.id if cycle else None)
        result.append(ManagerUserPublic(
            id=user.id, member_type=user.member_type, full_name=user.full_name, room_number=user.room_number,
            address_or_identity_note=user.address_or_identity_note,
            is_meal_member=user.is_meal_member,
            payment_status=payment.status if payment else PaymentStatus.unpaid,
            skipped_this_week=user.id in skip_ids,
            whatsapp_number=user.whatsapp_number,
            role=user.role,
        ))
    return result


@router.patch("/manager/users/{user_id}", response_model=ManagerUserPublic)
def update_user_registration(
    user_id: int,
    payload: ManagerUserUpdate,
    manager: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    duplicate = db.scalar(select(User).where(User.whatsapp_number == payload.whatsapp_number, User.id != user.id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Another account already uses this WhatsApp number")
    user.member_type = payload.member_type
    user.full_name = payload.full_name.strip()
    user.room_number = (payload.room_number or "").strip()
    user.address_or_identity_note = payload.address_or_identity_note.strip() if payload.address_or_identity_note else None
    user.whatsapp_number = payload.whatsapp_number
    user.role = payload.role
    if payload.role == UserRole.meal_manager:
        user.is_meal_member = True
    db.commit()
    cycle = active_cycle(db)
    payment = current_payment(db, user.id, cycle.id if cycle else None)
    skip = current_skip(db, user.id, cycle.id if cycle else None)
    return ManagerUserPublic(
        id=user.id, member_type=user.member_type, full_name=user.full_name, room_number=user.room_number,
        address_or_identity_note=user.address_or_identity_note,
        is_meal_member=user.is_meal_member,
        payment_status=payment.status if payment else PaymentStatus.unpaid,
        skipped_this_week=skip is not None,
        whatsapp_number=user.whatsapp_number,
        role=user.role,
    )


@router.delete("/manager/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_account(
    user_id: int,
    manager: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == manager.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own manager account while logged in")

    db.execute(delete(MealPost).where(MealPost.seller_id == user.id))
    db.execute(delete(Attendance).where(Attendance.user_id == user.id))
    db.execute(delete(Payment).where(Payment.user_id == user.id))
    db.execute(delete(WeeklySkip).where(WeeklySkip.user_id == user.id))
    db.execute(delete(PushSubscription).where(PushSubscription.user_id == user.id))
    db.execute(delete(NotificationRecipient).where(NotificationRecipient.user_id == user.id))
    db.execute(update(BazarExpense).where(BazarExpense.created_by == user.id).values(created_by=manager.id))
    db.execute(update(Payment).where(Payment.updated_by == user.id).values(updated_by=manager.id))
    db.execute(delete(MealMember).where(MealMember.user_id == user.id))
    db.execute(update(MealMember).where(MealMember.added_by == user.id).values(added_by=manager.id))
    db.execute(update(WeeklyCycle).where(WeeklyCycle.manager_id == user.id).values(manager_id=manager.id))
    db.execute(update(TodayMenu).where(TodayMenu.updated_by == user.id).values(updated_by=manager.id))
    db.execute(update(Notice).where(Notice.created_by == user.id).values(created_by=manager.id))
    db.execute(update(WeeklyNotice).where(WeeklyNotice.created_by == user.id).values(created_by=manager.id))
    db.execute(update(BroadcastNotification).where(BroadcastNotification.created_by == user.id).values(created_by=None))
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/manager/users/{user_id}/week-active", response_model=ManagerUserPublic)
def update_week_active(
    user_id: int,
    payload: WeeklyActiveUpdate,
    manager: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_meal_member:
        raise HTTPException(status_code=400, detail="Only meal members can be active for a weekly meal cycle")
    cycle = active_cycle(db)
    skip = current_skip(db, user.id, cycle.id if cycle else None)
    if payload.active and skip:
        db.delete(skip)
        skip = None
    if not payload.active:
        if skip is None:
            skip = WeeklySkip(user_id=user.id, cycle_id=cycle.id if cycle else None)
            db.add(skip)
        skip.reason = payload.reason.strip() if payload.reason else "Marked inactive by meal manager"
    db.commit()
    payment = current_payment(db, user.id, cycle.id if cycle else None)
    return ManagerUserPublic(
        id=user.id, member_type=user.member_type, full_name=user.full_name, room_number=user.room_number,
        address_or_identity_note=user.address_or_identity_note,
        is_meal_member=user.is_meal_member,
        payment_status=payment.status if payment else PaymentStatus.unpaid,
        skipped_this_week=not payload.active,
        whatsapp_number=user.whatsapp_number,
        role=user.role,
    )


@router.patch("/members/{user_id}", response_model=MemberPublic)
def update_member(
    user_id: int,
    payload: MemberUpdate,
    manager: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_meal_member = payload.is_meal_member
    membership = db.scalar(select(MealMember).where(MealMember.user_id == user.id))
    if membership is None:
        membership = MealMember(user_id=user.id, added_by=manager.id, is_active=payload.is_meal_member)
        db.add(membership)
    else:
        membership.is_active = payload.is_meal_member
    cycle = active_cycle(db)
    payment = current_payment(db, user.id, cycle.id if cycle else None)
    skip = current_skip(db, user.id, cycle.id if cycle else None)
    if payload.is_meal_member and payment is None:
        payment = Payment(user_id=user.id, cycle_id=cycle.id if cycle else None, updated_by=manager.id)
        db.add(payment)
    if not payload.is_meal_member and skip is not None:
        db.delete(skip)
        skip = None
    db.commit()
    return MemberPublic(
        id=user.id, member_type=user.member_type, full_name=user.full_name, room_number=user.room_number,
        address_or_identity_note=user.address_or_identity_note,
        is_meal_member=user.is_meal_member, payment_status=payment.status if payment else PaymentStatus.unpaid,
        skipped_this_week=skip is not None,
    )


@router.get("/payments", response_model=list[PaymentPublic])
def payments(db: Session = Depends(get_db)):
    cycle = active_cycle(db)
    skip_ids = skipped_user_ids(db, cycle.id if cycle else None)
    result = []
    for user in db.scalars(select(User).where(User.is_meal_member.is_(True)).order_by(User.room_number)).all():
        payment = current_payment(db, user.id, cycle.id if cycle else None)
        result.append(PaymentPublic(
            user_id=user.id, member_type=user.member_type, full_name=user.full_name, room_number=user.room_number,
            address_or_identity_note=user.address_or_identity_note,
            status=payment.status if payment else PaymentStatus.unpaid,
            skipped_this_week=user.id in skip_ids,
        ))
    return result


@router.patch("/payments/{user_id}", response_model=PaymentPublic)
def update_payment(
    user_id: int,
    payload: PaymentUpdate,
    manager: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None or not user.is_meal_member:
        raise HTTPException(status_code=404, detail="Meal member not found")
    cycle = active_cycle(db)
    payment = current_payment(db, user.id, cycle.id if cycle else None)
    skip = current_skip(db, user.id, cycle.id if cycle else None)
    if payment is None:
        payment = Payment(user_id=user.id, cycle_id=cycle.id if cycle else None, updated_by=manager.id)
        db.add(payment)
    payment.status = payload.status
    payment.updated_by = manager.id
    db.commit()
    return PaymentPublic(
        user_id=user.id, member_type=user.member_type, full_name=user.full_name,
        room_number=user.room_number, address_or_identity_note=user.address_or_identity_note,
        status=payment.status,
        skipped_this_week=skip is not None,
    )


def check_attendance(meal: str, current_user: User, db: Session) -> Attendance:
    if not current_user.is_meal_member:
        raise HTTPException(status_code=403, detail="Only meal members can record attendance")
    cycle = active_cycle(db)
    if current_skip(db, current_user.id, cycle.id if cycle else None):
        raise HTTPException(status_code=403, detail="You skipped this week. Join this week again before recording attendance")
    today = dhaka_today()
    attendance = db.scalar(select(Attendance).where(Attendance.user_id == current_user.id, Attendance.date == today))
    if attendance is None:
        attendance = Attendance(user_id=current_user.id, date=today)
        db.add(attendance)
    field = f"{meal}_checked"
    if getattr(attendance, field):
        raise HTTPException(status_code=409, detail=f"{meal.title()} attendance is already checked")
    setattr(attendance, field, True)
    db.commit()
    db.refresh(attendance)
    return attendance


@router.post("/attendance/lunch", response_model=AttendancePublic)
def lunch_attendance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return check_attendance("lunch", current_user, db)


@router.post("/attendance/dinner", response_model=AttendancePublic)
def dinner_attendance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return check_attendance("dinner", current_user, db)


@router.get("/attendance/today", response_model=AttendancePublic)
def today_attendance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cycle = active_cycle(db)
    skipped = current_skip(db, current_user.id, cycle.id if cycle else None) is not None
    attendance = db.scalar(select(Attendance).where(Attendance.user_id == current_user.id, Attendance.date == dhaka_today()))
    if attendance:
        return AttendancePublic(
            date=attendance.date,
            lunch_checked=attendance.lunch_checked,
            dinner_checked=attendance.dinner_checked,
            skipped_this_week=skipped,
        )
    return AttendancePublic(date=dhaka_today(), lunch_checked=False, dinner_checked=False, skipped_this_week=skipped)


@router.get("/me/week-status", response_model=WeeklyStatusPublic)
def week_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cycle = active_cycle(db)
    skip = current_skip(db, current_user.id, cycle.id if cycle else None)
    return WeeklyStatusPublic(cycle=cycle, skipped_this_week=skip is not None, skip_reason=skip.reason if skip else None)


@router.post("/me/skip-week", response_model=WeeklyStatusPublic, status_code=status.HTTP_201_CREATED)
def skip_week(
    payload: WeeklySkipCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_meal_member:
        raise HTTPException(status_code=403, detail="Only meal members can skip a weekly meal cycle")
    cycle = active_cycle(db)
    skip = current_skip(db, current_user.id, cycle.id if cycle else None)
    if skip is None:
        skip = WeeklySkip(user_id=current_user.id, cycle_id=cycle.id if cycle else None)
        db.add(skip)
    skip.reason = payload.reason.strip() if payload.reason else None
    db.commit()
    db.refresh(skip)
    return WeeklyStatusPublic(cycle=cycle, skipped_this_week=True, skip_reason=skip.reason)


@router.delete("/me/skip-week", response_model=WeeklyStatusPublic)
def unskip_week(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cycle = active_cycle(db)
    skip = current_skip(db, current_user.id, cycle.id if cycle else None)
    if skip:
        db.delete(skip)
        db.commit()
    return WeeklyStatusPublic(cycle=cycle, skipped_this_week=False, skip_reason=None)


@router.get("/attendance/remaining", response_model=RemainingAttendance)
def remaining_attendance(_: User = Depends(require_meal_manager), db: Session = Depends(get_db)):
    cycle = active_cycle(db)
    skip_ids = skipped_user_ids(db, cycle.id if cycle else None)
    members = db.scalars(select(User).where(User.is_meal_member.is_(True)).order_by(User.room_number)).all()
    records = {
        row.user_id: row for row in db.scalars(select(Attendance).where(Attendance.date == dhaka_today())).all()
    }
    def remaining(meal: str):
        return [
            RemainingMember(
                user_id=user.id, member_type=user.member_type, full_name=user.full_name,
                room_number=user.room_number, address_or_identity_note=user.address_or_identity_note,
                skipped_this_week=False,
            )
            for user in members if user.id not in skip_ids and (not records.get(user.id) or not getattr(records[user.id], f"{meal}_checked"))
        ]
    return RemainingAttendance(lunch=remaining("lunch"), dinner=remaining("dinner"))


@router.get("/attendance/dashboard", response_model=list[AttendanceDashboardRow])
def attendance_dashboard(_: User = Depends(require_meal_manager), db: Session = Depends(get_db)):
    cycle = active_cycle(db)
    skip_ids = skipped_user_ids(db, cycle.id if cycle else None)
    records = {
        row.user_id: row for row in db.scalars(select(Attendance).where(Attendance.date == dhaka_today())).all()
    }
    rows = []
    for user in db.scalars(select(User).where(User.is_meal_member.is_(True)).order_by(User.room_number, User.full_name)).all():
        record = records.get(user.id)
        rows.append(AttendanceDashboardRow(
            user_id=user.id,
            member_type=user.member_type,
            full_name=user.full_name,
            room_number=user.room_number,
            address_or_identity_note=user.address_or_identity_note,
            lunch_checked=bool(record and record.lunch_checked),
            dinner_checked=bool(record and record.dinner_checked),
            skipped_this_week=user.id in skip_ids,
        ))
    return rows


@router.get("/cycle", response_model=CyclePublic | None)
def get_cycle(db: Session = Depends(get_db)):
    return active_cycle(db)


@router.post("/manager/start-new-cycle", response_model=CyclePublic)
def start_new_cycle(
    payload: CycleCreate,
    manager: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    assigned_manager = db.get(User, payload.manager_id or manager.id)
    if assigned_manager is None:
        raise HTTPException(status_code=404, detail="Selected manager not found")
    cycle = create_cycle(db, assigned_manager, manager.id)
    return db.scalar(select(WeeklyCycle).options(selectinload(WeeklyCycle.manager)).where(WeeklyCycle.id == cycle.id))


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(_: User = Depends(require_meal_manager), db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(User).where(User.is_meal_member.is_(True))) or 0
    cycle = active_cycle(db)
    skip_ids = skipped_user_ids(db, cycle.id if cycle else None)
    paid_query = select(func.count()).select_from(Payment).where(
        Payment.status == PaymentStatus.paid,
        Payment.cycle_id == (cycle.id if cycle else None),
    )
    if skip_ids:
        paid_query = paid_query.where(Payment.user_id.not_in(skip_ids))
    paid = db.scalar(paid_query) or 0
    attendance = db.scalars(select(Attendance).where(Attendance.date == dhaka_today())).all()
    return DashboardStats(
        total_members=total,
        paid_members=paid,
        unpaid_members=max(total - len(skip_ids) - paid, 0),
        skipped_members=len(skip_ids),
        lunch_attendance=sum(1 for row in attendance if row.lunch_checked),
        dinner_attendance=sum(1 for row in attendance if row.dinner_checked),
        available_meals=db.scalar(select(func.count()).select_from(MealPost).where(MealPost.status == MealStatus.available)) or 0,
        sold_meals=db.scalar(select(func.count()).select_from(MealPost).where(MealPost.status == MealStatus.sold)) or 0,
    )


def registration_control(db: Session) -> RegistrationControl:
    control = db.get(RegistrationControl, 1)
    if control is None:
        control = RegistrationControl(id=1)
        db.add(control)
        db.commit()
        db.refresh(control)
    return control


@router.get("/registration", response_model=RegistrationControlPublic)
def get_registration_control(db: Session = Depends(get_db)):
    return registration_payload(db, registration_control(db))


@router.patch("/manager/registration", response_model=RegistrationControlPublic)
def update_registration_control(
    payload: RegistrationControlUpdate,
    manager: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    control = registration_control(db)
    control.is_open = payload.is_open
    control.message = payload.message.strip()
    control.max_registrations = payload.max_registrations
    control.updated_by = manager.id
    db.commit()
    db.refresh(control)
    return registration_payload(db, control)


@router.get("/manager/bazar", response_model=BazarSummary)
def bazar_expenses(_: User = Depends(require_meal_manager), db: Session = Depends(get_db)):
    cycle = active_cycle(db)
    rows = db.scalars(
        select(BazarExpense)
        .options(selectinload(BazarExpense.creator))
        .where(BazarExpense.cycle_id == (cycle.id if cycle else None))
        .order_by(BazarExpense.date.desc(), BazarExpense.id.desc())
    ).all()
    return BazarSummary(
        cycle=cycle,
        total_amount=sum(row.amount for row in rows),
        expense_count=len(rows),
        rows=rows,
    )


@router.post("/manager/bazar", response_model=BazarExpensePublic, status_code=status.HTTP_201_CREATED)
def create_bazar_expense(
    payload: BazarExpenseCreate,
    manager: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    cycle = active_cycle(db)
    expense = BazarExpense(
        cycle_id=cycle.id if cycle else None,
        date=payload.date,
        item_name=payload.item_name.strip(),
        amount=payload.amount,
        note=payload.note.strip() if payload.note else None,
        created_by=manager.id,
    )
    db.add(expense)
    db.commit()
    return db.scalar(
        select(BazarExpense)
        .options(selectinload(BazarExpense.creator))
        .where(BazarExpense.id == expense.id)
    )


@router.delete("/manager/bazar/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bazar_expense(
    expense_id: int,
    _: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    expense = db.get(BazarExpense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Bazar expense not found")
    db.delete(expense)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/notifications", response_model=list[NotificationPublic])
def notifications(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 25))
    has_recipients = select(NotificationRecipient.id).where(
        NotificationRecipient.notification_id == BroadcastNotification.id
    ).exists()
    targeted_to_user = select(NotificationRecipient.id).where(
        NotificationRecipient.notification_id == BroadcastNotification.id,
        NotificationRecipient.user_id == current_user.id,
    ).exists()
    return db.scalars(
        select(BroadcastNotification)
        .options(selectinload(BroadcastNotification.creator))
        .where(or_(~has_recipients, targeted_to_user))
        .order_by(BroadcastNotification.created_at.desc())
        .limit(limit)
    ).all()


@router.post("/manager/notifications/unpaid-payment-reminder", response_model=BulkReminderResult, status_code=status.HTTP_201_CREATED)
def notify_unpaid_payment_members(
    manager: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    recipients = unpaid_active_members(db)
    if not recipients:
        return BulkReminderResult(notified=0, push_sent=0, notification=None)

    notification = BroadcastNotification(
        title="Payment reminder",
        message="Your UFTB Boys Hostel weekly meal payment is still unpaid. Please complete it soon or contact the meal manager.",
        created_by=manager.id,
    )
    db.add(notification)
    db.flush()
    db.add_all([
        NotificationRecipient(notification_id=notification.id, user_id=user.id)
        for user in recipients
    ])
    db.commit()
    user_ids = [user.id for user in recipients]
    push_sent = send_push_to_users(db, user_ids, notification.title, notification.message, "/payments")
    saved_notification = db.scalar(
        select(BroadcastNotification)
        .options(selectinload(BroadcastNotification.creator))
        .where(BroadcastNotification.id == notification.id)
    )
    return BulkReminderResult(
        notified=len(user_ids),
        push_sent=push_sent,
        notification=saved_notification,
    )


@router.post("/notifications/meal-provided", response_model=NotificationPublic, status_code=status.HTTP_201_CREATED)
def announce_meal_provided(
    payload: MealProvidedNotificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.meal_manager and not current_user.is_meal_member:
        raise HTTPException(status_code=403, detail="Only meal managers and meal members can notify everyone")
    message = (payload.message or "").strip()
    if not message:
        message = f"{payload.meal_type.value} meal has been provided. Please collect your meal and tick attendance if you ate."
    notification = BroadcastNotification(
        title=f"{payload.meal_type.value} meal provided",
        message=message,
        meal_type=payload.meal_type,
        created_by=current_user.id,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    send_push_to_all(db, notification.title, notification.message, "/attendance")
    return db.scalar(
        select(BroadcastNotification)
        .options(selectinload(BroadcastNotification.creator))
        .where(BroadcastNotification.id == notification.id)
    )


@router.get("/push/public-key", response_model=PushPublicConfig)
def push_public_key():
    public_key, _, _ = push_config()
    return PushPublicConfig(enabled=push_enabled(), public_key=public_key)


@router.post("/push/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def subscribe_push(
    payload: PushSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subscription = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint))
    if subscription is None:
        subscription = PushSubscription(endpoint=payload.endpoint)
        db.add(subscription)
    subscription.user_id = current_user.id
    subscription.p256dh = payload.keys.p256dh
    subscription.auth = payload.keys.auth
    subscription.user_agent = payload.user_agent
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/push/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe_push(
    endpoint: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.execute(delete(PushSubscription).where(
        PushSubscription.endpoint == endpoint,
        PushSubscription.user_id == current_user.id,
    ))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

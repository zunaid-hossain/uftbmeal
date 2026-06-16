import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

os.environ["DATABASE_URL"] = "sqlite:///./test_uftb_meals.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["MANAGER_REGISTRATION_CODE"] = "manager-test-code"

from app.database import Base, SessionLocal, engine
from app.models import MealPost, MealStatus, MealType, MemberType, PaymentStatus, User, UserRole
from app.routes.auth import login, register
from app.routes.hostel import (
    announce_meal_provided,
    bazar_expenses,
    create_bazar_expense,
    dashboard_stats,
    delete_bazar_expense,
    delete_user_account,
    get_registration_control,
    lunch_attendance,
    notify_unpaid_payment_members,
    notifications,
    payments,
    remaining_attendance,
    skip_week,
    start_new_cycle,
    unskip_week,
    update_week_active,
    update_member,
    update_payment,
    update_registration_control,
    update_user_registration,
)
from app.routes.meals import create_meal, delete_meal, mark_sold
from app.routes.menu import update_today_menu
from app.schemas import BazarExpenseCreate, CycleCreate, LoginRequest, ManagerUserUpdate, MealCreate, MealProvidedNotificationCreate, MemberUpdate, MenuUpdate, PaymentUpdate, RegistrationControlUpdate, UserRegister, WeeklyActiveUpdate, WeeklySkipCreate
from app.utils.cleanup import cleanup_old_meal_posts


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def new_user(db, number, role=UserRole.student):
    result = register(UserRegister(
        full_name="Test Student",
        member_type=MemberType.hostel_resident,
        room_number="B-204",
        whatsapp_number=number,
        password="password123",
        role=role,
        manager_registration_code="manager-test-code" if role == UserRole.meal_manager else None,
    ), db)
    return db.get(User, result.user.id)


def test_registration_login_meal_and_ownership():
    with SessionLocal() as db:
        seller = new_user(db, "8801712345678")
        buyer = new_user(db, "8801812345678")
        seller.is_meal_member = True
        db.commit()
        authenticated = login(LoginRequest(whatsapp_number=seller.whatsapp_number, password="password123"), db)
        assert authenticated.access_token

        meal = create_meal(MealCreate(
            meal_type=MealType.lunch,
            date=datetime.now().date(),
            price=70,
            note="Token included",
        ), seller, db)
        with pytest.raises(HTTPException) as error:
            delete_meal(meal.id, buyer, db)
        assert error.value.status_code == 403
        sold = mark_sold(meal.id, seller, db)
        assert sold.status == MealStatus.sold


def test_manager_menu_and_cleanup():
    with SessionLocal() as db:
        student = new_user(db, "8801912345678")
        manager = new_user(db, "8801612345678", UserRole.meal_manager)
        menu = update_today_menu(MenuUpdate(
            lunch_menu="Rice, fish curry and dal",
            dinner_menu="Khichuri and egg",
            notice="Dinner at 8 PM",
        ), manager, db)
        assert menu.notice == "Dinner at 8 PM"

        db.add(MealPost(
            seller_id=student.id,
            meal_type=MealType.lunch,
            date=datetime.now().date(),
            price=50,
            status=MealStatus.available,
            created_at=datetime.now(timezone.utc) - timedelta(days=8),
        ))
        db.commit()
        deleted, _ = cleanup_old_meal_posts(db)
        assert deleted == 1


def test_membership_payment_attendance_and_cycle():
    with SessionLocal() as db:
        manager = new_user(db, "8801412345678", UserRole.meal_manager)
        student = new_user(db, "8801512345678")
        cycle = start_new_cycle(CycleCreate(), manager, db)
        assert cycle.manager.id == manager.id

        member = update_member(student.id, MemberUpdate(is_meal_member=True), manager, db)
        assert member.is_meal_member is True
        payment = update_payment(student.id, PaymentUpdate(status=PaymentStatus.paid), manager, db)
        assert payment.status == PaymentStatus.paid
        attendance = lunch_attendance(student, db)
        assert attendance.lunch_checked is True
        stats = dashboard_stats(manager, db)
        assert stats.total_members == 2
        assert stats.paid_members == 1
        assert stats.lunch_attendance == 1


def test_outside_member_and_registration_controls():
    with SessionLocal() as db:
        manager = new_user(db, "8801312345678", UserRole.meal_manager)
        control = update_registration_control(RegistrationControlUpdate(is_open=False, message="Registration paused"), manager, db)
        assert control.is_open is False
        with pytest.raises(HTTPException):
            register(UserRegister(
                member_type=MemberType.hostel_resident,
                full_name="Closed Student",
                room_number="101",
                whatsapp_number="8801555555555",
                password="password123",
            ), db)
        limited = update_registration_control(RegistrationControlUpdate(is_open=True, message="Registration open", max_registrations=1), manager, db)
        assert limited.max_registrations == 1
        assert limited.current_registrations == 0
        outside = register(UserRegister(
            member_type=MemberType.outside_member,
            full_name="Outside Member",
            address_or_identity_note="Nearby mess student",
            whatsapp_number="8801566666666",
            password="password123",
        ), db).user
        assert get_registration_control(db).remaining_slots == 0
        with pytest.raises(HTTPException) as error:
            register(UserRegister(
                member_type=MemberType.hostel_resident,
                full_name="Limit Student",
                room_number="102",
                whatsapp_number="8801577777777",
                password="password123",
            ), db)
        assert error.value.status_code == 403
        assert outside.room_number == ""
        updated = update_user_registration(outside.id, ManagerUserUpdate(
            member_type=MemberType.outside_member,
            full_name="Updated Outside",
            room_number=None,
            address_or_identity_note="Local guardian verified",
            whatsapp_number="8801566666666",
            role=UserRole.student,
        ), manager, db)
        assert updated.address_or_identity_note == "Local guardian verified"
        assert updated.room_number == ""


def test_notifications_and_manager_account_delete():
    with SessionLocal() as db:
        manager = new_user(db, "8801377777777", UserRole.meal_manager)
        student = new_user(db, "8801477777777")
        update_member(student.id, MemberUpdate(is_meal_member=True), manager, db)

        notification = announce_meal_provided(
            MealProvidedNotificationCreate(meal_type=MealType.lunch),
            student,
            db,
        )
        assert notification.title == "Lunch meal provided"
        assert notification.creator.id == student.id
        assert notifications(10, manager, db)[0].id == notification.id

        response = delete_user_account(student.id, manager, db)
        assert response.status_code == 204
        assert db.get(User, student.id) is None
        with pytest.raises(HTTPException) as error:
            delete_user_account(manager.id, manager, db)
        assert error.value.status_code == 400


def test_manager_can_notify_only_unpaid_members():
    with SessionLocal() as db:
        manager = new_user(db, "8801377777778", UserRole.meal_manager)
        paid_student = new_user(db, "8801477777778")
        unpaid_student = new_user(db, "8801577777778")
        start_new_cycle(CycleCreate(), manager, db)
        update_member(paid_student.id, MemberUpdate(is_meal_member=True), manager, db)
        update_member(unpaid_student.id, MemberUpdate(is_meal_member=True), manager, db)
        update_payment(manager.id, PaymentUpdate(status=PaymentStatus.paid), manager, db)
        update_payment(paid_student.id, PaymentUpdate(status=PaymentStatus.paid), manager, db)

        result = notify_unpaid_payment_members(manager, db)

        assert result.notified == 1
        assert result.notification.title == "Payment reminder"
        assert notifications(10, unpaid_student, db)[0].id == result.notification.id
        assert all(item.id != result.notification.id for item in notifications(10, paid_student, db))
        assert all(item.id != result.notification.id for item in notifications(10, manager, db))


def test_member_can_skip_and_rejoin_weekly_cycle():
    with SessionLocal() as db:
        manager = new_user(db, "8801388888888", UserRole.meal_manager)
        student = new_user(db, "8801488888888")
        start_new_cycle(CycleCreate(), manager, db)
        update_member(student.id, MemberUpdate(is_meal_member=True), manager, db)

        status = skip_week(WeeklySkipCreate(reason="Going home"), student, db)
        assert status.skipped_this_week is True
        assert status.skip_reason == "Going home"
        assert next(item for item in payments(db) if item.user_id == student.id).skipped_this_week is True
        assert all(person.user_id != student.id for person in remaining_attendance(manager, db).lunch)
        stats = dashboard_stats(manager, db)
        assert stats.skipped_members == 1
        assert stats.unpaid_members == 1
        with pytest.raises(HTTPException) as error:
            lunch_attendance(student, db)
        assert error.value.status_code == 403

        manager_update = update_week_active(student.id, WeeklyActiveUpdate(active=True), manager, db)
        assert manager_update.skipped_this_week is False
        manager_update = update_week_active(student.id, WeeklyActiveUpdate(active=False), manager, db)
        assert manager_update.skipped_this_week is True

        joined = unskip_week(student, db)
        assert joined.skipped_this_week is False
        assert lunch_attendance(student, db).lunch_checked is True


def test_manager_bazar_sheet():
    with SessionLocal() as db:
        manager = new_user(db, "8801399999999", UserRole.meal_manager)
        cycle = start_new_cycle(CycleCreate(), manager, db)
        expense = create_bazar_expense(BazarExpenseCreate(
            date=cycle.start_date,
            item_name="Rice",
            amount=1500,
            note="25 kg",
        ), manager, db)
        assert expense.item_name == "Rice"
        summary = bazar_expenses(manager, db)
        assert summary.expense_count == 1
        assert summary.total_amount == 1500
        response = delete_bazar_expense(expense.id, manager, db)
        assert response.status_code == 204
        assert bazar_expenses(manager, db).expense_count == 0

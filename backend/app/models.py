import enum
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    student = "student"
    meal_manager = "meal_manager"


class MemberType(str, enum.Enum):
    hostel_resident = "hostel_resident"
    outside_member = "outside_member"


class MealType(str, enum.Enum):
    lunch = "Lunch"
    dinner = "Dinner"


class MealStatus(str, enum.Enum):
    available = "available"
    sold = "sold"


class PaymentStatus(str, enum.Enum):
    paid = "paid"
    unpaid = "unpaid"


class CycleStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_type: Mapped[MemberType] = mapped_column(Enum(MemberType), default=MemberType.hostel_resident, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    room_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address_or_identity_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    whatsapp_number: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student)
    is_meal_member: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    meal_posts: Mapped[list["MealPost"]] = relationship(back_populates="seller", cascade="all, delete-orphan")


class MealPost(Base):
    __tablename__ = "meal_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    meal_type: Mapped[MealType] = mapped_column(Enum(MealType))
    date: Mapped[date] = mapped_column(Date, index=True)
    price: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MealStatus] = mapped_column(Enum(MealStatus), default=MealStatus.available, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    seller: Mapped[User] = relationship(back_populates="meal_posts")


class TodayMenu(Base):
    __tablename__ = "today_menus"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    lunch_menu: Mapped[str] = mapped_column(Text, default="Menu has not been published yet.")
    dinner_menu: Mapped[str] = mapped_column(Text, default="Menu has not been published yet.")
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(primary_key=True)
    message: Mapped[str] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class WeeklyCycle(Base):
    __tablename__ = "weekly_cycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[CycleStatus] = mapped_column(Enum(CycleStatus), default=CycleStatus.active, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    manager: Mapped[User] = relationship()


class MealMember(Base):
    __tablename__ = "meal_members"
    __table_args__ = (UniqueConstraint("user_id", name="uq_meal_member_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    added_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(foreign_keys=[user_id])


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("user_id", "cycle_id", name="uq_payment_user_cycle"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("weekly_cycles.id"), nullable=True, index=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.unpaid, index=True)
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(foreign_keys=[user_id])


class WeeklySkip(Base):
    __tablename__ = "weekly_skips"
    __table_args__ = (UniqueConstraint("user_id", "cycle_id", name="uq_weekly_skip_user_cycle"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("weekly_cycles.id"), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped[User] = relationship()
    cycle: Mapped[WeeklyCycle | None] = relationship()


class BazarExpense(Base):
    __tablename__ = "bazar_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("weekly_cycles.id"), nullable=True, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    item_name: Mapped[str] = mapped_column(String(140))
    amount: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    cycle: Mapped[WeeklyCycle | None] = relationship()
    creator: Mapped[User] = relationship()


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    lunch_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    dinner_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship()


class WeeklyNotice(Base):
    __tablename__ = "weekly_notices"

    id: Mapped[int] = mapped_column(primary_key=True)
    message: Mapped[str] = mapped_column(Text)
    cycle_id: Mapped[int | None] = mapped_column(ForeignKey("weekly_cycles.id"), nullable=True, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class BroadcastNotification(Base):
    __tablename__ = "broadcast_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(140))
    message: Mapped[str] = mapped_column(Text)
    meal_type: Mapped[MealType | None] = mapped_column(Enum(MealType), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    creator: Mapped[User | None] = relationship()


class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"
    __table_args__ = (UniqueConstraint("notification_id", "user_id", name="uq_notification_recipient"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("broadcast_notifications.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    notification: Mapped[BroadcastNotification] = relationship()
    user: Mapped[User] = relationship()


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    endpoint: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    p256dh: Mapped[str] = mapped_column(String(255))
    auth: Mapped[str] = mapped_column(String(255))
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped[User] = relationship()


class RegistrationControl(Base):
    __tablename__ = "registration_controls"

    id: Mapped[int] = mapped_column(primary_key=True)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    message: Mapped[str] = mapped_column(Text, default="Registration is open for UFTB Boys Hostel students.")
    max_registrations: Mapped[int | None] = mapped_column(nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

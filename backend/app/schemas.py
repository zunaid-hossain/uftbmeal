import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import CycleStatus, MealStatus, MealType, MemberType, PaymentStatus, UserRole


BD_WHATSAPP_PATTERN = re.compile(r"^8801[3-9]\d{8}$")


class UserRegister(BaseModel):
    member_type: MemberType = MemberType.hostel_resident
    full_name: str = Field(min_length=2, max_length=120)
    room_number: str | None = Field(default=None, max_length=30)
    address_or_identity_note: str | None = Field(default=None, max_length=500)
    whatsapp_number: str
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.student
    manager_registration_code: str | None = None

    @field_validator("whatsapp_number")
    @classmethod
    def validate_whatsapp(cls, value: str) -> str:
        normalized = re.sub(r"[\s+\-()]", "", value)
        if not BD_WHATSAPP_PATTERN.fullmatch(normalized):
            raise ValueError("Use Bangladesh format: 8801XXXXXXXXX")
        return normalized

    @model_validator(mode="after")
    def validate_member_details(self):
        if self.member_type == MemberType.hostel_resident and not (self.room_number or "").strip():
            raise ValueError("Hostel residents must provide room number")
        if self.member_type == MemberType.outside_member and not (self.address_or_identity_note or "").strip():
            raise ValueError("Outside meal members must provide a short identity note")
        return self


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_type: MemberType
    full_name: str
    room_number: str | None
    address_or_identity_note: str | None = None
    whatsapp_number: str
    role: UserRole
    is_meal_member: bool


class LoginRequest(BaseModel):
    whatsapp_number: str
    password: str

    @field_validator("whatsapp_number")
    @classmethod
    def normalize_whatsapp(cls, value: str) -> str:
        return re.sub(r"[\s+\-()]", "", value)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class MealCreate(BaseModel):
    meal_type: MealType
    date: date
    price: float = Field(gt=0, le=10000)
    note: str | None = Field(default=None, max_length=500)
    status: MealStatus = MealStatus.available


class MealPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_type: MealType
    date: date
    price: float
    note: str | None
    status: MealStatus
    created_at: datetime
    seller: UserPublic


class MenuUpdate(BaseModel):
    lunch_menu: str = Field(min_length=2, max_length=1000)
    dinner_menu: str = Field(min_length=2, max_length=1000)
    notice: str | None = Field(default=None, max_length=1000)


class MenuPublic(BaseModel):
    date: date
    lunch_menu: str
    dinner_menu: str
    notice: str | None = None
    updated_at: datetime | None = None


class CleanupResult(BaseModel):
    deleted: int
    cutoff: datetime


class MemberUpdate(BaseModel):
    is_meal_member: bool


class MemberPublic(BaseModel):
    id: int
    member_type: MemberType
    full_name: str
    room_number: str | None
    address_or_identity_note: str | None = None
    is_meal_member: bool
    payment_status: PaymentStatus = PaymentStatus.unpaid
    skipped_this_week: bool = False


class ManagerUserPublic(MemberPublic):
    whatsapp_number: str
    role: UserRole


class ManagerUserUpdate(BaseModel):
    member_type: MemberType
    full_name: str = Field(min_length=2, max_length=120)
    room_number: str | None = Field(default=None, max_length=30)
    address_or_identity_note: str | None = Field(default=None, max_length=500)
    whatsapp_number: str
    role: UserRole

    @field_validator("whatsapp_number")
    @classmethod
    def validate_whatsapp(cls, value: str) -> str:
        normalized = re.sub(r"[\s+\-()]", "", value)
        if not BD_WHATSAPP_PATTERN.fullmatch(normalized):
            raise ValueError("Use Bangladesh format: 8801XXXXXXXXX")
        return normalized

    @model_validator(mode="after")
    def validate_member_details(self):
        if self.member_type == MemberType.hostel_resident and not (self.room_number or "").strip():
            raise ValueError("Hostel residents must provide room number")
        if self.member_type == MemberType.outside_member and not (self.address_or_identity_note or "").strip():
            raise ValueError("Outside meal members must provide a short identity note")
        return self


class PaymentUpdate(BaseModel):
    status: PaymentStatus


class PaymentPublic(BaseModel):
    user_id: int
    member_type: MemberType
    full_name: str
    room_number: str | None
    address_or_identity_note: str | None = None
    status: PaymentStatus
    skipped_this_week: bool = False


class AttendancePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    lunch_checked: bool
    dinner_checked: bool
    skipped_this_week: bool = False


class RemainingMember(BaseModel):
    user_id: int
    member_type: MemberType
    full_name: str
    room_number: str | None
    address_or_identity_note: str | None = None
    skipped_this_week: bool = False


class RemainingAttendance(BaseModel):
    lunch: list[RemainingMember]
    dinner: list[RemainingMember]


class AttendanceDashboardRow(BaseModel):
    user_id: int
    member_type: MemberType
    full_name: str
    room_number: str | None
    address_or_identity_note: str | None = None
    lunch_checked: bool
    dinner_checked: bool
    skipped_this_week: bool = False


class CycleCreate(BaseModel):
    manager_id: int | None = None


class CyclePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_date: date
    end_date: date
    status: CycleStatus
    manager: UserPublic


class DashboardStats(BaseModel):
    total_members: int
    paid_members: int
    unpaid_members: int
    skipped_members: int = 0
    lunch_attendance: int
    dinner_attendance: int
    available_meals: int
    sold_meals: int


class RegistrationControlPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_open: bool
    message: str
    max_registrations: int | None = None
    current_registrations: int = 0
    remaining_slots: int | None = None
    updated_at: datetime | None = None


class RegistrationControlUpdate(BaseModel):
    is_open: bool
    message: str = Field(min_length=2, max_length=500)
    max_registrations: int | None = Field(default=None, ge=1, le=10000)


class MealProvidedNotificationCreate(BaseModel):
    meal_type: MealType
    message: str | None = Field(default=None, max_length=500)


class NotificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    meal_type: MealType | None = None
    created_by: int | None = None
    created_at: datetime
    creator: UserPublic | None = None


class BulkReminderResult(BaseModel):
    notified: int
    push_sent: int
    notification: NotificationPublic | None = None


class WeeklySkipCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class WeeklyStatusPublic(BaseModel):
    cycle: CyclePublic | None = None
    skipped_this_week: bool = False
    skip_reason: str | None = None


class WeeklyActiveUpdate(BaseModel):
    active: bool
    reason: str | None = Field(default=None, max_length=500)


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str = Field(min_length=10, max_length=500)
    keys: PushKeys
    user_agent: str | None = Field(default=None, max_length=255)


class PushPublicConfig(BaseModel):
    enabled: bool
    public_key: str | None = None


class BazarExpenseCreate(BaseModel):
    date: date
    item_name: str = Field(min_length=2, max_length=140)
    amount: float = Field(gt=0, le=1000000)
    note: str | None = Field(default=None, max_length=500)


class BazarExpensePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cycle_id: int | None = None
    date: date
    item_name: str
    amount: float
    note: str | None = None
    created_at: datetime
    creator: UserPublic


class BazarSummary(BaseModel):
    cycle: CyclePublic | None = None
    total_amount: float
    expense_count: int
    rows: list[BazarExpensePublic]

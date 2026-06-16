import json
import os

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import PushSubscription

try:
    from pywebpush import WebPushException, webpush
except Exception:  # pragma: no cover - optional dependency guard for local setup drift
    WebPushException = Exception
    webpush = None


def push_config() -> tuple[str | None, str | None, str]:
    public_key = os.getenv("VAPID_PUBLIC_KEY")
    private_key = os.getenv("VAPID_PRIVATE_KEY")
    subject = os.getenv("VAPID_SUBJECT", "mailto:admin@uftb-hostel.local")
    return public_key, private_key, subject


def push_enabled() -> bool:
    public_key, private_key, _ = push_config()
    return bool(public_key and private_key and webpush)


def _send_push_to_subscriptions(db: Session, subscriptions: list[PushSubscription], title: str, message: str, url: str) -> int:
    public_key, private_key, subject = push_config()
    if not (public_key and private_key and webpush):
        return 0

    payload = json.dumps({"title": title, "message": message, "url": url})
    sent = 0
    stale_subscription_ids = []
    for subscription in subscriptions:
        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": subject},
            )
            sent += 1
        except WebPushException as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code in {404, 410}:
                stale_subscription_ids.append(subscription.id)

    if stale_subscription_ids:
        db.execute(delete(PushSubscription).where(PushSubscription.id.in_(stale_subscription_ids)))
        db.commit()
    return sent


def send_push_to_all(db: Session, title: str, message: str, url: str = "/attendance") -> int:
    subscriptions = db.scalars(select(PushSubscription)).all()
    return _send_push_to_subscriptions(db, subscriptions, title, message, url)


def send_push_to_users(db: Session, user_ids: list[int] | set[int], title: str, message: str, url: str = "/payments") -> int:
    if not user_ids:
        return 0
    subscriptions = db.scalars(
        select(PushSubscription).where(PushSubscription.user_id.in_(set(user_ids)))
    ).all()
    return _send_push_to_subscriptions(db, subscriptions, title, message, url)

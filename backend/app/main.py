from contextlib import asynccontextmanager
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from .auth import require_meal_manager
from .database import Base, SessionLocal, apply_compatibility_migrations, engine, get_db
from .models import RegistrationControl, User
from .routes import auth, hostel, meals, menu
from .schemas import CleanupResult
from .utils.cleanup import cleanup_old_meal_posts, cleanup_weekly_data
from .utils.cycles import rotate_expired_cycle


scheduler = BackgroundScheduler(timezone="Asia/Dhaka")


def scheduled_cleanup():
    with SessionLocal() as db:
        cleanup_weekly_data(db)
        rotate_expired_cycle(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    apply_compatibility_migrations()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.get(RegistrationControl, 1) is None:
            db.add(RegistrationControl(id=1))
            db.commit()
        cleanup_weekly_data(db)
    scheduler.add_job(scheduled_cleanup, "cron", hour=3, minute=0, id="weekly-data-cleanup", replace_existing=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="UFTB Boys Hostel Meal Exchange",
    version="1.0.0",
    description="A trusted lunch and dinner exchange for UFTB Boys Hostel students.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(meals.router)
app.include_router(menu.router)
app.include_router(hostel.router)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/admin/cleanup-old-posts", response_model=CleanupResult)
def cleanup_old_posts(
    _: User = Depends(require_meal_manager),
    db: Session = Depends(get_db),
):
    deleted, cutoff = cleanup_old_meal_posts(db)
    return CleanupResult(deleted=deleted, cutoff=cutoff)

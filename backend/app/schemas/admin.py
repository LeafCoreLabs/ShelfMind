from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "user"
    store_id: int | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    store_id: int | None = None
    is_active: bool | None = None
    password: str | None = None


class StoreCreate(BaseModel):
    name: str
    location: str
    lat: float = 19.0760
    lon: float = 72.8777
    salary_cycle_day: int = 1
    phone: str | None = None
    business_type: str | None = None
    timezone: str = "Asia/Kolkata"
    preferences: dict | None = None


class StoreUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    lat: float | None = None
    lon: float | None = None
    salary_cycle_day: int | None = None
    phone: str | None = None
    business_type: str | None = None
    timezone: str | None = None
    preferences: dict | None = None
    is_active: bool | None = None


class OnboardingStepPayload(BaseModel):
    data: dict = Field(default_factory=dict)

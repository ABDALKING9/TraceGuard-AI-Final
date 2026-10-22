from pydantic import BaseModel, Field
from typing import Literal


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = ""
    status: Literal["Open", "Under Review", "Closed"] = "Open"


class NoteCreate(BaseModel):
    note_text: str = Field(min_length=1, max_length=5000)
    record_id: int | None = None
    disposition: Literal["Pending Review", "Reviewed — No Action", "Further Review Required"] = "Pending Review"


class ReviewUpdate(BaseModel):
    review_status: Literal["Pending Review", "Reviewed — No Action", "Further Review Required"]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=180)
    password: str = Field(min_length=1, max_length=200)


class SessionUser(BaseModel):
    email: str
    role: str = "demonstration operator"


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    expires_in_minutes: int
    user: SessionUser


class LogoutResponse(BaseModel):
    revoked: bool

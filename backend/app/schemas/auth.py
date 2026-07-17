from pydantic import BaseModel, Field
from typing import Optional


class AuthRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(max_length=255)
    password: str = Field(min_length=6, max_length=128)


class AuthLogin(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str = Field(max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserProfile"


class UserProfile(BaseModel):
    id: int
    username: str
    email: str
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None  # مطلوب فقط لو الحساب مفعّل عليه 2FA


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class EmailVerificationConfirm(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_code_base64: str


class TwoFactorCodeRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6)

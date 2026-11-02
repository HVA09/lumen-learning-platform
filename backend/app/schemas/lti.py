from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.lti_service import validate_lti_platform_endpoint_url


class LTIPlatformCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    issuer: str = Field(min_length=1, max_length=500)
    client_id: str = Field(min_length=1, max_length=255)
    deployment_id: str = Field(min_length=1, max_length=255)
    auth_login_url: str = Field(min_length=1, max_length=500)
    auth_token_url: str = Field(min_length=1, max_length=500)
    jwks_url: str = Field(min_length=1, max_length=500)

    @field_validator(
        "name", "issuer", "client_id", "deployment_id",
        "auth_login_url", "auth_token_url", "jwks_url",
        mode="before",
    )
    @classmethod
    def trim_required_values(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("LTI platform fields cannot be blank")
        return cleaned

    @field_validator("issuer", "auth_login_url", "auth_token_url", "jwks_url")
    @classmethod
    def validate_platform_urls(cls, value: str) -> str:
        return validate_lti_platform_endpoint_url(value)


class LTIPlatformOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    issuer: str
    client_id: str
    deployment_id: str


class LTIExchangeCodeRequest(BaseModel):
    code: str = Field(min_length=32, max_length=256)



class LTIAssignmentLinkCreate(BaseModel):
    platform_id: int = Field(gt=0)
    assignment_id: int = Field(gt=0)
    resource_link_id: str = Field(min_length=1, max_length=255)
    score_maximum: float = Field(default=100.0, gt=0, le=1000000, allow_inf_nan=False)

    @field_validator("resource_link_id")
    @classmethod
    def validate_resource_link_id(cls, value: str) -> str:
        if not value.isascii() or not value.strip():
            raise ValueError("resource_link_id must be a non-empty ASCII identifier")
        return value.strip()


class LTIAssignmentLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    platform_id: int
    assignment_id: int
    deployment_id: str
    resource_link_id: str
    lineitem_ready: bool
    score_scope_allowed: bool
    score_maximum: float
    created_at: datetime


class LTIDiscoveredResourceLinkOut(BaseModel):
    id: int
    platform_id: int
    deployment_id: str
    resource_link_id: str
    lineitem_ready: bool
    score_scope_allowed: bool
    first_seen_at: datetime
    last_seen_at: datetime
    mapped_assignment_id: int | None = None


class LTIAGSGradeEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    submission_id: int
    grade_version: int
    status: str
    attempts: int
    last_error: str | None
    created_at: datetime
    delivered_at: datetime | None

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.lti_service import validate_lti_platform_endpoint_url


class LTIPlatformCreate(BaseModel):
    name: str
    issuer: str
    client_id: str
    deployment_id: str
    auth_login_url: str
    auth_token_url: str
    jwks_url: str

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

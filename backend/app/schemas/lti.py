from pydantic import BaseModel, ConfigDict, Field


class LTIPlatformCreate(BaseModel):
    name: str
    issuer: str
    client_id: str
    deployment_id: str
    auth_login_url: str
    auth_token_url: str
    jwks_url: str


class LTIPlatformOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    issuer: str
    client_id: str
    deployment_id: str


class LTIExchangeCodeRequest(BaseModel):
    code: str = Field(min_length=32, max_length=256)

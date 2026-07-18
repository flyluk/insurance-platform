from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ProductCode = Literal["AUTO", "HOME", "LIFE"]
PublishStatus = Literal["DRAFT", "PUBLISHED"]
FieldType = Literal["number", "boolean", "text", "select"]


class RiskField(BaseModel):
    key: str
    label: str
    type: FieldType = "number"
    required: bool = True
    default: Any = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    options: list[dict[str, Any]] | None = None


class UwCondition(BaseModel):
    field: str
    op: Literal["eq", "ne", "gt", "gte", "lt", "lte"] = "eq"
    value: Any


class UwRule(BaseModel):
    all: list[UwCondition] = Field(default_factory=list)
    reason: str = ""


class UwRules(BaseModel):
    decline: list[UwRule] = Field(default_factory=list)
    refer: list[UwRule] = Field(default_factory=list)


class PlanCreate(BaseModel):
    product_code: ProductCode
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    base_premium: float = Field(ge=0)
    sort_order: int = 0
    risk_schema: list[RiskField] = Field(default_factory=list)
    uw_rules: UwRules | None = None


class PlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    base_premium: float | None = Field(default=None, ge=0)
    sort_order: int | None = None
    risk_schema: list[RiskField] | None = None
    uw_rules: UwRules | None = None


class RiderCreate(BaseModel):
    product_code: ProductCode
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    premium: float = Field(ge=0)
    sort_order: int = 0


class RiderUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    premium: float | None = Field(default=None, ge=0)
    sort_order: int | None = None


class RiderOut(BaseModel):
    id: str
    product_code: str
    code: str
    name: str
    description: str | None
    premium: float
    status: str
    sort_order: int
    created_at: datetime
    updated_at: datetime
    effective_premium: float | None = None

    model_config = {"from_attributes": True}


class PlanOut(BaseModel):
    id: str
    product_code: str
    code: str
    name: str
    description: str | None
    base_premium: float
    status: str
    sort_order: int
    risk_schema: list[Any] = Field(default_factory=list)
    uw_rules: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    riders: list[RiderOut] = Field(default_factory=list)
    effective_premium: float | None = None

    model_config = {"from_attributes": True}

    @field_validator("risk_schema", mode="before")
    @classmethod
    def _schema(cls, v: Any) -> list:
        return v or []

    @field_validator("uw_rules", mode="before")
    @classmethod
    def _uw(cls, v: Any) -> dict:
        return v or {"decline": [], "refer": []}


class PlanRidersUpdate(BaseModel):
    rider_ids: list[str] = Field(default_factory=list)


class LineSummary(BaseModel):
    product_code: ProductCode
    plan_count: int
    rider_count: int
    published_plans: int


class RateVersionCreate(BaseModel):
    version_code: str = Field(min_length=1, max_length=64)
    amount: float = Field(ge=0)
    effective_from: date
    effective_to: date | None = None


class RateVersionOut(BaseModel):
    id: str
    plan_id: str | None
    rider_id: str | None
    version_code: str
    amount: float
    effective_from: date
    effective_to: date | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QuoteResolveIn(BaseModel):
    plan_id: str
    rider_ids: list[str] = Field(default_factory=list)
    as_of: date | None = None


class QuoteResolveOut(BaseModel):
    plan_id: str
    plan_amount: float
    plan_rate_version_id: str | None
    riders: list[dict[str, Any]]
    total_base: float


class EvaluateUwIn(BaseModel):
    plan_id: str | None = None
    product_code: str | None = None
    risk_attributes: dict[str, Any] = Field(default_factory=dict)
    annual_premium: float


class EvaluateUwOut(BaseModel):
    decision: str
    reason: str
    plan_id: str | None = None

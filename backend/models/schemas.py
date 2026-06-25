from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PaperOut(BaseModel):
    id: str
    title: str
    authors: Optional[str]
    year: Optional[int]
    journal: Optional[str]
    abstract: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class PaperDetailOut(PaperOut):
    full_text: Optional[str]

class PaperListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=1000)
    keyword: Optional[str] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    tag: Optional[str] = None
    domain_id: Optional[str] = None

class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    scope_paper_ids: list[str] = []
    scope_domain_id: Optional[str] = None
    stream: bool = True

class ChatEvent(BaseModel):
    type: str
    content: Optional[str] = None
    refs: Optional[list[dict]] = None

class ExtractRequest(BaseModel):
    paper_id: str

class ExtractStatus(BaseModel):
    paper_id: str
    status: str
    entity_count: Optional[int] = None

class VisualizeRequest(BaseModel):
    query: str
    scope_paper_ids: list[str] = []

class VisualizeResponse(BaseModel):
    chart_type: str
    title: str
    data: list[dict]
    echarts_option: dict
    explanation: Optional[str] = None

class EntityQueryParams(BaseModel):
    entity_type: Optional[str] = None
    paper_id: Optional[str] = None
    attribute_key: Optional[str] = None
    attribute_value: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)

class AnalyticsQueryParams(BaseModel):
    metric: str = Field(default="avg", pattern="^(avg|median)$")
    method: Optional[str] = None
    element: Optional[str] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    confidence_min: float = Field(default=0.7, ge=0, le=1)

class RecordQueryParams(BaseModel):
    paper_id: Optional[str] = None
    method: Optional[str] = None
    element: Optional[str] = None
    confidence_min: float = Field(default=0.0, ge=0, le=1)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", max_length=256)


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    conversation_id: str
    role: str
    content: str
    citations: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LibraryDomainOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    is_default: bool = False
    paper_count: int = 0
    ingested_count: int = 0
    processing_count: int = 0
    failed_count: int = 0
    latest_paper_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LibraryDomainCreate(BaseModel):
    id: str = Field(min_length=2, max_length=64, pattern="^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=2, max_length=128)
    description: Optional[str] = None
    color: Optional[str] = Field(default=None, pattern="^#[0-9A-Fa-f]{6}$")
    sort_order: int = 0
    is_default: bool = False


class LibraryDomainUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=128)
    description: Optional[str] = None
    color: Optional[str] = Field(default=None, pattern="^#[0-9A-Fa-f]{6}$")
    sort_order: Optional[int] = None
    is_default: Optional[bool] = None


class PaperDomainAssignRequest(BaseModel):
    domain_id: str = Field(min_length=2, max_length=64)


class DownloadCreate(BaseModel):
    identifier: str = Field(min_length=3, max_length=512)
    strategy: str = Field(default="legal_only", pattern="^(legal_only|oa_first|fastest)$")


class DownloadIngestRequest(BaseModel):
    domain_id: str = Field(min_length=2, max_length=64)
    auto_mine: bool = False


class DownloadedPaperOut(BaseModel):
    id: str
    identifier: str
    doi: Optional[str] = None
    title: Optional[str] = None
    source: Optional[str] = None
    strategy: str = "legal_only"
    file_path: Optional[str] = None
    paper_id: Optional[str] = None
    status: str
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

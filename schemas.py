from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from models import EnrichmentStatus

class ProductResponse(BaseModel):
    id: UUID
    batch_id: Optional[UUID]
    raw_name: str
    seo_description: Optional[str]
    category_tags: Optional[str]
    status: EnrichmentStatus
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class BatchResponse(BaseModel):
    id: UUID
    filename: str
    total_rows: int
    processed_rows: int
    status: EnrichmentStatus
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class PaginatedProductsResponse(BaseModel):
    total: int
    page: int
    size: int
    products: List[ProductResponse]

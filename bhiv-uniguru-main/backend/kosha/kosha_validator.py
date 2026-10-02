from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class KoshaEntry(BaseModel):
    knowledge_id: str = Field(..., description="Unique identifier for the knowledge entry")
    domain: str = Field(..., description="Domain must be one of: Agriculture, Urban, Water / Rivers, Infrastructure")
    content: str = Field(..., description="The verified content")
    source: str = Field(..., description="Source of the knowledge")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    timestamp: str = Field(..., description="ISO 8601 formatted timestamp")
    tags: List[str] = Field(default_factory=list, description="List of tags for retrieval")
    clean_content: Optional[str] = Field(default=None, description="Cleaned version of content (optional)")

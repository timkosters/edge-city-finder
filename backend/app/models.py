from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime

# Valid funnel stages
FunnelStage = Literal['discovered', 'qualified', 'interesting', 'contacted', 'dismissed']

class Property(BaseModel):
    id: Optional[str] = None
    title: str
    url: str
    price: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: str = "New"  # New, Starred, Reviewed, Contacted, Passed, Archived
    score: int = 0
    
    # Vital Stats
    acreage: Optional[float] = None
    bed_count: Optional[int] = None
    year_built: Optional[int] = None
    
    # Logistics
    nearest_airport: Optional[str] = None
    drive_time_minutes: Optional[int] = None
    
    # AI
    ai_summary: Optional[str] = None
    image_url: Optional[str] = None
    
    # Funnel Tracking
    funnel_stage: FunnelStage = "discovered"
    is_new: bool = True
    
    # Verification Metadata
    verification_result: Optional[str] = None  # 'available', 'sold', 'not_listing', etc.
    verification_reason: Optional[str] = None  # Human-readable explanation
    last_verified_at: Optional[datetime] = None
    source_type: Optional[str] = None  # 'listing', 'news', 'auction', 'foreclosure'
    
    # Discovery Metadata
    discovered_via: Optional[str] = None  # 'exa_loopnet', 'tavily_news', 'manual', etc.
    search_query: Optional[str] = None  # The query that found this
    
    # Feedback Learning
    dismissed_reason: Optional[str] = None  # 'already_sold', 'not_relevant', etc.
    dismissed_pattern: Optional[str] = None  # Extracted pattern for future filtering


class SearchResult(BaseModel):
    properties: List[Property]


class VerificationResult(BaseModel):
    """Result from Analyst verification"""
    is_listing: bool
    is_available: bool
    classification: FunnelStage  # 'qualified', 'interesting', or 'dismissed'
    reason: str
    extracted_data: Optional[dict] = None  # price, beds, acreage from page

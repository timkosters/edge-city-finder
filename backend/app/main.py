from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from app.models import SearchResult, Property
from app.database import property_db

app = FastAPI(title="Edge City Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],  # Allow all for Railway
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "Edge City Finder Backend is running",
        "database_connected": property_db.is_available()
    }


# ----------------- Property Endpoints -----------------

@app.get("/api/properties", response_model=SearchResult)
async def get_properties(
    status: Optional[str] = None,
    funnel_stage: Optional[str] = None
):
    """
    Get all properties, optionally filtered by status or funnel_stage.
    """
    if property_db.is_available():
        properties = await property_db.get_all_properties(
            status_filter=status,
            funnel_filter=funnel_stage
        )
        return SearchResult(properties=properties)
    
    # Fall back to empty if no database
    return SearchResult(properties=[])


@app.get("/api/properties/qualified", response_model=SearchResult)
async def get_qualified_leads():
    """Get only qualified leads (actual listings that are available)."""
    if property_db.is_available():
        properties = await property_db.get_all_properties(funnel_filter="qualified")
        return SearchResult(properties=properties)
    return SearchResult(properties=[])


@app.get("/api/properties/interesting", response_model=SearchResult)
async def get_interesting_finds():
    """Get interesting finds (news/articles, not direct listings)."""
    if property_db.is_available():
        properties = await property_db.get_all_properties(funnel_filter="interesting")
        return SearchResult(properties=properties)
    return SearchResult(properties=[])


@app.get("/api/properties/{property_id}", response_model=Property)
async def get_property(property_id: str):
    """Get a single property by ID."""
    prop = await property_db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


@app.patch("/api/properties/{property_id}/status")
async def update_property_status(property_id: str, status: str):
    """Update property status."""
    valid_statuses = ["New", "Starred", "Reviewed", "Contacted", "Passed", "Archived"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    prop = await property_db.update_status(property_id, status)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"success": True, "property": prop}


class DismissRequest(BaseModel):
    reason: str
    pattern: Optional[str] = None


@app.post("/api/properties/{property_id}/dismiss")
async def dismiss_property(property_id: str, request: DismissRequest):
    """
    Dismiss a property with a reason. Updates funnel_stage to 'dismissed'
    and stores the pattern for future filtering.
    """
    prop = await property_db.dismiss_property(
        property_id, 
        reason=request.reason,
        pattern=request.pattern
    )
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"success": True, "property": prop}


@app.delete("/api/properties/{property_id}")
async def delete_property(property_id: str):
    """Delete a property."""
    success = await property_db.delete_property(property_id)
    if not success:
        raise HTTPException(status_code=404, detail="Property not found or database unavailable")
    return {"success": True}


# ----------------- Agent Endpoints -----------------

class SearchRequest(BaseModel):
    query: Optional[str] = None
    categories: Optional[List[str]] = None  # ['platforms', 'news', 'distress']
    verify: bool = True  # Run analyst verification


@app.post("/api/scout/run", response_model=SearchResult)
async def run_scout(request: Optional[SearchRequest] = None):
    """
    Trigger the Scout agent to find new properties.
    
    Optional body:
    - query: Custom search query
    - categories: Which search categories to run
    - verify: Whether to run Gemini verification (default: true)
    """
    from app.scout.agent import scout_agent
    from app.analyst.agent import analyst_agent
    
    # Get existing URLs for deduplication
    existing_urls = await property_db.get_all_urls()
    
    # Parse request
    custom_query = request.query if request else None
    categories = request.categories if request else None
    should_verify = request.verify if request else True
    
    # Run scout
    properties = await scout_agent.find_candidates(
        existing_urls=existing_urls,
        custom_query=custom_query,
        categories=categories
    )
    
    if not properties:
        return SearchResult(properties=[])
    
    # Run verification if enabled
    if should_verify:
        print(f"Verifying {len(properties)} properties with Analyst agent...")
        verified_properties = []
        for prop in properties:
            try:
                verified_prop = await analyst_agent.verify_and_analyze(prop)
                verified_properties.append(verified_prop)
            except Exception as e:
                print(f"Error verifying {prop.title}: {e}")
                prop.funnel_stage = "interesting"  # Default on error
                verified_properties.append(prop)
        properties = verified_properties
    
    # Save to database
    if property_db.is_available():
        try:
            properties = await property_db.upsert_properties(properties)
        except Exception as e:
            print(f"Error upserting properties: {e}")
    
    return SearchResult(properties=properties)


@app.post("/api/scout/search")
async def manual_search(query: str = Query(..., description="Search query")):
    """
    Run a manual search with a custom query.
    Results are verified and saved to database.
    """
    request = SearchRequest(query=query, verify=True)
    return await run_scout(request)


@app.post("/api/analyst/verify/{property_id}", response_model=Property)
async def verify_single_property(property_id: str):
    """
    Re-verify a specific property using the Analyst agent.
    """
    from app.analyst.agent import analyst_agent
    
    prop = await property_db.get_property(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    verified_prop = await analyst_agent.verify_and_analyze(prop)
    
    if property_db.is_available():
        verified_prop = await property_db.upsert_property(verified_prop)
    
    return verified_prop


@app.post("/api/properties/{property_id}/mark-seen")
async def mark_as_seen(property_id: str):
    """Mark a property as seen (is_new = false)."""
    prop = await property_db.mark_as_seen(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"success": True}

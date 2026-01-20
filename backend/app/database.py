"""
Supabase database layer for property persistence.
"""
from typing import List, Optional, Set
from supabase import create_client, Client
from app.config import settings
from app.models import Property
from datetime import datetime


def get_supabase_client() -> Optional[Client]:
    """Get Supabase client if credentials are configured."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


class PropertyDatabase:
    """Database operations for properties."""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.table_name = "properties"
    
    def is_available(self) -> bool:
        """Check if database is configured and available."""
        return self.client is not None
    
    async def get_all_properties(
        self, 
        status_filter: Optional[str] = None,
        funnel_filter: Optional[str] = None
    ) -> List[Property]:
        """Get all properties, optionally filtered by status or funnel stage."""
        if not self.is_available():
            return []
        
        query = self.client.table(self.table_name).select("*")
        
        if status_filter:
            query = query.eq("status", status_filter)
        
        if funnel_filter:
            query = query.eq("funnel_stage", funnel_filter)
        else:
            # By default, exclude dismissed
            query = query.neq("funnel_stage", "dismissed")
        
        result = query.order("created_at", desc=True).execute()
        
        return [Property(**row) for row in result.data]
    
    async def get_all_urls(self) -> Set[str]:
        """Get all existing property URLs for deduplication."""
        if not self.is_available():
            return set()
        
        result = self.client.table(self.table_name).select("url").execute()
        return {row["url"] for row in result.data if row.get("url")}
    
    async def get_dismissed_patterns(self) -> List[str]:
        """Get patterns from dismissed properties for filtering."""
        if not self.is_available():
            return []
        
        result = self.client.table(self.table_name).select("dismissed_pattern").eq(
            "funnel_stage", "dismissed"
        ).not_.is_("dismissed_pattern", "null").execute()
        
        return [row["dismissed_pattern"] for row in result.data if row.get("dismissed_pattern")]
    
    async def get_property(self, property_id: str) -> Optional[Property]:
        """Get a single property by ID."""
        if not self.is_available():
            return None
        
        result = self.client.table(self.table_name).select("*").eq("id", property_id).single().execute()
        
        if result.data:
            return Property(**result.data)
        return None
    
    async def upsert_property(self, prop: Property) -> Property:
        """Insert or update a property."""
        if not self.is_available():
            return prop
        
        data = prop.model_dump(exclude_none=True)
        
        # Handle datetime serialization
        if 'last_verified_at' in data and data['last_verified_at']:
            data['last_verified_at'] = data['last_verified_at'].isoformat()
        
        result = self.client.table(self.table_name).upsert(
            data, 
            on_conflict="url"  # Use URL as unique key
        ).execute()
        
        if result.data:
            return Property(**result.data[0])
        return prop
    
    async def upsert_properties(self, properties: List[Property]) -> List[Property]:
        """Bulk insert or update properties."""
        if not self.is_available():
            return properties
        
        data = []
        for p in properties:
            d = p.model_dump(exclude_none=True)
            # Handle datetime serialization
            if 'last_verified_at' in d and d['last_verified_at']:
                d['last_verified_at'] = d['last_verified_at'].isoformat()
            data.append(d)
        
        result = self.client.table(self.table_name).upsert(
            data,
            on_conflict="url"
        ).execute()
        
        return [Property(**row) for row in result.data]
    
    async def update_status(self, property_id: str, status: str) -> Optional[Property]:
        """Update the status of a property (Star, Archive, etc.)."""
        if not self.is_available():
            return None
        
        result = self.client.table(self.table_name).update({
            "status": status
        }).eq("id", property_id).execute()
        
        if result.data:
            return Property(**result.data[0])
        return None
    
    async def dismiss_property(
        self, 
        property_id: str, 
        reason: str,
        pattern: Optional[str] = None
    ) -> Optional[Property]:
        """Dismiss a property with a reason and optional pattern for future filtering."""
        if not self.is_available():
            return None
        
        update_data = {
            "funnel_stage": "dismissed",
            "dismissed_reason": reason,
            "status": "Archived"
        }
        
        if pattern:
            update_data["dismissed_pattern"] = pattern
        
        result = self.client.table(self.table_name).update(update_data).eq(
            "id", property_id
        ).execute()
        
        if result.data:
            return Property(**result.data[0])
        return None
    
    async def mark_as_seen(self, property_id: str) -> Optional[Property]:
        """Mark a property as seen (is_new = false)."""
        if not self.is_available():
            return None
        
        result = self.client.table(self.table_name).update({
            "is_new": False
        }).eq("id", property_id).execute()
        
        if result.data:
            return Property(**result.data[0])
        return None
    
    async def delete_property(self, property_id: str) -> bool:
        """Delete a property."""
        if not self.is_available():
            return False
        
        self.client.table(self.table_name).delete().eq("id", property_id).execute()
        return True


# Singleton instance
property_db = PropertyDatabase()

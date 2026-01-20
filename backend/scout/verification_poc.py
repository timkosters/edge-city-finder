import asyncio
import httpx
from typing import List, Optional

async def verify_url(url: str) -> bool:
    """
    Level 0 Check: Does the link actually work?
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.head(url, follow_redirects=True)
            return response.status_code == 200
    except Exception:
        return False

async def verify_content_match(url: str, entity_name: str, keywords: List[str]) -> bool:
    """
    Level 0 Check: Does the page actually mention what we think it does?
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, follow_redirects=True)
            content = response.text.lower()
            
            # 1. Check if entity name is present (fuzzy match logic would go here)
            if entity_name.lower() not in content:
                return False
                
            # 2. Check if at least one keyword is present
            if not any(k.lower() in content for k in keywords):
                return False
                
            return True
    except Exception:
        return False

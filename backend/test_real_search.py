"""
Real Search Test Script
Runs Exa.ai and Tavily searches, verifies results, and outputs real properties.
"""
import asyncio
import os
import json
import httpx
from dotenv import load_dotenv
from exa_py import Exa
import datetime

# Load environment variables
load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Common US state abbreviations for location extraction
US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL',
    'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT',
    'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
    'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
}

import re

def extract_location(text: str, title: str) -> str:
    """Extract location from title or text using patterns."""
    combined = f"{title} {text}"
    
    # Pattern: "City, ST" or "City, State"
    pattern = r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?),\s*([A-Z]{2})\b'
    match = re.search(pattern, combined)
    if match:
        city, state = match.groups()
        if state in US_STATES:
            return f"{city}, {state}"
    
    # Pattern: Just state abbreviation in context
    for state in US_STATES:
        if f" {state} " in combined or combined.endswith(f" {state}"):
            return state
    
    return "Location Unknown"


async def verify_url(url: str) -> bool:
    """Check if URL is accessible."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.head(url)
            return response.status_code == 200
    except Exception as e:
        print(f"  URL verification failed: {e}")
        return False


async def search_exa() -> list:
    """Run Exa.ai search and return results."""
    if not EXA_API_KEY:
        print("❌ EXA_API_KEY not found")
        return []
    
    print("\n" + "="*60)
    print("🔍 RUNNING EXA.AI SEARCH")
    print("="*60)
    
    exa = Exa(api_key=EXA_API_KEY)
    
    # Calculate date range for recent results (last 3 months)
    start_date = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
    
    # Target actual listing platforms with site: operators for better results
    queries = [
        # Direct platform searches - commercial real estate
        "site:loopnet.com campus OR college OR university for sale",
        "site:crexi.com institutional property school campus",
        "site:landwatch.com retreat center OR camp property acreage",
        "site:landandfarm.com camp OR conference center for sale",
        # Specific property type searches
        "site:loopnet.com hotel resort for sale acres",
        "site:crexi.com hospitality development opportunity",
        "site:landsofamerica.com dormitory OR housing campus",
        # International platforms
        "site:properstar.com rural hotel estate for sale",
        "site:kyero.com rural retreat hotel Spain Portugal",
    ]
    
    results = []
    
    for query in queries:
        print(f"\n📝 Query: '{query}'")
        try:
            # Using new Exa v2 API - search() now returns text by default
            response = exa.search(
                query,
                num_results=3,
                start_published_date=start_date,
                contents={"text": {"max_characters": 1000}}
            )
            
            print(f"   Found {len(response.results)} results")
            
            for result in response.results:
                results.append({
                    "source": "exa",
                    "title": result.title or "Untitled",
                    "url": result.url,
                    "text": (result.text or "")[:500],
                    "location": extract_location(result.text or "", result.title or "")
                })
                print(f"   ✓ {result.title[:60]}..." if result.title else "   ✓ Untitled")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    return results


async def search_tavily() -> list:
    """Run Tavily search and return results."""
    if not TAVILY_API_KEY:
        print("❌ TAVILY_API_KEY not found")
        return []
    
    print("\n" + "="*60)
    print("🔍 RUNNING TAVILY SEARCH")
    print("="*60)
    
    queries = [
        "distressed college campus for sale bankruptcy",
        "summer camp property for sale closing",
        "retreat center for sale rural property",
    ]
    
    results = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for query in queries:
            print(f"\n📝 Query: '{query}'")
            try:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": TAVILY_API_KEY,
                        "query": query,
                        "search_depth": "advanced",
                        "include_answer": False,
                        "max_results": 5
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                tavily_results = data.get("results", [])
                print(f"   Found {len(tavily_results)} results")
                
                for item in tavily_results:
                    results.append({
                        "source": "tavily",
                        "title": item.get("title", "Untitled"),
                        "url": item.get("url", ""),
                        "text": item.get("content", "")[:500],
                        "location": extract_location(item.get("content", ""), item.get("title", ""))
                    })
                    print(f"   ✓ {item.get('title', 'Untitled')[:60]}...")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
    
    return results


async def verify_results(results: list) -> list:
    """Verify each result URL is accessible."""
    print("\n" + "="*60)
    print("✅ VERIFYING RESULTS (checking URLs are real)")
    print("="*60)
    
    verified = []
    seen_urls = set()
    
    for result in results:
        url = result["url"]
        
        # Skip duplicates
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        print(f"\n🔗 Checking: {url[:70]}...")
        is_valid = await verify_url(url)
        
        if is_valid:
            print("   ✓ URL is accessible")
            verified.append(result)
        else:
            print("   ✗ URL not accessible - skipping")
    
    return verified


async def main():
    print("\n" + "🏠"*20)
    print("EDGE CITY FINDER - REAL SEARCH TEST")
    print("🏠"*20)
    
    # Run both searches
    exa_results = await search_exa()
    tavily_results = await search_tavily()
    
    all_results = exa_results + tavily_results
    
    print(f"\n📊 Total raw results: {len(all_results)}")
    print(f"   - Exa.ai: {len(exa_results)}")
    print(f"   - Tavily: {len(tavily_results)}")
    
    # Verify results
    verified_results = await verify_results(all_results)
    
    # Final output
    print("\n" + "="*60)
    print(f"🎉 VERIFIED PROPERTIES: {len(verified_results)}")
    print("="*60)
    
    for i, prop in enumerate(verified_results, 1):
        print(f"\n--- Property {i} [{prop['source'].upper()}] ---")
        print(f"Title: {prop['title']}")
        print(f"URL: {prop['url']}")
        print(f"Location: {prop['location']}")
        print(f"Description: {prop['text'][:200]}...")
    
    # Save to JSON for reference
    with open("search_results.json", "w") as f:
        json.dump(verified_results, f, indent=2)
    print(f"\n💾 Results saved to search_results.json")
    
    return verified_results


if __name__ == "__main__":
    asyncio.run(main())

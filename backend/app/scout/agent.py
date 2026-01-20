from exa_py import Exa
from tavily import TavilyClient
from app.config import settings
from app.models import Property
from typing import List, Set, Optional
import datetime
import re

# Common US state abbreviations for location extraction
US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL',
    'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT',
    'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
    'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
}

# Search query categories with source tracking
SEARCH_QUERIES = {
    # Platform-focused queries (actual listings)
    "platforms": [
        ("site:loopnet.com college campus for sale", "exa_loopnet"),
        ("site:crexi.com institutional property for sale", "exa_crexi"),
        ("site:auction.com commercial property foreclosure", "exa_auction"),
        ("site:ten-x.com hotel resort auction", "exa_tenx"),
        ("site:landwatch.com large acreage retreat center", "exa_landwatch"),
        ("site:landsofamerica.com campus dormitory for sale", "exa_landsofamerica"),
    ],
    # Local news monitoring
    "news": [
        ("college closing announcement campus for sale", "exa_news"),
        ("university shutdown bankruptcy real estate", "exa_news"),
        ("resort hotel foreclosure auction rural", "exa_news"),
        ("summer camp property sale closing", "exa_news"),
        ("boarding school closing campus available", "exa_news"),
        ("monastery convent sold conversion opportunity", "exa_news"),
    ],
    # Distress signals
    "distress": [
        ("WARN Act notice college layoffs closure", "exa_legal"),
        ("Chapter 11 bankruptcy college university campus", "exa_legal"),
        ("foreclosure rural hotel resort property", "exa_foreclosure"),
        ("abandoned institutional building redevelopment", "exa_distress"),
    ],
}


class ScoutAgent:
    def __init__(self):
        self.exa = Exa(api_key=settings.EXA_API_KEY) if settings.EXA_API_KEY else None
        self.tavily = TavilyClient(api_key=settings.TAVILY_API_KEY) if settings.TAVILY_API_KEY else None

    def _extract_location(self, text: str, title: str) -> str:
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
    
    def _extract_price(self, text: str) -> Optional[str]:
        """Extract price from text."""
        # Pattern: $X,XXX,XXX or $X.X million
        patterns = [
            r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|M))?',
            r'asking\s+\$[\d,]+',
            r'listed\s+(?:at|for)\s+\$[\d,]+',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        base_url = url.split('?')[0].split('#')[0]
        return base_url.rstrip('/')
    
    def _determine_source_type(self, url: str, discovered_via: str) -> str:
        """Determine if source is a listing, news, or auction."""
        url_lower = url.lower()
        
        # Listing platforms
        if any(site in url_lower for site in ['loopnet', 'crexi', 'landwatch', 'landsofamerica']):
            return 'listing'
        
        # Auction sites
        if any(site in url_lower for site in ['auction.com', 'ten-x', 'hubzu']):
            return 'auction'
        
        # News sources
        if any(site in url_lower for site in ['news', 'journal', 'times', 'post', 'herald', 'nytimes', 'wsj']):
            return 'news'
        
        # Based on discovery method
        if 'legal' in discovered_via or 'foreclosure' in discovered_via:
            return 'foreclosure'
        
        return 'news'  # Default to news

    async def find_candidates(
        self, 
        existing_urls: Set[str] = None,
        custom_query: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> List[Property]:
        """
        Search for distressed properties using Exa.ai and Tavily.
        
        Args:
            existing_urls: URLs already in database to skip
            custom_query: Optional manual search query
            categories: Which query categories to run ('platforms', 'news', 'distress')
        """
        if not self.exa:
            print("WARNING: Exa API key not found. Returning empty list.")
            return []

        if existing_urls is None:
            existing_urls = set()
        
        if categories is None:
            categories = ['platforms', 'news', 'distress']

        # Date range for recent content (last 3 months)
        start_date = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")

        found_properties = []
        seen_urls: Set[str] = set()
        
        # Build query list
        queries_to_run = []
        
        # Add custom query if provided
        if custom_query:
            queries_to_run.append((custom_query, "manual"))
        
        # Add category queries
        for category in categories:
            if category in SEARCH_QUERIES:
                queries_to_run.extend(SEARCH_QUERIES[category])

        for query, discovered_via in queries_to_run:
            try:
                # Run Exa search
                response = self.exa.search(
                    query,
                    num_results=5,
                    start_published_date=start_date,
                    contents={"text": {"max_characters": 1500}}
                )
                
                for result in response.results:
                    normalized_url = self._normalize_url(result.url)
                    
                    # Skip duplicates
                    if normalized_url in existing_urls or normalized_url in seen_urls:
                        print(f"Skipping duplicate: {normalized_url}")
                        continue
                    
                    seen_urls.add(normalized_url)
                    
                    # Extract data
                    text_content = result.text or ""
                    location = self._extract_location(text_content, result.title or "")
                    price = self._extract_price(text_content)
                    source_type = self._determine_source_type(result.url, discovered_via)
                    
                    prop = Property(
                        title=result.title or "Untitled Property",
                        url=result.url,
                        location=location,
                        price=price,
                        description=text_content[:500] + "..." if len(text_content) > 500 else text_content,
                        status="New",
                        score=50,
                        image_url=getattr(result, 'image', None),
                        # Funnel tracking
                        funnel_stage="discovered",
                        is_new=True,
                        source_type=source_type,
                        discovered_via=discovered_via,
                        search_query=query,
                    )
                    found_properties.append(prop)
                    
            except Exception as e:
                print(f"Error searching for '{query}': {e}")
                continue
        
        # Also run Tavily for additional coverage
        if self.tavily and not custom_query:
            await self._search_tavily(found_properties, seen_urls, existing_urls)

        print(f"Scout found {len(found_properties)} new unique properties")
        return found_properties
    
    async def _search_tavily(
        self, 
        found_properties: List[Property], 
        seen_urls: Set[str],
        existing_urls: Set[str]
    ):
        """Additional search via Tavily for news coverage."""
        tavily_queries = [
            "college campus for sale closing 2025 2026",
            "rural resort hotel foreclosure auction",
            "summer camp property sale available",
        ]
        
        for query in tavily_queries:
            try:
                response = self.tavily.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5
                )
                
                for result in response.get('results', []):
                    url = result.get('url', '')
                    normalized_url = self._normalize_url(url)
                    
                    if normalized_url in existing_urls or normalized_url in seen_urls:
                        continue
                    
                    seen_urls.add(normalized_url)
                    
                    text_content = result.get('content', '')
                    title = result.get('title', 'Untitled')
                    
                    prop = Property(
                        title=title,
                        url=url,
                        location=self._extract_location(text_content, title),
                        price=self._extract_price(text_content),
                        description=text_content[:500] + "..." if len(text_content) > 500 else text_content,
                        status="New",
                        score=50,
                        funnel_stage="discovered",
                        is_new=True,
                        source_type="news",
                        discovered_via="tavily_news",
                        search_query=query,
                    )
                    found_properties.append(prop)
                    
            except Exception as e:
                print(f"Tavily error for '{query}': {e}")
                continue


scout_agent = ScoutAgent()

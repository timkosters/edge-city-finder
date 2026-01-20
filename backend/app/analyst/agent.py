import google.generativeai as genai
import httpx
from app.config import settings
from app.models import Property, VerificationResult
from typing import Optional
import json
import re
from datetime import datetime


class AnalystAgent:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    async def verify_url(self, url: str) -> tuple[bool, str]:
        """Check if URL is accessible and returns relevant content."""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.head(url)
                if response.status_code == 200:
                    return True, "URL accessible"
                elif response.status_code == 404:
                    return False, "URL not found (404)"
                else:
                    return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, f"Error accessing URL: {str(e)}"

    async def verify_property(self, prop: Property) -> Property:
        """
        Verify a property using Gemini to determine:
        - Is this an actual listing or just an article?
        - Is the property still available?
        - Does it meet our criteria?
        
        Updates and returns the property with verification results.
        """
        if not self.model:
            print("WARNING: Gemini API key not found. Skipping verification.")
            prop.funnel_stage = "qualified"  # Assume qualified if no verification
            return prop

        # First, check if URL is accessible
        url_accessible, url_status = await self.verify_url(prop.url)
        
        if not url_accessible:
            prop.verification_result = "invalid_url"
            prop.verification_reason = url_status
            prop.funnel_stage = "dismissed"
            prop.last_verified_at = datetime.now()
            return prop

        # Use Gemini to analyze the content
        prompt = f"""
You are a real estate analyst verifying property leads. Analyze this property and determine if it's a viable lead.

Property Title: {prop.title}
URL: {prop.url}
Source Type: {prop.source_type}
Description: {prop.description}

Answer these questions:
1. Is this an ACTUAL LISTING (property for sale/rent) or just a NEWS ARTICLE about a property?
2. Is the property AVAILABLE (can be purchased) or ALREADY SOLD/ACQUIRED by someone else?
3. What is the property type? (college, camp, resort, hotel, retreat center, other)
4. Any red flags that make this NOT a viable lead?

Consider these as NOT available:
- Properties being acquired by another institution (e.g., "bought by Vanderbilt")
- Properties already sold/under contract
- Properties that are closing but not selling the real estate
- Purely news coverage without sale information

Output JSON:
{{
    "is_listing": true/false,
    "is_available": true/false,
    "property_type": "college|camp|resort|hotel|retreat|other",
    "classification": "qualified|interesting|dismissed",
    "reason": "Brief explanation of classification",
    "extracted_price": "$X,XXX,XXX or null",
    "extracted_beds": number or null,
    "extracted_acreage": number or null
}}

Classification rules:
- "qualified": Is a listing AND is available
- "interesting": Is news/article about a property that MIGHT become available
- "dismissed": Already sold, not a property, or not relevant
"""
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text
            
            # Extract JSON from response
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                
                # Update property with verification results
                prop.verification_result = "available" if data.get("is_available") else "not_available"
                prop.verification_reason = data.get("reason", "")
                prop.funnel_stage = data.get("classification", "interesting")
                prop.last_verified_at = datetime.now()
                
                # Update extracted data if available
                if data.get("extracted_price"):
                    prop.price = data["extracted_price"]
                if data.get("extracted_beds"):
                    prop.bed_count = data["extracted_beds"]
                if data.get("extracted_acreage"):
                    prop.acreage = data["extracted_acreage"]
                    
        except Exception as e:
            print(f"Error verifying property {prop.title}: {e}")
            prop.verification_result = "error"
            prop.verification_reason = str(e)
            prop.funnel_stage = "interesting"  # Default to interesting on error
            prop.last_verified_at = datetime.now()
            
        return prop

    async def analyze_property(self, prop: Property) -> Property:
        """
        Performs a deep dive analysis on a verified property using Gemini.
        Generates a viability score and AI summary.
        """
        if not self.model:
            return prop

        prompt = f"""
You are an expert real estate analyst specializing in distressed assets (colleges, camps, resorts).
Analyze this verified property lead and provide a structured summary.

Property Title: {prop.title}
URL: {prop.url}
Location: {prop.location}
Price: {prop.price}
Description: {prop.description}
Verification: {prop.verification_reason}

Task:
1. Rate the "viability" score (0-100) for turning this into a co-living village for 200+ builders.
2. Write a one-sentence "punchy" summary of why this is interesting.
3. Extract any vital stats if apparent from context.

Consider:
- Capacity (200+ beds needed)
- Drive time to major airport (<2 hours ideal)
- Price point
- Infrastructure condition

Output JSON:
{{
    "score": <int 0-100>,
    "ai_summary": "<one compelling sentence>",
    "inferred_beds": <int or null>,
    "inferred_acreage": <float or null>
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text
            
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                
                prop.score = data.get("score", prop.score)
                prop.ai_summary = data.get("ai_summary", prop.ai_summary)
                if data.get("inferred_beds") and not prop.bed_count:
                    prop.bed_count = data.get("inferred_beds")
                if data.get("inferred_acreage") and not prop.acreage:
                    prop.acreage = data.get("inferred_acreage")
                    
        except Exception as e:
            print(f"Error analyzing property {prop.title}: {e}")
            
        return prop

    async def verify_and_analyze(self, prop: Property) -> Property:
        """Full pipeline: verify then analyze if qualified."""
        # First verify
        prop = await self.verify_property(prop)
        
        # Only analyze if qualified or interesting
        if prop.funnel_stage in ['qualified', 'interesting']:
            prop = await self.analyze_property(prop)
        
        return prop


analyst_agent = AnalystAgent()

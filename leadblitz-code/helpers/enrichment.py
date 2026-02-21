import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from typing import Dict, Optional

def get_openai_client():
    base_url = os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL")
    api_key = os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY")
    
    if not api_key or api_key == "_DUMMY_API_KEY_":
        api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key:
        if base_url:
            return OpenAI(api_key=api_key, base_url=base_url)
        else:
            return OpenAI(api_key=api_key)
    return None

def analyze_website(url: str) -> Dict:
    analysis = {
        "has_ssl": False,
        "is_responsive": False,
        "technology": "Unknown",
        "status_code": None,
        "error": None
    }
    
    if not url:
        analysis["error"] = "No website URL"
        return analysis
    
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    analysis["has_ssl"] = url.startswith("https://")
    
    try:
        response = requests.get(url, timeout=10, allow_redirects=True, verify=True)
        analysis["status_code"] = response.status_code
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
            analysis["is_responsive"] = viewport_meta is not None
            
            content = response.text.lower()
            if 'wp-content' in content or 'wordpress' in content:
                analysis["technology"] = "WordPress"
            elif 'wix.com' in content or 'wix-' in content:
                analysis["technology"] = "Wix"
            elif 'shopify' in content:
                analysis["technology"] = "Shopify"
            elif 'squarespace' in content:
                analysis["technology"] = "Squarespace"
            else:
                analysis["technology"] = "Custom/Other"
    
    except requests.exceptions.Timeout:
        analysis["error"] = "Timeout"
    except requests.exceptions.SSLError:
        analysis["error"] = "SSL Error"
    except Exception as e:
        analysis["error"] = str(e)[:100]
    
    return analysis


def score_lead_with_ai(lead_data: Dict, website_analysis: Dict) -> Dict:
    client = get_openai_client()
    if not client:
        return {
            "score": 50,
            "reasoning": {
                "total_score": 50,
                "website_quality": {"score": 15, "rationale": "Unable to analyze - AI service unavailable"},
                "digital_presence": {"score": 15, "rationale": "Unable to analyze - AI service unavailable"},
                "automation_opportunity": {"score": 20, "rationale": "Unable to analyze - AI service unavailable"},
                "summary": "Default score assigned due to AI service unavailability",
                "top_recommendation": "Configure OpenAI API to enable AI scoring"
            }
        }
    
    rating = lead_data.get('rating', 0)
    review_count = lead_data.get('review_count', 0)
    
    prompt = f"""Analyze this local business and score their current digital maturity. High scores = strong, well-optimized businesses. Low scores = weak digital presence needing improvement.

Business: {lead_data.get('name', 'Unknown')}
Website: {lead_data.get('website', 'None')}

Google Reviews:
- Rating: {rating:.1f}/5.0 stars
- Total Reviews: {review_count}

Website Analysis:
- Has SSL: {website_analysis.get('has_ssl', False)}
- Mobile Responsive: {website_analysis.get('is_responsive', False)}
- Technology: {website_analysis.get('technology', 'Unknown')}
- Status: {website_analysis.get('status_code', 'N/A')}
- Error: {website_analysis.get('error', 'None')}

Provide a JSON response with this exact structure:
{{
  "total_score": <number 0-100>,
  "website_quality": {{
    "score": <number 0-30>,
    "rationale": "<brief explanation>"
  }},
  "digital_presence": {{
    "score": <number 0-30>,
    "rationale": "<brief explanation covering reviews and online reputation>"
  }},
  "automation_opportunity": {{
    "score": <number 0-40>,
    "rationale": "<brief explanation of current automation level and potential>"
  }},
  "summary": "<2-3 sentence overall assessment>",
  "top_recommendation": "<single actionable recommendation for improvement>"
}}

CRITICAL SCORING RUBRICS (HIGH SCORE = HIGH QUALITY):

⚠️ STRICT LIMITS - DO NOT EXCEED THESE MAXIMUM SCORES ⚠️

Website Quality (0-30 points MAXIMUM = current website quality):
- Modern, professional site (SSL, responsive, fast, good UX): 25-30 points (excellent!)
- Decent site with minor issues (has SSL, mostly responsive): 15-24 points (good)
- Basic/outdated site or broken/no website: 0-14 points (needs work)
- MAXIMUM ALLOWED: 30 points (NEVER score above 30)

Digital Presence (0-30 points MAXIMUM = current online reputation):
- Strong reviews (50+ reviews, 4.5+ rating): 25-30 points (excellent reputation!)
- Some reviews (10-50) with decent rating: 15-24 points (good presence)
- No reviews or very few (<10 reviews): 0-14 points (weak presence)
- MAXIMUM ALLOWED: 30 points (NEVER score above 30)

Automation & Technology (0-40 points MAXIMUM = current automation level):
- Advanced AI tools, chatbots, automated workflows already in use: 30-40 points (highly automated!)
- Some automation but gaps remain: 15-29 points (moderate automation)
- Manual processes, no chatbot, missing lead capture: 0-14 points (low automation)
- MAXIMUM ALLOWED: 40 points (NEVER score above 40)

TOTAL SCORE INTERPRETATION:
- 80-100: EXCELLENT - strong digital presence, well-optimized
- 50-79: GOOD - decent foundation with room for improvement
- 0-49: NEEDS IMPROVEMENT - weak digital presence, significant opportunity for growth"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a lead scoring expert. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        if content:
            import json
            reasoning = json.loads(content)
            
            # Validate and cap component scores at their maximums
            if "website_quality" in reasoning and isinstance(reasoning["website_quality"], dict):
                score = reasoning["website_quality"].get("score", 0)
                reasoning["website_quality"]["score"] = max(0, min(30, score))
            
            if "digital_presence" in reasoning and isinstance(reasoning["digital_presence"], dict):
                score = reasoning["digital_presence"].get("score", 0)
                reasoning["digital_presence"]["score"] = max(0, min(30, score))
            
            if "automation_opportunity" in reasoning and isinstance(reasoning["automation_opportunity"], dict):
                score = reasoning["automation_opportunity"].get("score", 0)
                reasoning["automation_opportunity"]["score"] = max(0, min(40, score))
            
            # Calculate capped total from components
            total_score = (
                reasoning.get("website_quality", {}).get("score", 0) +
                reasoning.get("digital_presence", {}).get("score", 0) +
                reasoning.get("automation_opportunity", {}).get("score", 0)
            )
            total_score = max(0, min(100, total_score))
            reasoning["total_score"] = total_score
            
            return {
                "score": total_score,
                "reasoning": reasoning
            }
        else:
            raise ValueError("Empty response from AI")
    
    except Exception as e:
        print(f"Error scoring lead with AI: {e}")
        return {
            "score": 50,
            "reasoning": {
                "total_score": 50,
                "website_quality": {"score": 15, "rationale": "Error during analysis"},
                "digital_presence": {"score": 15, "rationale": "Error during analysis"},
                "automation_opportunity": {"score": 20, "rationale": "Error during analysis"},
                "summary": f"Default score assigned due to error: {str(e)[:100]}",
                "top_recommendation": "Review lead manually"
            }
        }

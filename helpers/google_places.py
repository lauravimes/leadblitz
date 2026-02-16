import os
import time
import requests
import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

BASE_URL = "https://maps.googleapis.com/maps/api/place"

def _get_api_key():
    key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    return key

def search_places(business_type: str, location: str, limit: int = 20, page_token: Optional[str] = None) -> Dict:
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY not configured. Please add it to your environment secrets.")
    
    limit = min(limit, 20)
    
    query = f"{business_type} in {location}"
    
    url = f"{BASE_URL}/textsearch/json"
    params = {
        "query": query,
        "key": api_key
    }
    
    if page_token:
        params["pagetoken"] = page_token
    
    try:
        print(f"[PLACES] Text search request: query='{query}', limit={limit}")
        t0 = time.time()
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        elapsed = time.time() - t0
        
        status = data.get("status")
        print(f"[PLACES] Text search response: status={status}, elapsed={elapsed:.1f}s")
        
        if status == "REQUEST_DENIED":
            error_msg = data.get("error_message", "API key is invalid or restricted")
            logger.error(f"Google Places API REQUEST_DENIED - Check API key configuration in Secrets")
            raise ValueError(f"Google Places API error: {error_msg}. Please check that GOOGLE_MAPS_API_KEY is set correctly in your production Secrets.")
        elif status == "OVER_QUERY_LIMIT":
            logger.error("Google Places API OVER_QUERY_LIMIT - Check billing settings")
            raise ValueError("Google Places API quota exceeded. Please check your billing settings.")
        elif status == "INVALID_REQUEST":
            logger.error(f"Google Places API INVALID_REQUEST for query: {query}")
            raise ValueError("Invalid search request. Please check your search parameters.")
        elif status == "ZERO_RESULTS":
            logger.info(f"Google Places API returned ZERO_RESULTS for query: {query}")
            return {"places": [], "next_page_token": None}
        elif status != "OK":
            logger.error(f"Google Places API returned unexpected status: {status}")
            raise ValueError(f"Google Places API returned status: {status}")
        
        results = data.get("results", [])[:limit]
        next_page_token = data.get("next_page_token")
        
        place_ids = [r.get("place_id") for r in results if r.get("place_id")]
        print(f"[PLACES] Fetching details for {len(place_ids)} places in parallel...")
        
        t1 = time.time()
        DETAILS_DEADLINE = 20.0
        places = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_id = {executor.submit(get_place_details, pid, api_key): pid for pid in place_ids}
            try:
                for future in as_completed(future_to_id, timeout=DETAILS_DEADLINE):
                    try:
                        remaining = max(1.0, DETAILS_DEADLINE - (time.time() - t1))
                        details = future.result(timeout=remaining)
                        if details:
                            places.append(details)
                    except Exception as e:
                        pid = future_to_id[future]
                        logger.warning(f"Place details failed for {pid}: {e}")
            except TimeoutError:
                print(f"[PLACES] Details deadline exceeded after {time.time()-t1:.1f}s, returning {len(places)} partial results")
        
        details_elapsed = time.time() - t1
        total_elapsed = time.time() - t0
        print(f"[PLACES] Details fetched in {details_elapsed:.1f}s, total search: {total_elapsed:.1f}s, got {len(places)} places")
        
        return {
            "places": places,
            "next_page_token": next_page_token
        }
    
    except requests.exceptions.Timeout:
        logger.error("Google Places API request timed out")
        raise ValueError("Google Places API request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error calling Google Places API: {type(e).__name__}")
        raise ValueError("Network error connecting to Google Places API. Please try again.")
    except ValueError:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error searching places: {type(e).__name__}")
        raise ValueError("An unexpected error occurred while searching. Please try again.")


def get_place_details(place_id: str, api_key: str = None) -> Optional[Dict]:
    if not api_key:
        api_key = _get_api_key()
    if not api_key:
        return None
    
    url = f"{BASE_URL}/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,formatted_phone_number,international_phone_number,website,rating,user_ratings_total",
        "key": api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        status = data.get("status")
        if status != "OK":
            logger.warning(f"Place details API returned status: {status} for place_id: {place_id}")
            return None
        
        result = data.get("result", {})
        
        return {
            "name": result.get("name", ""),
            "address": result.get("formatted_address", ""),
            "phone": result.get("formatted_phone_number") or result.get("international_phone_number", ""),
            "email": "",
            "website": result.get("website", ""),
            "rating": result.get("rating", 0),
            "review_count": result.get("user_ratings_total", 0)
        }
    
    except Exception as e:
        logger.warning(f"Error getting place details for {place_id}: {type(e).__name__}")
        return None

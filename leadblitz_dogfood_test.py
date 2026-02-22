#!/usr/bin/env python3
"""
LeadBlitz Dogfood Test - Steven's Request
Testing 20 leads each in Oxford, England; Baltimore; and Amsterdam
"""

import requests
import json
import time

# Laura's LeadBlitz account (1000 credits available)
LOGIN_URL = "https://leadblitz.co/api/auth/login"
SEARCH_URL = "https://leadblitz.co/api/search"

def login_to_leadblitz():
    """Login and get session cookie"""
    login_data = {
        "email": "laura.vimes@icloud.com",
        "password": "NewTest2026!"
    }
    
    session = requests.Session()
    response = session.post(LOGIN_URL, json=login_data)
    
    if response.status_code == 200:
        print("✅ Login successful")
        return session
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def search_businesses(session, location, limit=20):
    """Search for businesses in a location"""
    search_data = {
        "business_type": "web design agency",  # Target market for LeadBlitz
        "location": location,
        "limit": limit
    }
    
    print(f"\n🔍 Searching for {limit} web design agencies in {location}...")
    
    response = session.post(SEARCH_URL, json=search_data)
    
    if response.status_code == 200:
        data = response.json()
        businesses = data.get('businesses', [])
        print(f"✅ Found {len(businesses)} businesses")
        
        # Log key details for first few results
        for i, biz in enumerate(businesses[:5]):
            print(f"  {i+1}. {biz.get('name', 'Unknown')} - Score: {biz.get('ai_score', 'Not scored')}/100")
            
        return businesses
    else:
        print(f"❌ Search failed: {response.status_code}")
        print(response.text)
        return []

def main():
    """Run dogfood test for 3 cities"""
    print("🐕 LeadBlitz Dogfood Test - Testing Current Live System")
    print("=" * 60)
    
    # Login
    session = login_to_leadblitz()
    if not session:
        return
    
    # Test cities
    cities = [
        "Oxford, England",
        "Baltimore, MD",
        "Amsterdam, Netherlands"
    ]
    
    all_results = {}
    
    for city in cities:
        results = search_businesses(session, city, 20)
        all_results[city] = results
        time.sleep(2)  # Be nice to the API
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DOGFOOD TEST SUMMARY")
    print("=" * 60)
    
    total_businesses = 0
    total_scored = 0
    score_sum = 0
    
    for city, businesses in all_results.items():
        scored_count = sum(1 for b in businesses if b.get('ai_score'))
        avg_score = sum(b.get('ai_score', 0) for b in businesses if b.get('ai_score'))
        if scored_count > 0:
            avg_score = avg_score / scored_count
            
        print(f"\n{city}:")
        print(f"  📍 Total found: {len(businesses)}")
        print(f"  🤖 Scored: {scored_count}")
        print(f"  📈 Avg score: {avg_score:.1f}/100" if scored_count > 0 else "  📈 Avg score: N/A")
        
        total_businesses += len(businesses)
        total_scored += scored_count
        if scored_count > 0:
            score_sum += avg_score * scored_count
    
    if total_scored > 0:
        overall_avg = score_sum / total_scored
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"  Total businesses: {total_businesses}")
        print(f"  Total scored: {total_scored}")
        print(f"  Overall avg score: {overall_avg:.1f}/100")
        print(f"  Scoring rate: {total_scored/total_businesses*100:.1f}%")
    
    print("\n🔧 This is BEFORE the brotli compression fix.")
    print("   After deployment, scores should improve significantly!")

if __name__ == "__main__":
    main()
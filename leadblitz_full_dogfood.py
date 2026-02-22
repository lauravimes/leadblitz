#!/usr/bin/env python3
"""
Full LeadBlitz Dogfood Test - Before Brotli Fix
Testing 20 leads each in Oxford, England; Baltimore; and Amsterdam
"""

import requests
import json
import time

def test_leadblitz_full():
    """Full dogfood test for 3 cities"""
    
    print("🐕 LeadBlitz Dogfood Test - BEFORE Brotli Fix")
    print("=" * 60)
    
    # Login
    session = requests.Session()
    login_data = {
        "email": "laura.vimes@icloud.com", 
        "password": "NewTest2026!"
    }
    
    print("🔐 Logging in...")
    response = session.post("https://leadblitz.co/api/auth/login", json=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return
    
    print("✅ Login successful\n")
    
    # Test cities
    cities = [
        "Oxford, England",
        "Baltimore, MD", 
        "Amsterdam, Netherlands"
    ]
    
    all_results = {}
    
    for city in cities:
        search_data = {
            "business_type": "web design agency",
            "location": city,
            "limit": 20
        }
        
        print(f"🔍 Searching for web design agencies in {city}...")
        
        try:
            response = session.post("https://leadblitz.co/api/search", json=search_data, timeout=90)
            
            if response.status_code == 200:
                data = response.json()
                leads = data.get('leads', [])
                all_results[city] = leads
                
                scored_count = sum(1 for lead in leads if lead.get('ai_score'))
                print(f"✅ Found {len(leads)} leads ({scored_count} scored)")
                
                # Show first 3 as sample
                for i, lead in enumerate(leads[:3]):
                    name = lead.get('name', 'Unknown')[:40]
                    score = lead.get('ai_score', 'Not scored')
                    website = 'YES' if lead.get('website') else 'NO'
                    print(f"  {i+1}. {name} - Score: {score}/100 - Website: {website}")
                    
            else:
                print(f"❌ Search failed for {city}: {response.status_code}")
                all_results[city] = []
                
        except Exception as e:
            print(f"❌ Error searching {city}: {str(e)}")
            all_results[city] = []
            
        print()
        time.sleep(3)  # Rate limiting
    
    # Summary
    print("=" * 60)
    print("📊 DOGFOOD TEST RESULTS - BEFORE BROTLI FIX")
    print("=" * 60)
    
    total_leads = 0
    total_with_websites = 0
    total_scored = 0
    total_score_sum = 0
    
    for city, leads in all_results.items():
        with_websites = sum(1 for lead in leads if lead.get('website'))
        scored = sum(1 for lead in leads if lead.get('ai_score'))
        score_sum = sum(lead.get('ai_score', 0) for lead in leads if lead.get('ai_score'))
        avg_score = score_sum / scored if scored > 0 else 0
        
        print(f"\n🌍 {city}:")
        print(f"  📍 Total leads: {len(leads)}")
        print(f"  🌐 With websites: {with_websites}")
        print(f"  🤖 AI scored: {scored}")
        print(f"  📈 Avg score: {avg_score:.1f}/100" if scored > 0 else "  📈 Avg score: N/A")
        print(f"  🎯 Scoring rate: {scored/with_websites*100:.1f}%" if with_websites > 0 else "  🎯 Scoring rate: N/A")
        
        total_leads += len(leads)
        total_with_websites += with_websites  
        total_scored += scored
        total_score_sum += score_sum
    
    print(f"\n🎯 OVERALL BASELINE (Before Brotli Fix):")
    print(f"  Total leads found: {total_leads}")
    print(f"  Leads with websites: {total_with_websites}")
    print(f"  Leads AI scored: {total_scored}")
    print(f"  Overall scoring rate: {total_scored/total_with_websites*100:.1f}%" if total_with_websites > 0 else "  Overall scoring rate: 0%")
    
    if total_scored > 0:
        overall_avg = total_score_sum / total_scored
        print(f"  Overall avg score: {overall_avg:.1f}/100")
    else:
        print(f"  Overall avg score: N/A (no leads scored!)")
    
    print(f"\n🔧 EXPECTED AFTER BROTLI FIX:")
    print(f"  - Scoring rate should jump from {total_scored/total_with_websites*100:.1f}% to ~80-90%")
    print(f"  - Average scores should increase significantly")
    print(f"  - More websites will be properly analyzed")
    
    return all_results

if __name__ == "__main__":
    results = test_leadblitz_full()
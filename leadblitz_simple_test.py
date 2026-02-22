#!/usr/bin/env python3
"""
Simple LeadBlitz Test - One City
"""

import requests
import json

def test_leadblitz():
    """Simple test of LeadBlitz API"""
    
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
        print(response.text)
        return
    
    print("✅ Login successful")
    
    # Search for 5 businesses in Oxford as a test
    search_data = {
        "business_type": "web design agency",
        "location": "Oxford, England",
        "limit": 5
    }
    
    print("🔍 Searching for 5 web design agencies in Oxford...")
    response = session.post("https://leadblitz.co/api/search", json=search_data, timeout=60)
    
    if response.status_code == 200:
        data = response.json()
        leads = data.get('leads', [])
        print(f"✅ Found {len(leads)} leads")
        
        for i, lead in enumerate(leads):
            name = lead.get('name', 'Unknown')
            score = lead.get('ai_score', 'Not scored')
            website = lead.get('website', 'No website')
            print(f"  {i+1}. {name} - Score: {score}/100 - {website}")
            
    else:
        print(f"❌ Search failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_leadblitz()
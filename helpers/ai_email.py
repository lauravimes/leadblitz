import os
from openai import OpenAI
from typing import Dict

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

def generate_personalized_email(lead_data: Dict, base_pitch: str) -> Dict[str, str]:
    client = get_openai_client()
    
    business_name = lead_data.get('name', 'your business')
    
    if not client:
        raise ValueError("OpenAI API key is not configured. Please add your API key in Settings.")
    
    website = lead_data.get('website', 'no website')
    score = lead_data.get('score', 0)
    
    contact_name = lead_data.get('contact_name', '')
    first_name = contact_name.split()[0] if contact_name and contact_name.strip() else ''
    
    greeting_instruction = f'Start with "Hi {first_name},"' if first_name else 'Start with just "Hi,"'
    
    prompt = f"""Write a personalized, friendly cold email to a local business.

Business Details:
- Name: {business_name}
- Website: {website}
- Lead Score: {score}/100 (indicates opportunity level)

Your Pitch: {base_pitch}

Requirements:
1. Keep it under 150 words
2. Be specific to THIS business
3. Reference their business name naturally
4. Professional but conversational tone
5. Clear call-to-action
6. NO pushy sales language
7. Make it feel genuine, not templated
8. {greeting_instruction}

Return ONLY the email body (no subject line)."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at writing personalized, non-spammy cold outreach emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        content = response.choices[0].message.content
        body = content.strip() if content else f"Hi,\n\n{base_pitch}\n\nBest regards"
        
        subject_prompt = f"Write a short, specific email subject line (max 8 words) for an email to {business_name} about: {base_pitch}. Return ONLY the subject line, no quotes or punctuation."
        
        subject_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You write compelling email subject lines."},
                {"role": "user", "content": subject_prompt}
            ],
            temperature=0.7,
            max_tokens=20
        )
        
        subject_content = subject_response.choices[0].message.content
        subject = subject_content.strip().strip('"\'') if subject_content else f"Opportunity for {business_name}"
        
        return {
            "subject": subject,
            "body": body
        }
    
    except Exception as e:
        print(f"Error generating personalized email: {e}")
        raise

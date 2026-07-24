import os
import json
from groq import Groq

def classify_message(text):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {
            "severity": "safe",
            "confidence": 0,
            "is_bullying": False,
            "reason": "No API key configured",
            "suggested_reply": ""
        }
        
    client = Groq(api_key=api_key)
    
    prompt = f"""Classify this message for cyberbullying. Return ONLY JSON:
{{"severity": "safe|flagged|high", "confidence": 0-100, "is_bullying": true|false, "reason": "", "suggested_reply": ""}}

Message: "{text}"
"""
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a cyberbullying classification API. Output ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=150
        )
        
        response_text = completion.choices[0].message.content.strip()
        # Clean up any potential markdown formatting from the response
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        return json.loads(response_text)
    except Exception as e:
        print(f"Groq API Error: {e}")
        return {
            "severity": "safe",
            "confidence": 0,
            "is_bullying": False,
            "reason": "Error calling API",
            "suggested_reply": ""
        }

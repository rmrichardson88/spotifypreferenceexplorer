import os
import requests
import streamlit as st
import time

def generate_commentary(top_attributes):
    """Generate insightful commentary on playlist audio features using Groq LLM API."""
    try:
        api_key = st.secrets.get("GROQ_API_KEY")
        if not api_key:
            st.warning("⚠️ Groq API key not found. Using placeholder commentary.")
            return "⚠️ AI Commentary not available (Groq API key not configured). Configure the GROQ_API_KEY in your Streamlit secrets to enable this feature."
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        attributes_str = "".join([f"- {attr}: {value:.3f}\n" for attr, value in top_attributes.items()])
        
        prompt = f"""Analyze these average Spotify audio features from a playlist:

{attributes_str}

Based on these audio features, what kind of music is in this playlist? 
Write a short, engaging paragraph (3-5 sentences) with insights about:
1. The overall mood and energy of this music
2. What activities this music would be good for
3. What music genres likely appear in this playlist

Be specific, analytical, and insightful rather than generic.
"""

        body = {
            "model": "mistral-saba-24b",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 300
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions", 
                    headers=headers, 
                    json=body,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    st.warning(f"API call failed, retrying ({attempt+1}/{max_retries})...")
                    time.sleep(2)
                else:
                    st.error(f"Failed to generate commentary after {max_retries} attempts: {str(e)}")
                    return "Could not generate AI commentary. Please try again later."
    
    except Exception as e:
        st.error(f"Error generating commentary: {str(e)}")
        return "Could not generate AI commentary due to an error."

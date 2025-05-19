import os
import requests

def generate_commentary(top_attributes):
    api_key = os.getenv("GROQ_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    prompt = f"""
    Analyze these average Spotify audio features from a trending playlist:

    {top_attributes.to_string()}

    Write a short paragraph with insight into what kind of music is trending. Be concise, but insightful.
    """

    body = {
        "model": "mistral-saba-24b",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

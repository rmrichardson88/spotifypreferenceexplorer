# === README.md ===
# AI Music Analyst

[Streamlit Cloud](https://spotifypreferenceexplorer.streamlit.app/)
This Streamlit app analyzes a Spotify playlist and provides audio feature insights with LLM commentary using Groq + Mistral.

## Setup

1. Clone the repo
2. Create a `.env` or set environment variables:
   ```bash
   export SPOTIFY_CLIENT_ID=your_client_id
   export SPOTIFY_CLIENT_SECRET=your_client_secret
   export GROQ_API_KEY=your_groq_key
   ```
3. Run the app:
   ```bash
   streamlit run streamlit_app.py
   ```

## Deployment

Use [Streamlit Cloud](https://streamlit.io/cloud), and add your secrets to `.streamlit/secrets.toml`.

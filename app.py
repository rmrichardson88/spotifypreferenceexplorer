import streamlit as st
from spotify_client import get_playlist_audio_features
from groq_agent import generate_commentary

st.set_page_config(page_title="AI Music Analyst", layout="centered")
st.title("🎧 AI Music Analyst: Playlist Explorer")

playlist_url = st.text_input("Enter a Spotify playlist URL (e.g. Today's Top Hits):")

if playlist_url:
    with st.spinner("Fetching playlist data..."):
        try:
            df, top_attributes = get_playlist_audio_features(playlist_url)
            st.subheader("Top Audio Attributes")
            st.bar_chart(top_attributes)

            st.subheader("🤖 LLM Commentary")
            commentary = generate_commentary(top_attributes)
            st.markdown(commentary)
        except Exception as e:
            st.error(f"Failed to load playlist data: {e}")

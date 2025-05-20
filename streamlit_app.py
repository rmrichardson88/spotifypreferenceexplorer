import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotify_client import get_playlist_audio_features
from groq_agent import generate_commentary

SPOTIFY_CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]


def get_spotify_client():
    auth_manager = SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
    return spotipy.Spotify(auth_manager=auth_manager)


st.set_page_config(page_title="AI Music Analyst", layout="centered")
st.title("\U0001F3B7 AI Music Analyst: Playlist Explorer")

sp = get_spotify_client()

playlist_url = st.text_input("Enter a Spotify playlist URL (e.g. Today's Top Hits):")
if playlist_url:
    with st.spinner("Fetching playlist data..."):
        try:
            df, top_attributes = get_playlist_audio_features(sp, playlist_url)

            st.subheader("Top Audio Attributes")
            st.bar_chart(top_attributes)

            st.subheader("\U0001F916 LLM Commentary")
            commentary = generate_commentary(top_attributes)
            st.markdown(commentary)

        except Exception as e:
            import traceback
            st.error(f"Failed to load playlist data: {e}")
            st.text(traceback.format_exc())

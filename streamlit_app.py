import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotify_client import get_playlist_audio_features
from groq_agent import generate_commentary
import os
from urllib.parse import urlparse

scope = "playlist-read-private playlist-read-collaborative"
redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

def get_spotify_client():
    sp_oauth = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=redirect_uri,
        scope=scope,
        cache_path=None
    )

    if "token_info" not in st.session_state:
        auth_url = sp_oauth.get_authorize_url()
        st.markdown(f"[Click here to log in to Spotify]({auth_url})")

        code = st.query_params.get("code")
        if code:
            code = code[0]
            token_info = sp_oauth.get_access_token(code)
            st.session_state["token_info"] = token_info
            st.experimental_rerun()
        return None

    token_info = st.session_state["token_info"]

    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
        st.session_state["token_info"] = token_info

    sp = spotipy.Spotify(auth=token_info["access_token"])
    return sp

st.set_page_config(page_title="AI Music Analyst", layout="centered")
st.title("\U0001F3B7 AI Music Analyst: Playlist Explorer")

sp = get_spotify_client()

if sp:
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
else:
    st.info("Please log in to Spotify to continue.")

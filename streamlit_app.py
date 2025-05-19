import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotify_client import get_playlist_audio_features
from groq_agent import generate_commentary
import os
from urllib.parse import urlparse


SPOTIFY_CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
SPOTIFY_CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["SPOTIPY_REDIRECT_URI"]
SCOPE = "playlist-read-private playlist-read-collaborative"

def get_spotify_client():
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
    )

    token_info = st.session_state.get("token_info", None)

    if not token_info:
        code = st.experimental_get_query_params().get("code")
        if code:
            code = code[0]
            try:
                access_token = sp_oauth.get_access_token(code, as_dict=False)
                token_info = sp_oauth.cache_handler.get_cached_token()
                st.session_state["token_info"] = token_info
                st.experimental_set_query_params()
                st.experimental_rerun()
            except SpotifyOauthError as e:
                st.error(f"Spotify OAuth error: {e}")
                return None
        else:
            auth_url = sp_oauth.get_authorize_url()
            st.markdown(f"[Log in with Spotify]({auth_url})")
            return None

    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        st.session_state["token_info"] = token_info

    access_token = token_info["access_token"]
    return spotipy.Spotify(auth=access_token)

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

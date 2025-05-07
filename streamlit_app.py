import streamlit as st
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

# --- PAGE CONFIG ---
st.set_page_config(page_title="Spotify Preference Explorer", layout="wide")

# --- AUTHENTICATION SETUP ---

from spotipy.cache_handler import CacheHandler

class StreamlitOAuthCache(CacheHandler):
    def __init__(self):
        self.token_info = None

    def get_cached_token(self):
        return self.token_info

    def save_token_to_cache(self, token_info):
        self.token_info = token_info


# Initialize cache handler
cache_handler = StreamlitOAuthCache()

# Set up Spotify OAuth
auth_manager = SpotifyOAuth(
    client_id=st.secrets["SPOTIPY_CLIENT_ID"],
    client_secret=st.secrets["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=st.secrets["SPOTIPY_REDIRECT_URI"],
    scope="user-library-read playlist-read-private user-top-read",
    cache_handler=cache_handler,
    show_dialog=True,
)

# Handle authentication and token management
if "token_info" not in st.session_state:
    code = st.experimental_set_query_params().get("code", [None])[0]

    if code:
        token_info = auth_manager.get_access_token(code, as_dict=True)
        if token_info:
            st.session_state.token_info = token_info
            st.experimental_set_query_params()  # Clear code from URL
        else:
            st.error("Authentication failed. Please try again.")
            st.stop()
    else:
        auth_url = auth_manager.get_authorize_url()
        st.markdown(f"### [Click here to authenticate with Spotify]({auth_url})")
        st.stop()

# Token refresh logic
token_info = st.session_state.token_info
if auth_manager.is_token_expired(token_info):
    token_info = auth_manager.refresh_access_token(token_info['refresh_token'])
    st.session_state.token_info = token_info

# Initialize Spotipy client
sp = Spotify(auth=token_info["access_token"])

# --- MAIN APP CONTENT ---

st.title("🎧 Spotify Preference Explorer")

# Fetch and display user's top tracks
with st.spinner("Fetching your top tracks..."):
    top_tracks = sp.current_user_top_tracks(limit=10, time_range="short_term")

if top_tracks["items"]:
    st.subheader("Your Top 10 Tracks (Last 4 Weeks)")
    for idx, item in enumerate(top_tracks["items"], start=1):
        st.markdown(f"**{idx}. {item['name']}** by {', '.join(artist['name'] for artist in item['artists'])}")
else:
    st.warning("No top tracks found.")

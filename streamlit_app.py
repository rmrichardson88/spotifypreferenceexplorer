import os
import time
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import plotly.express as px

# --- Page config ---
st.set_page_config(page_title="Spotify Explorer", page_icon="🎧")

# --- Create cache directory ---
CACHE_DIR = ".streamlit_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# --- Spotify OAuth Setup (One-Time Initialization) ---
if "auth_manager" not in st.session_state:
    st.session_state.auth_manager = SpotifyOAuth(
        client_id=st.secrets["SPOTIPY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIPY_CLIENT_SECRET"],
        redirect_uri=st.secrets["SPOTIPY_REDIRECT_URI"],  # Must match Spotify dashboard
        scope="user-top-read",
        cache_path=os.path.join(CACHE_DIR, "spotify_token_cache")
    )

auth_manager = st.session_state.auth_manager

# --- Helper: Get Valid Token ---
def get_valid_token():
    try:
        token_info = auth_manager.get_cached_token()
        if token_info is None or auth_manager.is_token_expired(token_info):
            token_info = auth_manager.get_access_token(as_dict=True)
        return token_info
    except Exception as e:
        st.error(f"Auth error: {e}")
        return None

# --- Token Handling ---
if "token_info" not in st.session_state:
    st.session_state.token_info = get_valid_token()

# --- Sidebar: Settings ---
with st.sidebar:
    st.title("Settings")

    # Sign Out Button
    if st.button("🔁 Sign Out and Reauthenticate"):
        st.session_state.clear()
        cache_file = os.path.join(CACHE_DIR, "spotify_token_cache")
        if os.path.exists(cache_file):
            os.remove(cache_file)
        st.success("Signed out. Reloading...")
        st.rerun()

    # Debug Info
    with st.expander("🧪 Auth Debug", expanded=False):
        st.write("**Token Cached:**", auth_manager.get_cached_token() is not None)
        st.write("**Token Expires At:**", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(
            st.session_state.token_info.get("expires_at", 0))))
        st.write("**Access Token:**", st.session_state.token_info.get("access_token", "Not found"))

# --- Auth Check ---
if st.session_state.token_info is None:
    auth_url = auth_manager.get_authorize_url()
    st.markdown(f"## 🔐 [Click here to log in to Spotify]({auth_url})")
    st.info("After logging in, return to this page to continue.")
    st.stop()

# --- Initialize Spotify Client ---
sp = spotipy.Spotify(auth=st.session_state.token_info["access_token"])

# --- Main App UI ---
st.title("🎧 Spotify Audio Feature Explorer")
st.markdown("Explore your top tracks from Spotify.")

# Time range selector
time_range = st.sidebar.radio(
    "Time Range",
    options=["short_term", "medium_term", "long_term"],
    format_func=lambda x: {
        "short_term": "Last 4 Weeks",
        "medium_term": "Last 6 Months",
        "long_term": "All Time"
    }[x]
)

# Get top tracks
with st.spinner("Loading top tracks..."):
    try:
        top_tracks = sp.current_user_top_tracks(limit=20, time_range=time_range)
    except spotipy.exceptions.SpotifyException:
        st.error("Authentication failed. Please try signing out and logging in again.")
        st.stop()

# Handle no results
if not top_tracks or not top_tracks.get("items"):
    st.warning("No top tracks found. Try listening to some music first!")
    st.stop()

# Parse top track data
track_data = []
for item in top_tracks["items"]:
    features = sp.audio_features([item["id"]])[0]
    track_data.append({
        "Track Name": item["name"],
        "Artist": item["artists"][0]["name"],
        "Danceability": features["danceability"],
        "Energy": features["energy"],
        "Valence": features["valence"],
        "Tempo": features["tempo"],
        "Popularity": item["popularity"],
        "Track ID": item["id"]
    })

# Create DataFrame
df = pd.DataFrame(track_data)

# Track selector
selected_track_name = st.selectbox("🎵 Select a track to highlight", df["Track Name"])
selected_track_id = df[df["Track Name"] == selected_track_name]["Track ID"].values[0]

# Feature scatterplot
st.subheader("🔍 Audio Feature Scatterplot")
x_feature = st.selectbox("X-axis", ["Danceability", "Energy", "Valence", "Tempo", "Popularity"], index=0)
y_feature = st.selectbox("Y-axis", ["Energy", "Valence", "Danceability", "Tempo", "Popularity"], index=1)

# Plot
fig = px.scatter(
    df,
    x=x_feature,
    y=y_feature,
    color="Artist",
    hover_name="Track Name",
    size="Popularity",
    title=f"{x_feature} vs {y_feature}",
    template="plotly_dark"
)

# Highlight selected track
selected_row = df[df["Track Name"] == selected_track_name].iloc[0]
fig.add_scatter(
    x=[selected_row[x_feature]],
    y=[selected_row[y_feature]],
    mode="markers+text",
    marker=dict(color="red", size=15, line=dict(color="white", width=2)),
    text=["🎯"],
    textposition="top center",
    name="Selected Track"
)

st.plotly_chart(fig, use_container_width=True)

# Optional: Raw data
with st.expander("📋 View Raw Data"):
    st.dataframe(df.drop(columns=["Track ID"]))

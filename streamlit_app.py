import os
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import plotly.express as px

# --- Page config ---
st.set_page_config(page_title="Spotify Explorer", page_icon="🎧")

# --- Debug: Show cache path ---
st.sidebar.markdown(f"**Cache Path:** `{os.path.abspath('.cache')}`")

# --- Spotify OAuth setup ---
auth_manager = SpotifyOAuth(
    client_id=st.secrets["SPOTIPY_CLIENT_ID"],
    client_secret=st.secrets["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=st.secrets["SPOTIPY_REDIRECT_URI"],  # Must exactly match Spotify dashboard
    scope="user-top-read",
    cache_path=".cache",
    show_dialog=True  # Force Spotify to re-prompt for login
)

# --- Sidebar: Logout ---
with st.sidebar:
    st.title("Settings")
    if st.button("🔁 Sign Out and Reauthenticate"):
        # Remove all .cache* files
        for f in os.listdir():
            if f.startswith(".cache"):
                os.remove(f)
        st.success("Cache cleared. Reloading...")
        st.rerun()

# --- Authentication Check ---
token_info = auth_manager.get_cached_token()
st.sidebar.markdown("### Token Info")
st.sidebar.json(token_info)  # Debug display, optional

# If no token is cached, prompt for login
if not token_info:
    auth_url = auth_manager.get_authorize_url()
    st.markdown(f"## 🔐 [Click here to log in to Spotify]({auth_url})")
    st.info("After logging in, return to this page to continue.")
    st.stop()

# --- Initialize Spotify client with token ---
sp = spotipy.Spotify(auth_manager=auth_manager)

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

# Handle case with no top tracks
if not top_tracks or not top_tracks.get("items"):
    st.warning("No top tracks found. Try listening to some music first!")
    st.stop()

# Parse top track data
track_data = []
for idx, item in enumerate(top_tracks["items"]):
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

# Convert to DataFrame
df = pd.DataFrame(track_data)

# Track selection
selected_track_name = st.selectbox("🎵 Select a track to highlight", df["Track Name"])
selected_track_id = df[df["Track Name"] == selected_track_name]["Track ID"].values[0]

# Feature scatterplot
st.subheader("🔍 Audio Feature Scatterplot")
x_feature = st.selectbox("X-axis", ["Danceability", "Energy", "Valence", "Tempo", "Popularity"], index=0)
y_feature = st.selectbox("Y-axis", ["Energy", "Valence", "Danceability", "Tempo", "Popularity"], index=1)

# Create scatterplot
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

# Show scatterplot
st.plotly_chart(fig, use_container_width=True)

# Optional: raw data table
with st.expander("📋 View Raw Data"):
    st.dataframe(df.drop(columns=["Track ID"]))

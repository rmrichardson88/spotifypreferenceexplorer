import os
import re
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import plotly.express as px

# --- Page config ---
st.set_page_config(page_title="Spotify Explorer", page_icon="🎧")

# --- Helper: Extract playlist ID from URL or raw input ---
def extract_playlist_id(input_str):
    match = re.search(r"(playlist/)?([a-zA-Z0-9]{22})", input_str)
    if match:
        return match.group(2)
    return None

# --- Spotify OAuth setup ---
auth_manager = SpotifyOAuth(
    client_id=st.secrets["SPOTIPY_CLIENT_ID"],
    client_secret=st.secrets["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=st.secrets["SPOTIPY_REDIRECT_URI"],
    scope="user-top-read",
    cache_path=".cache",
    show_dialog=True
)

# --- Sidebar: Settings and Sign Out ---
with st.sidebar:
    st.title("Settings")
    if st.button("🔁 Sign Out and Reauthenticate"):
        for f in os.listdir():
            if f.startswith(".cache"):
                os.remove(f)
        st.success("Cache cleared. Reloading...")
        st.rerun()

# --- Authentication ---
token_info = auth_manager.get_cached_token()
if not token_info:
    auth_url = auth_manager.get_authorize_url()
    st.markdown(f"## 🔐 [Click here to log in to Spotify]({auth_url})")
    st.info("After logging in, return to this page to continue.")
    st.stop()

# --- Initialize Spotify client ---
sp = spotipy.Spotify(auth_manager=auth_manager)

# --- Main UI ---
st.title("🎧 Spotify Audio Feature Explorer")

# Choose between top tracks or playlist
mode = st.radio("What would you like to explore?", ["Your Top Tracks", "A Public Playlist"])

if mode == "Your Top Tracks":
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

    with st.spinner("Loading top tracks..."):
        try:
            top_tracks = sp.current_user_top_tracks(limit=20, time_range=time_range)
        except spotipy.exceptions.SpotifyException:
            st.error("Authentication failed. Try signing out and logging in again.")
            st.stop()

    if not top_tracks or not top_tracks.get("items"):
        st.warning("No top tracks found. Try listening to some music first!")
        st.stop()

    items = top_tracks["items"]

else:
    playlist_url_or_id = st.text_input("Enter a Spotify playlist URL or ID")
    if not playlist_url_or_id:
        st.stop()

    playlist_id = extract_playlist_id(playlist_url_or_id)
    if not playlist_id:
        st.error("❌ Invalid playlist URL or ID.")
        st.stop()

    with st.spinner("Loading playlist..."):
        try:
            playlist_data = sp.playlist_items(
                playlist_id,
                market="from_token",
                additional_types=["track"],
                limit=100
            )
            items = [item["track"] for item in playlist_data["items"] if item["track"]]
        except spotipy.exceptions.SpotifyException as e:
            st.error("Could not fetch playlist. Make sure it's public.")
            st.exception(e)
            st.stop()

# --- Parse audio features ---
track_data = []
for item in items:
    features = sp.audio_features([item["id"]])[0]
    if features is None:
        continue  # skip if audio features not found
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

if not track_data:
    st.warning("No track data could be retrieved.")
    st.stop()

df = pd.DataFrame(track_data)

# --- Track selection ---
selected_track_name = st.selectbox("🎵 Select a track to highlight", df["Track Name"])
selected_row = df[df["Track Name"] == selected_track_name].iloc[0]

# --- Feature scatterplot ---
st.subheader("🔍 Audio Feature Scatterplot")
x_feature = st.selectbox("X-axis", ["Danceability", "Energy", "Valence", "Tempo", "Popularity"], index=0)
y_feature = st.selectbox("Y-axis", ["Energy", "Valence", "Danceability", "Tempo", "Popularity"], index=1)

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

# --- Raw data ---
with st.expander("📋 View Raw Data"):
    st.dataframe(df.drop(columns=["Track ID"]))

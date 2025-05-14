import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import plotly.express as px
import os

# Set Streamlit page config
st.set_page_config(page_title="Spotify Preference Explorer", layout="wide")

# Sidebar authentication setup
st.sidebar.title("Spotify Authentication")
client_id = st.secrets["SPOTIPY_CLIENT_ID"]
client_secret = st.secrets["SPOTIPY_CLIENT_SECRET"]
redirect_uri = st.secrets["SPOTIPY_REDIRECT_URI"]

scope = "user-top-read"
auth_manager = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    show_dialog=True,
    cache_path=".cache"
)

if st.sidebar.button("Sign Out and Reauthenticate"):
    try:
        os.remove(".cache")
    except FileNotFoundError:
        pass
    st.success("Cache cleared. Please reload to log in again.")
    st.rerun()

# Get token
token_info = auth_manager.get_access_token(as_dict=True)

if not token_info:
    auth_url = auth_manager.get_authorize_url()
    st.markdown(f"## 🔐 [Click here to log in to Spotify]({auth_url})")
    st.info("After logging in, return to this app URL to continue.")
    st.stop()

# Create Spotify API client
sp = spotipy.Spotify(auth_manager=auth_manager)

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

# Title
st.title("🎧 Spotify Preference Explorer")

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

df = pd.DataFrame(track_data)

# Track selection
selected_track_name = st.selectbox("🎵 Select a track to highlight", df["Track Name"])
selected_track_id = df[df["Track Name"] == selected_track_name]["Track ID"].values[0]
st.query_params.update({"track_id": selected_track_id})

# Feature scatterplot
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

# Raw data table
with st.expander("📋 View Raw Data"):
    st.dataframe(df.drop(columns=["Track ID"]))

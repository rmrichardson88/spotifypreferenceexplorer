import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import time
import plotly.express as px

# Set page config
st.set_page_config(page_title="Spotify Preference Explorer", layout="wide")

# Sidebar authentication setup
st.sidebar.title("Spotify Authentication")
client_id = st.secrets["SPOTIPY_CLIENT_ID"]
client_secret = st.secrets["SPOTIPY_CLIENT_SECRET"]
redirect_uri = st.secrets["SPOTIPY_REDIRECT_URI"]

# Authenticate with Spotify
scope = "user-top-read"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    show_dialog=True,
    cache_path=".cache"
))

# Get time range selection
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
    except spotipy.exceptions.SpotifyException as e:
        st.error("Authentication failed. Please try logging in again.")
        st.stop()

# Title
st.title("🎧 Spotify Preference Explorer")

# If no top tracks
if not top_tracks or not top_tracks.get("items"):
    st.warning("No top tracks found. Try listening to some music first!")
    st.stop()

# Parse top tracks
track_data = []
for idx, item in enumerate(top_tracks["items"]):
    features = sp.audio_features([item["id"]])[0]
    if features is None:  # 🔧 SAFEGUARD against missing features
        continue
    track_data.append({
        "Track Name": item["name"],
        "Artist": item["artists"][0]["name"],
        "Danceability": features["danceability"],
        "Energy": features["energy"],
        "Valence": features["valence"],
        "Tempo": features["tempo"],
        "Popularity": item["popularity"],
        "Track ID": item["id"],
        "Preview URL": item.get("preview_url")  # 🔧 Add preview URL if available
    })

df = pd.DataFrame(track_data)

# Track selection
selected_track_name = st.selectbox("🎵 Select a track to highlight", df["Track Name"])

# Get corresponding ID and update query params
selected_track_id = df[df["Track Name"] == selected_track_name]["Track ID"].values[0]
st.experimental_set_query_params(track_id=selected_track_id)  # 🔧 Use experimental method for query param

# 2D Feature Scatterplot
st.subheader("🔍 Audio Feature Scatterplot")

# 🔧 Place X/Y selectors in columns for better layout
col1, col2 = st.columns(2)
with col1:
    x_feature = st.selectbox("X-axis", ["Danceability", "Energy", "Valence", "Tempo", "Popularity"], index=0)
with col2:
    y_feature_options = [feat for feat in ["Danceability", "Energy", "Valence", "Tempo", "Popularity"] if feat != x_feature]
    y_feature = st.selectbox("Y-axis", y_feature_options, index=0)

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

# 🔧 Optional: Audio preview
if selected_row.get("Preview URL"):
    st.subheader("▶️ Track Preview")
    st.audio(selected_row["Preview URL"])

# Display data table
with st.expander("📋 View Raw Data"):
    st.dataframe(df.drop(columns=["Track ID", "Preview URL"]))

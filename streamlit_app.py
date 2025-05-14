import os
import pandas as pd
import plotly.express as px
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from packaging import version

# --- Page config ---
st.set_page_config(page_title="Spotify Explorer", page_icon="🎧")

# --- Spotify OAuth setup ---
auth_manager = SpotifyOAuth(
    client_id=st.secrets["SPOTIPY_CLIENT_ID"],
    client_secret=st.secrets["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=st.secrets["SPOTIPY_REDIRECT_URI"],
    scope="user-top-read",
    cache_path=".cache"
)

# --- Sidebar logout ---
with st.sidebar:
    st.title("Settings")
    if st.button("🔁 Sign Out and Reauthenticate"):
        try:
            os.remove(".cache")
        except FileNotFoundError:
            pass
        st.success("Cache cleared. Please reload the page to log in again.")
        st.stop()

# --- Authentication ---
try:
    token_info = auth_manager.get_access_token(as_dict=True)
    if not token_info:
        raise Exception("No token")
except Exception:
    auth_url = auth_manager.get_authorize_url()
    st.markdown(f"## 🔐 [Click here to log in to Spotify]({auth_url})")
    st.info("After logging in, return to this page to continue.")
    st.stop()

# --- Initialize Spotify client ---
sp = spotipy.Spotify(auth_manager=auth_manager)

# --- App content ---
st.title("🎧 Spotify Audio Feature Explorer")
st.markdown("Explore your top tracks and their audio features.")

# --- Time range selector ---
time_range = st.sidebar.radio(
    "Time Range",
    options=["short_term", "medium_term", "long_term"],
    format_func=lambda x: {
        "short_term": "Last 4 Weeks",
        "medium_term": "Last 6 Months",
        "long_term": "All Time"
    }[x]
)

# --- Fetch top tracks ---
with st.spinner("Loading top tracks..."):
    try:
        top_tracks = sp.current_user_top_tracks(limit=20, time_range=time_range)
    except spotipy.exceptions.SpotifyException:
        st.error("Authentication failed. Please try signing out and logging in again.")
        st.stop()

# --- Handle empty results ---
if not top_tracks or not top_tracks.get("items"):
    st.warning("No top tracks found. Try listening to some music first!")
    st.stop()

# --- Build DataFrame ---
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

df = pd.DataFrame(track_data)

# --- Track selector ---
selected_track_name = st.selectbox("🎵 Select a track to highlight", df["Track Name"])
selected_track_id = df[df["Track Name"] == selected_track_name]["Track ID"].values[0]

# --- Set query param (modern & fallback support) ---
if version.parse(st.__version__) >= version.parse("1.32.0"):
    st.query_params["track_id"] = [selected_track_id]
else:
    st.experimental_set_query_params(track_id=selected_track_id)

# --- Scatterplot for features ---
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

# --- Highlight selected track ---
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

# --- Show raw data ---
with st.expander("📋 View Raw Data"):
    st.dataframe(df.drop(columns=["Track ID"]))

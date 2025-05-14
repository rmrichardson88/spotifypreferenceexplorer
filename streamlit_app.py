import os
import re
import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import plotly.express as px

# --- Page config ---
st.set_page_config(page_title="Spotify Explorer", page_icon="🎧")

# --- Spotify OAuth setup ---
auth_manager = SpotifyOAuth(
    client_id=st.secrets["SPOTIPY_CLIENT_ID"],
    client_secret=st.secrets["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=st.secrets["SPOTIPY_REDIRECT_URI"],
    scope="user-top-read",
    cache_path=".cache",
    show_dialog=True
)

# --- Sidebar: Settings and logout ---
with st.sidebar:
    st.title("Settings")
    if st.button("🔁 Sign Out and Reauthenticate"):
        for f in os.listdir():
            if f.startswith(".cache"):
                os.remove(f)
        st.success("Cache cleared. Reloading...")
        st.experimental_rerun()

# --- Token check ---
token_info = auth_manager.get_cached_token()
if not token_info:
    auth_url = auth_manager.get_authorize_url()
    st.markdown(f"## 🔐 [Click here to log in to Spotify]({auth_url})")
    st.info("After logging in, return to this page to continue.")
    st.stop()

# --- Spotify client ---
sp = spotipy.Spotify(auth_manager=auth_manager)

# --- Caching functions ---
@st.cache_data(show_spinner=False)
def get_audio_features_cached(track_ids):
    try:
        return sp.audio_features(track_ids)
    except Exception:
        return [None] * len(track_ids)

@st.cache_data(show_spinner=False)
def get_playlist_items_cached(playlist_id):
    try:
        results = sp.playlist_items(playlist_id, market="from_token", additional_types=["track"])
        return results["items"]
    except Exception:
        return None

# --- App Title ---
st.title("🎧 Spotify Audio Feature Explorer")

# --- Mode Selection ---
mode = st.radio("Choose Mode:", ["Your Top Tracks", "Explore a Playlist"])

track_data = []

# --- Helper: Extract playlist ID ---
def extract_playlist_id(input_str):
    if not input_str:
        return None
    # Accept either full URL or just ID
    match = re.search(r"(playlist\/|spotify:playlist:)?([a-zA-Z0-9]+)", input_str)
    return match.group(2) if match else None

# --- Mode: Top Tracks ---
if mode == "Your Top Tracks":
    time_range = st.sidebar.radio(
        "Time Range",
        options=["short_term", "medium_term", "long_term"],
        format_func=lambda x: {
            "short_term": "Last 4 Weeks",
            "medium_term": "Last 6 Months",
            "long_term": "All Time"
        }[x]
    )
    with st.spinner("Loading your top tracks..."):
        try:
            top_tracks = sp.current_user_top_tracks(limit=20, time_range=time_range)
        except spotipy.exceptions.SpotifyException:
            st.error("Authentication failed. Please sign out and try again.")
            st.stop()
        except Exception as e:
            st.error(f"Spotify API error: {e}")
            st.stop()

    if not top_tracks or not top_tracks.get("items"):
        st.warning("No top tracks found. Try listening to more music first!")
        st.stop()

    track_ids = [item["id"] for item in top_tracks["items"]]
    features_list = get_audio_features_cached(track_ids)

    for item, features in zip(top_tracks["items"], features_list):
        if features:
            track_data.append({
                "Track Name": item["name"],
                "Artist": item["artists"][0]["name"],
                "Danceability": features["danceability"],
                "Energy": features["energy"],
                "Valence": features["valence"],
                "Tempo": features["tempo"],
                "Popularity": item["popularity"],
                "Speechiness": features["speechiness"],
                "Acousticness": features["acousticness"],
                "Instrumentalness": features["instrumentalness"],
                "Liveness": features["liveness"],
                "Track ID": item["id"]
            })

# --- Mode: Playlist Explorer ---
else:
    playlist_input = st.text_input("Paste Spotify playlist URL or ID:")
    playlist_id = extract_playlist_id(playlist_input)

    if playlist_id:
        with st.spinner("Loading playlist..."):
            playlist_tracks = get_playlist_items_cached(playlist_id)
            if playlist_tracks is None:
                st.error("Could not fetch playlist. Make sure it's public and the ID is correct.")
                st.stop()

        if not playlist_tracks:
            st.warning("No tracks found in the playlist.")
            st.stop()

        track_ids = []
        tracks_info = []
        for item in playlist_tracks:
            track = item.get("track")
            if track and track.get("id"):
                track_ids.append(track["id"])
                tracks_info.append(track)

        features_list = get_audio_features_cached(track_ids)

        for track, features in zip(tracks_info, features_list):
            if features:
                track_data.append({
                    "Track Name": track["name"],
                    "Artist": track["artists"][0]["name"],
                    "Danceability": features["danceability"],
                    "Energy": features["energy"],
                    "Valence": features["valence"],
                    "Tempo": features["tempo"],
                    "Popularity": track["popularity"],
                    "Speechiness": features["speechiness"],
                    "Acousticness": features["acousticness"],
                    "Instrumentalness": features["instrumentalness"],
                    "Liveness": features["liveness"],
                    "Track ID": track["id"]
                })

# --- Data Handling ---
if not track_data:
    st.warning("No audio features available to display.")
    st.stop()

df = pd.DataFrame(track_data)

# --- Track selection ---
track_options = df.apply(lambda r: f"{r['Track Name']} — {r['Artist']}", axis=1)
selected_option = st.selectbox("🎵 Select a track to highlight", track_options)
selected_track_id = df.loc[track_options == selected_option, "Track ID"].values[0]

# --- Feature scatterplot ---
st.subheader("🔍 Audio Feature Scatterplot")
feature_options = ["Danceability", "Energy", "Valence", "Tempo", "Popularity", "Speechiness", "Acousticness", "Instrumentalness", "Liveness"]
x_feature = st.selectbox("X-axis", feature_options, index=0)
y_feature = st.selectbox("Y-axis", [f for f in feature_options if f != x_feature], index=1)

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
selected_row = df[df["Track ID"] == selected_track_id].iloc[0]
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

# --- Raw data expander ---
with st.expander("📋 View Raw Data"):
    st.dataframe(df.drop(columns=["Track ID"]))

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
    show_dialog=False
)

# --- Sidebar: Settings and logout ---
with st.sidebar:
    st.title("Settings")
    if st.button("🔁 Sign Out and Reauthenticate"):
        st.session_state.clear()
        st.success("Session cleared. Reloading...")
        st.rerun()

# --- Token management ---
if "token_info" not in st.session_state:
    query_params = st.query_params

    # Handle redirect with "code" in URL
    if "code" in query_params:
        code = query_params["code"]
        token_info = auth_manager.get_access_token(code, as_dict=True)
        st.session_state.token_info = token_info
        st.success("Successfully authenticated with Spotify!")
        st.rerun()

    else:
        auth_url = auth_manager.get_authorize_url()
        st.markdown(f"## 🔐 [Click here to log in to Spotify]({auth_url})")
        st.info("After logging in, return to this page.")
        st.stop()

# Reuse cached token
token_info = st.session_state.token_info

# --- Spotify client ---
sp = spotipy.Spotify(auth=token_info["access_token"])

# --- App Title ---
st.title("🎧 Spotify Audio Feature Explorer")

# Optional: confirm login
try:
    profile = sp.current_user()
    st.success(f"Logged in as **{profile['display_name']}**")
except:
    st.error("Spotify session expired or failed. Please sign out and log in again.")
    st.stop()

# --- Mode Selection ---
mode = st.radio("Choose Mode:", ["Your Top Tracks", "Explore a Playlist"])

track_data = []

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

    if not top_tracks or not top_tracks.get("items"):
        st.warning("No top tracks found. Try listening to more music first!")
        st.stop()

    for item in top_tracks["items"]:
        features = sp.audio_features([item["id"]])[0]
        if features:
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

# --- Mode: Playlist Explorer ---
else:
    playlist_input = st.text_input("Paste Spotify Playlist ID or URL:")

    def extract_playlist_id(url):
        match = re.search(r"(playlist\/|spotify:playlist:)?([a-zA-Z0-9]+)", url)
        return match.group(2) if match else None

    playlist_id = extract_playlist_id(playlist_input)

    if playlist_id:
        with st.spinner("Loading playlist..."):
            try:
                results = sp.playlist_items(
                    playlist_id,
                    market="from_token",
                    additional_types=["track"]
                )
                playlist_tracks = results["items"]
            except spotipy.exceptions.SpotifyException:
                st.error("Could not fetch playlist. Make sure it's public.")
                st.stop()

        if not playlist_tracks:
            st.warning("No tracks found in the playlist.")
            st.stop()

        for item in playlist_tracks:
            track = item["track"]
            if not track or not track.get("id"):
                continue
            features = sp.audio_features([track["id"]])[0]
            if features:
                track_data.append({
                    "Track Name": track["name"],
                    "Artist": track["artists"][0]["name"],
                    "Danceability": features["danceability"],
                    "Energy": features["energy"],
                    "Valence": features["valence"],
                    "Tempo": features["tempo"],
                    "Popularity": track["popularity"],
                    "Track ID": track["id"]
                })

# --- Data Handling ---
if not track_data:
    st.warning("No audio features available to display.")
    st.stop()

df = pd.DataFrame(track_data)

# --- Track selection ---
selected_track_name = st.selectbox("🎵 Select a track to highlight", df["Track Name"])
selected_track_id = df[df["Track Name"] == selected_track_name]["Track ID"].values[0]

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

# --- Raw data expander ---
with st.expander("📋 View Raw Data"):
    st.dataframe(df.drop(columns=["Track ID"]))

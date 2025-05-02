import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import plotly.graph_objects as go
import os

# Set page config
st.set_page_config(page_title="Spotify Audio Feature Explorer", layout="wide")

# --- AUTHENTICATION ---
# Setup Spotify Auth
auth_manager = SpotifyOAuth(
    client_id=st.secrets["SPOTIPY_CLIENT_ID"],
    client_secret=st.secrets["SPOTIPY_CLIENT_SECRET"],
    redirect_uri=st.secrets["SPOTIPY_REDIRECT_URI"],
    scope="user-library-read playlist-read-private user-top-read",
    show_dialog=True,
    open_browser=False,
    cache_path=".cache"
)

# Check for authentication token
try:
    token_info = auth_manager.get_cached_token()
    if not token_info:
        auth_url = auth_manager.get_authorize_url()
        st.markdown(f"[Click here to authenticate with Spotify]({auth_url})")
        st.stop()

    sp = spotipy.Spotify(auth_manager=auth_manager)
except Exception as e:
    st.error(f"Spotify authentication failed: {e}")
    st.stop()

# --- HELPER FUNCTIONS ---
def get_tracks_from_playlist(playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    track_data = []
    for item in tracks:
        track = item['track']
        if track and track['id']:
            track_data.append({
                'name': track['name'],
                'id': track['id'],
                'artist': track['artists'][0]['name'] if track['artists'] else 'Unknown',
                'album': track['album']['name'] if track['album'] else 'Unknown'
            })
    return pd.DataFrame(track_data)

def get_audio_features(track_ids):
    features = sp.audio_features(tracks=track_ids)
    return pd.DataFrame(features)

def process_playlist(playlist_id):
    tracks = get_tracks_from_playlist(playlist_id)
    features = get_audio_features(tracks['id'].tolist())
    return pd.merge(tracks, features, on='id')

# --- MAIN APP ---
st.title("🎶 Spotify Audio Feature Explorer")

# Get user playlists
playlists = sp.current_user_playlists(limit=50)
playlist_options = {pl['name']: pl['id'] for pl in playlists['items']}

# Select two playlists to compare
col1, col2 = st.columns(2)
with col1:
    playlist_1_name = st.selectbox("🎧 Playlist 1", playlist_options.keys(), key="pl1")
with col2:
    playlist_2_name = st.selectbox("🎼 Playlist 2", playlist_options.keys(), key="pl2")

playlist_1_id = playlist_options[playlist_1_name]
playlist_2_id = playlist_options[playlist_2_name]

with st.spinner("Fetching and comparing playlists..."):
    df1 = process_playlist(playlist_1_id)
    df2 = process_playlist(playlist_2_id)

    features = ['danceability', 'energy', 'valence', 'acousticness', 'liveness', 'speechiness']
    avg1 = df1[features].mean()
    avg2 = df2[features].mean()

# --- RADAR CHART ---
fig_compare = go.Figure()

fig_compare.add_trace(go.Scatterpolar(
    r=avg1.values,
    theta=features,
    fill='toself',
    name=playlist_1_name
))
fig_compare.add_trace(go.Scatterpolar(
    r=avg2.values,
    theta=features,
    fill='toself',
    name=playlist_2_name
))

fig_compare.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0,1])),
    title="🔁 Playlist Comparison: Audio Feature Profiles"
)

st.plotly_chart(fig_compare, use_container_width=True)

# --- OPTIONAL TRACK TABLES ---
with st.expander("🔍 Playlist 1 Tracks"):
    st.dataframe(df1[['name', 'artist', 'danceability', 'energy', 'valence']].round(2))

with st.expander("🔍 Playlist 2 Tracks"):
    st.dataframe(df2[['name', 'artist', 'danceability', 'energy', 'valence']].round(2))

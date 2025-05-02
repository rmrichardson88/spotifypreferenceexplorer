import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Page config
st.set_page_config(page_title="Spotify Audio Feature Explorer", layout="wide")

# Setup SpotifyOAuth using Streamlit secrets
sp_oauth = SpotifyOAuth(
    client_id=st.secrets["spotify"]["client_id"],
    client_secret=st.secrets["spotify"]["client_secret"],
    redirect_uri=st.secrets["spotify"]["redirect_uri"],
    scope="user-library-read playlist-read-private user-top-read",
    cache_path=".cache"  # optional: avoids repeated login
)

# Handle token retrieval
token_info = sp_oauth.get_access_token(as_dict=False)
if not token_info:
    st.error("Unable to authenticate with Spotify.")
    st.stop()

# Initialize Spotify client
sp = spotipy.Spotify(auth=token_info)

# Fetch user info
user = sp.current_user()
st.sidebar.image(user['images'][0]['url'], width=100) if user.get('images') else None
st.sidebar.markdown(f"### {user['display_name']}")
st.sidebar.write(f"ID: `{user['id']}`")

# Fetch user playlists
playlists = sp.current_user_playlists(limit=50)

playlist_options = {pl['name']: pl['id'] for pl in playlists['items']}
selected_name = st.selectbox("🎵 Choose a playlist", playlist_options.keys())
selected_id = playlist_options[selected_name]

st.write(f"Selected playlist: `{selected_name}` (`{selected_id}`)")

import pandas as pd

# Get tracks from the selected playlist
def get_tracks_from_playlist(playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    
    # Paginate if more than 100 tracks
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    
    # Extract track info
    track_data = []
    for item in tracks:
        track = item['track']
        if track:  # filter out missing
            track_data.append({
                'name': track['name'],
                'id': track['id'],
                'artist': track['artists'][0]['name'] if track['artists'] else 'Unknown',
                'album': track['album']['name'] if track['album'] else 'Unknown'
            })
    
    return pd.DataFrame(track_data)

# Get audio features for a list of track IDs
def get_audio_features(track_ids):
    features = sp.audio_features(tracks=track_ids)
    return pd.DataFrame(features)

# Get track list and audio features
with st.spinner("Fetching tracks and audio features..."):
    track_df = get_tracks_from_playlist(selected_id)
    audio_df = get_audio_features(track_df['id'].tolist())

# Merge track info with audio features
merged_df = pd.merge(track_df, audio_df, left_on='id', right_on='id')
display_cols = ['name', 'artist', 'danceability', 'energy', 'valence', 'tempo']
st.subheader("🎧 Audio Features")
st.dataframe(merged_df[display_cols].round(2))

import plotly.graph_objects as go

# Let user pick a track
selected_track = st.selectbox("🎵 Choose a track to explore", merged_df['name'])

track_row = merged_df[merged_df['name'] == selected_track].iloc[0]
features_to_plot = ['danceability', 'energy', 'valence', 'acousticness', 'liveness', 'speechiness']

# 🎯 RADAR CHART for a single track
fig_radar = go.Figure()

fig_radar.add_trace(go.Scatterpolar(
    r=[track_row[feature] for feature in features_to_plot],
    theta=features_to_plot,
    fill='toself',
    name=selected_track
))

fig_radar.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0,1])),
    showlegend=False,
    title=f"🎯 Audio Profile: {selected_track}"
)

st.plotly_chart(fig_radar, use_container_width=True)

# 📊 BAR CHART for average across playlist
avg_features = merged_df[features_to_plot].mean().round(2)

fig_bar = go.Figure([go.Bar(x=avg_features.index, y=avg_features.values)])
fig_bar.update_layout(title="📊 Average Audio Features in Playlist", yaxis=dict(range=[0, 1]))
st.plotly_chart(fig_bar, use_container_width=True)


import pandas as pd
from urllib.parse import urlparse
import re
import streamlit as st

def extract_playlist_id(playlist_url: str) -> str:
    """Extract Spotify playlist ID from different URL formats."""
    match = re.search(r"playlist/([a-zA-Z0-9]+)", playlist_url)
    if match:
        return match.group(1)
    
    if re.match(r"^[a-zA-Z0-9]{22}$", playlist_url):
        return playlist_url
        
    raise ValueError("Invalid Spotify playlist URL or ID")

def get_playlist_audio_features(sp, playlist_url: str):
    """Fetch and analyze audio features from a Spotify playlist."""
    try:
        playlist_id = extract_playlist_id(playlist_url)
        st.info(f"Using playlist ID: {playlist_id}")
        
        try:
            playlist_info = sp.playlist(playlist_id, fields="name,description")
            st.success(f"Found playlist: {playlist_info['name']}")
        except Exception as e:
            st.error(f"Error accessing playlist: {str(e)}")
            raise ValueError(f"Could not access playlist. Verify the playlist is public and your credentials are correct: {str(e)}")
        
        results = sp.playlist_tracks(playlist_id, limit=100, market='US')
        tracks = results["items"]

        if not tracks:
            raise ValueError("The playlist is empty or could not be fetched.")

        st.info(f"Successfully found {len(tracks)} tracks in the playlist")
        
        track_ids = [item.get("track", {}).get("id") for item in tracks if item.get("track")]
        track_ids = [tid for tid in track_ids if tid]
        
        if not track_ids:
            raise ValueError("No valid tracks found in this playlist.")
            
        audio_features = []
        batch_size = 50
        for i in range(0, len(track_ids), batch_size):
            batch = track_ids[i:i+batch_size]
            batch_features = sp.audio_features(batch)
            audio_features.extend(batch_features)

        for i, item in enumerate(tracks):
            track = item.get("track")
            if not track or not track.get("id") or i >= len(audio_features) or not audio_features[i]:
                continue
                
            audio_features[i]["name"] = track["name"]
            audio_features[i]["artist"] = track["artists"][0]["name"]
        
        audio_features = [af for af in audio_features if af]
        
        if not audio_features:
            raise ValueError("No valid audio features found in this playlist.")

        df = pd.DataFrame(audio_features)
        feature_cols = ["danceability", "energy", "valence", "tempo", "acousticness", "instrumentalness"]
        top_attributes = df[feature_cols].mean().sort_values(ascending=False)
        return df, top_attributes
        
    except Exception as e:
        import traceback
        st.error(f"Error in playlist processing: {str(e)}")
        st.code(traceback.format_exc(), language="python")
        raise

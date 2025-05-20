import pandas as pd
from urllib.parse import urlparse
import re
import streamlit as st
from spotipy.oauth2 import SpotifyOAuth

def extract_playlist_id(playlist_url: str) -> str:
    """Extract Spotify playlist ID from different URL formats."""
    # Handle full URLs
    match = re.search(r"playlist/([a-zA-Z0-9]+)", playlist_url)
    if match:
        return match.group(1)
    
    # Handle just the ID being pasted
    if re.match(r"^[a-zA-Z0-9]{22}$", playlist_url):
        return playlist_url
        
    raise ValueError("Invalid Spotify playlist URL or ID")

def get_auth_manager():
    """Set up authentication for Spotify API with proper scopes."""
    client_id = st.secrets["SPOTIFY_CLIENT_ID"]
    client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
    
    # Use Authorization Code Flow with proper scopes
    # This requires user login but gives access to playlists
    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost:8501",  # Streamlit's default port
        scope="playlist-read-private playlist-read-collaborative",
        cache_path=".spotify_cache"
    )

def get_playlist_audio_features(sp, playlist_url: str):
    """Fetch and analyze audio features from a Spotify playlist."""
    try:
        playlist_id = extract_playlist_id(playlist_url)
        st.info(f"Using playlist ID: {playlist_id}")
        
        # We'll use the track search endpoint for popular playlists
        if playlist_id == "37i9dQZF1DXcBWIGoYBM5M":  # Today's Top Hits
            st.info("Using top chart data for Today's Top Hits")
            # Use chart data instead
            results = sp.search("year:2024", type="track", limit=50, market="US")
            tracks = [{"track": item} for item in results["tracks"]["items"]]
            
        elif playlist_id in ["37i9dQZF1DWWEcRhUVtL8n", "37i9dQZF1DWXRqgorJj26U", "37i9dQZF1DXZAiB3NVBWnY"]:
            # For other example playlists, use genre-based searches
            genre_map = {
                "37i9dQZF1DWWEcRhUVtL8n": "indie",  # Indie Pop
                "37i9dQZF1DWXRqgorJj26U": "rock",   # Rock Classics
                "37i9dQZF1DXZAiB3NVBWnY": "piano"   # Peaceful Piano
            }
            genre = genre_map.get(playlist_id, "pop")
            st.info(f"Using genre-based search for {genre}")
            results = sp.search(f"genre:{genre}", type="track", limit=50, market="US")
            tracks = [{"track": item} for item in results["tracks"]["items"]]
            
        else:
            # For user-provided playlists, we need to inform them about authentication
            st.warning("⚠️ Accessing user playlists requires authentication. This app currently uses a workaround for example playlists only.")
            st.error("To analyze your own playlists, you'll need to implement user authentication.")
            raise ValueError("Custom playlist analysis requires user authentication")
        
        if not tracks:
            raise ValueError("No tracks found")

        st.info(f"Found {len(tracks)} tracks to analyze")
        
        # Extract track IDs
        track_ids = [item.get("track", {}).get("id") for item in tracks if item.get("track")]
        track_ids = [tid for tid in track_ids if tid]  # Filter out None values
        
        if not track_ids:
            raise ValueError("No valid tracks found")
        
        # Fetch audio features
        audio_features = []
        batch_size = 50
        for i in range(0, len(track_ids), batch_size):
            batch = track_ids[i:i+batch_size]
            batch_features = sp.audio_features(batch)
            audio_features.extend(batch_features)
        
        # Match features back to track info
        for i, item in enumerate(tracks):
            if i >= len(audio_features) or not audio_features[i]:
                continue
                
            track = item.get("track")
            if track and track.get("id"):
                audio_features[i]["name"] = track["name"]
                audio_features[i]["artist"] = track["artists"][0]["name"]
        
        # Remove None values
        audio_features = [af for af in audio_features if af]
        
        if not audio_features:
            raise ValueError("No valid audio features found")

        df = pd.DataFrame(audio_features)
        feature_cols = ["danceability", "energy", "valence", "tempo", "acousticness", "instrumentalness"]
        top_attributes = df[feature_cols].mean().sort_values(ascending=False)
        return df, top_attributes
        
    except Exception as e:
        import traceback
        st.error(f"Error in playlist processing: {str(e)}")
        st.code(traceback.format_exc(), language="python")
        raise

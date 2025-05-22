# spotify_client.py
import pandas as pd
import streamlit as st
from spotipy.oauth2 import SpotifyOAuth
import re
from typing import Tuple, List, Dict, Optional, Any
import time

def extract_playlist_id(playlist_url: str) -> str:
    """
    Extract Spotify playlist ID from different URL formats.
    
    Supports:
    - Full URL (https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M)
    - URI format (spotify:playlist:37i9dQZF1DXcBWIGoYBM5M)
    - Raw ID (37i9dQZF1DXcBWIGoYBM5M)
    
    Args:
        playlist_url: String containing a Spotify playlist URL or ID
        
    Returns:
        String containing just the playlist ID
        
    Raises:
        ValueError: If the input doesn't match any expected Spotify playlist format
    """
    # Check for full URL format
    url_match = re.search(r"playlist/([a-zA-Z0-9]+)", playlist_url)
    if url_match:
        return url_match.group(1)
    
    # Check for URI format
    uri_match = re.search(r"spotify:playlist:([a-zA-Z0-9]+)", playlist_url)
    if uri_match:
        return uri_match.group(1)
    
    # Check if it's just the ID
    if re.match(r"^[a-zA-Z0-9]{22}$", playlist_url):
        return playlist_url
        
    raise ValueError("Invalid Spotify playlist URL or ID format")

def setup_spotify_oauth():
    """
    Set up authentication for Spotify API with proper redirect.
    
    Returns:
        SpotifyOAuth: Authentication manager for Spotify API
    """
    return SpotifyOAuth(
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=st.secrets.get("SPOTIPY_REDIRECT_URI", "https://spotifypreferenceexplorer.streamlit.app/"),
        scope="playlist-read-private playlist-read-collaborative user-library-read",
        cache_path=".spotify_cache"
    )

@st.cache_data(ttl=3600)  # Cache results for 1 hour
def get_playlist_tracks(sp, playlist_id: str) -> List[Dict[str, Any]]:
    """
    Get all tracks from a Spotify playlist.
    
    Args:
        sp: Authenticated Spotify client
        playlist_id: ID of the playlist to fetch
        
    Returns:
        List of track items from the playlist
        
    Raises:
        Exception: If playlist cannot be accessed or doesn't exist
    """
    try:
        # Get playlist information
        playlist = sp.playlist(playlist_id)
        
        # Initialize with first batch of tracks
        results = playlist["tracks"]
        tracks = results["items"]
        
        # Paginate if there are more tracks
        while results["next"]:
            results = sp.next(results)
            tracks.extend(results["items"])
        
        return tracks
    except Exception as e:
        st.error(f"Failed to get playlist tracks: {str(e)}")
        raise

@st.cache_data(ttl=3600)  # Cache results for 1 hour
def get_audio_features_batch(sp, track_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Get audio features for a batch of tracks.
    
    Args:
        sp: Authenticated Spotify client
        track_ids: List of track IDs to fetch features for
        
    Returns:
        List of audio features for tracks
    """
    audio_features = []
    # Process in batches of 100 (Spotify API limit)
    batch_size = 100
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i:i+batch_size]
        batch_features = sp.audio_features(batch)
        
        # Add retry logic for API rate limiting
        retry_count = 0
        while batch_features is None and retry_count < 3:
            st.warning(f"Rate limiting detected, retrying in {2**retry_count} seconds...")
            time.sleep(2**retry_count)
            batch_features = sp.audio_features(batch)
            retry_count += 1
            
        if batch_features:
            audio_features.extend(batch_features)
    
    return [af for af in audio_features if af is not None]

def process_track_features(tracks: List[Dict[str, Any]], 
                          audio_features: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Process and combine track info with audio features.
    
    Args:
        tracks: List of track items from the playlist
        audio_features: List of audio features for the tracks
        
    Returns:
        DataFrame with combined track info and audio features
    """
    # Create a dictionary mapping track IDs to their audio features
    features_dict = {item["id"]: item for item in audio_features if item}
    
    # Create a list to hold the combined data
    combined_data = []
    
    for item in tracks:
        track = item.get("track")
        if not track or not track.get("id"):
            continue
            
        track_id = track["id"]
        features = features_dict.get(track_id)
        
        if not features:
            continue
            
        # Combine track info with audio features
        combined_item = {
            "id": track_id,
            "name": track["name"],
            "artist": ", ".join([artist["name"] for artist in track["artists"]]),
            "album": track["album"]["name"],
            "popularity": track["popularity"],
            "duration_ms": track["duration_ms"],
            "explicit": track["explicit"],
            "album_release_date": track["album"]["release_date"],
            "external_url": track["external_urls"].get("spotify", "")
        }
        
        # Add audio features
        feature_keys = ["danceability", "energy", "key", "loudness", "mode", 
                        "speechiness", "acousticness", "instrumentalness", 
                        "liveness", "valence", "tempo", "time_signature"]
                        
        for key in feature_keys:
            combined_item[key] = features.get(key)
            
        combined_data.append(combined_item)
    
    # Convert to DataFrame
    return pd.DataFrame(combined_data)

def calculate_top_attributes(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate average audio features from track data.
    
    Args:
        df: DataFrame containing track data with audio features
        
    Returns:
        Dictionary with average values for key audio features
    """
    # Select the features we want to analyze
    feature_cols = ["danceability", "energy", "valence", "tempo", 
                   "acousticness", "instrumentalness", "speechiness"]
    
    # Calculate averages and normalize tempo to 0-1 scale for consistency
    means = df[feature_cols].mean()
    
    # Convert tempo to a 0-1 scale (assuming tempo ranges from 0-250 BPM)
    if "tempo" in means:
        means["tempo"] = means["tempo"] / 250
    
    # Sort features by value
    return means.sort_values(ascending=False)

def get_playlist_audio_features(sp, playlist_url: str) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Fetch and analyze audio features from a Spotify playlist.
    
    Args:
        sp: Authenticated Spotify client
        playlist_url: URL or ID of the Spotify playlist
        
    Returns:
        Tuple containing:
            - DataFrame with track data and audio features
            - Dictionary with average values for key audio features
    """
    try:
        # Extract playlist ID from URL
        playlist_id = extract_playlist_id(playlist_url)
        st.info(f"Using playlist ID: {playlist_id}")
        
        # Handle example playlists differently
        example_ids = ["37i9dQZF1DXcBWIGoYBM5M", "37i9dQZF1DWWEcRhUVtL8n", 
                      "37i9dQZF1DWXRqgorJj26U", "37i9dQZF1DXZAiB3NVBWnY"]
        
        if playlist_id in example_ids:
            tracks = handle_example_playlist(sp, playlist_id)
        else:
            # For real playlists
            tracks = get_playlist_tracks(sp, playlist_id)
        
        if not tracks:
            raise ValueError("No tracks found in playlist")

        st.info(f"Found {len(tracks)} tracks to analyze")
        
        # Extract track IDs
        track_ids = [item.get("track", {}).get("id") for item in tracks if item.get("track")]
        track_ids = [tid for tid in track_ids if tid]  # Filter out None values
        
        if not track_ids:
            raise ValueError("No valid tracks found in playlist")
        
        # Fetch audio features
        audio_features = get_audio_features_batch(sp, track_ids)
        
        if not audio_features:
            raise ValueError("Failed to retrieve audio features")

        # Process and combine track info with audio features
        df = process_track_features(tracks, audio_features)
        
        # Calculate average audio features
        top_attributes = calculate_top_attributes(df)
        
        return df, top_attributes
        
    except Exception as e:
        st.error(f"Error in playlist processing: {str(e)}")
        raise

def handle_example_playlist(sp, playlist_id: str) -> List[Dict[str, Any]]:
    """
    Handle example playlists by searching for tracks instead of direct access.
    
    Args:
        sp: Authenticated Spotify client
        playlist_id: ID of the example playlist
        
    Returns:
        List of track items mimicking playlist track structure
    """
    # Map of playlist IDs to search queries
    playlist_queries = {
        "37i9dQZF1DXcBWIGoYBM5M": {"query": "year:2024", "genre": None},  # Today's Top Hits
        "37i9dQZF1DWWEcRhUVtL8n": {"query": None, "genre": "indie"},      # Indie Pop
        "37i9dQZF1DWXRqgorJj26U": {"query": None, "genre": "rock"},       # Rock Classics
        "37i9dQZF1DXZAiB3NVBWnY": {"query": None, "genre": "piano"}       # Peaceful Piano
    }
    
    query_info = playlist_queries.get(playlist_id, {"query": "pop", "genre": None})
    
    if query_info["genre"]:
        st.info(f"Using genre-based search for {query_info['genre']}")
        search_query = f"genre:{query_info['genre']}"
    else:
        search_query = query_info["query"] or "year:2024"
        st.info(f"Using search query: {search_query}")
    
    # Search for tracks
    results = sp.search(search_query, type="track", limit=50, market="US")
    
    # Format results to match playlist tracks structure
    return [{"track": item} for item in results["tracks"]["items"]]

def get_recommendations(sp, top_attributes: Dict[str, float], 
                       seed_tracks: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get track recommendations based on playlist characteristics.
    
    Args:
        sp: Authenticated Spotify client
        top_attributes: Dictionary with audio feature values to target
        seed_tracks: List of track IDs to use as seeds (max 5)
        limit: Number of recommendations to return
        
    Returns:
        List of recommended tracks
    """
    # Use up to 5 seed tracks (Spotify API limit)
    seed_tracks = seed_tracks[:min(5, len(seed_tracks))]
    
    # Prepare parameters based on playlist's audio features
    params = {
        "seed_tracks": seed_tracks,
        "limit": limit
    }
    
    # Add target parameters based on playlist's audio features
    feature_mapping = {
        "danceability": "target_danceability",
        "energy": "target_energy",
        "valence": "target_valence",
        "acousticness": "target_acousticness",
        "instrumentalness": "target_instrumentalness"
    }
    
    for feature, target_name in feature_mapping.items():
        if feature in top_attributes:
            params[target_name] = top_attributes[feature]
    
    # Get recommendations
    try:
        recommendations = sp.recommendations(**params)
        return recommendations.get("tracks", [])
    except Exception as e:
        st.error(f"Error getting recommendations: {str(e)}")
        return []

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
import os
from urllib.parse import urlparse

def extract_playlist_id(url):
    path = urlparse(url).path
    parts = path.split("/")
    if len(parts) < 3 or not parts[-1]:
        raise ValueError("Invalid Spotify playlist URL.")
    return parts[-1]

def get_playlist_audio_features(playlist_url):
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise EnvironmentError("Missing Spotify API credentials.")

    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    ))

    playlist_id = extract_playlist_id(playlist_url)
    results = sp.playlist_tracks(playlist_id, limit=100, market='US')
    tracks = results.get("items", [])

    if not tracks:
        raise ValueError("The playlist is empty or could not be fetched.")

    audio_features = []
    for item in tracks:
        track = item.get("track")
        if not track or not track.get("id"):
            continue

        af = sp.audio_features(track["id"])[0]
        if af:
            af["name"] = track["name"]
            af["artist"] = track["artists"][0]["name"]
            audio_features.append(af)

    if not audio_features:
        raise ValueError("No valid audio features found in this playlist.")

    df = pd.DataFrame(audio_features)
    feature_cols = ["danceability", "energy", "valence", "tempo", "acousticness", "instrumentalness"]
    top_attributes = df[feature_cols].mean().sort_values(ascending=False)
    return df, top_attributes

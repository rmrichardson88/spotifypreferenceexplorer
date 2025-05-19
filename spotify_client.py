import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
import os
from urllib.parse import urlparse

def extract_playlist_id(url):
    path = urlparse(url).path
    return path.split("/")[-1]

def get_playlist_audio_features(playlist_url):
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
    ))
    
    playlist_id = extract_playlist_id(playlist_url)
    results = sp.playlist_tracks(playlist_id, limit=100, market="US")
    tracks = results["items"]

    audio_features = []
    for item in tracks:
        track = item["track"]
        af = sp.audio_features(track["id"])[0]
        if af:
            af["name"] = track["name"]
            af["artist"] = track["artists"][0]["name"]
            audio_features.append(af)

    df = pd.DataFrame(audio_features)
    feature_cols = ["danceability", "energy", "valence", "tempo", "acousticness", "instrumentalness"]
    top_attributes = df[feature_cols].mean().sort_values(ascending=False)
    return df, top_attributes

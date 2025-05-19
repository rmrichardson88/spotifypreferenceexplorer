import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import os
from urllib.parse import urlparse

def extract_playlist_id(url):
    path = urlparse(url).path
    return path.split("/")[-1]

def get_playlist_audio_features(playlist_url):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback"),
        scope="playlist-read-private playlist-read-collaborative"
    ))

    playlist_id = extract_playlist_id(playlist_url)
    results = sp.playlist_tracks(playlist_id, limit=100, market='US')
    tracks = results["items"]

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

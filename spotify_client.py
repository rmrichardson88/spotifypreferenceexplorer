import spotipy
from spotipy.oauth2 import SpotifyPKCE
import pandas as pd
import os
from urllib.parse import urlparse, parse_qs
import streamlit as st

def extract_playlist_id(url):
    path = urlparse(url).path
    return path.split("/")[-1]

def get_playlist_audio_features(playlist_url):
    sp_oauth = SpotifyPKCE(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        redirect_uri="https://spotifypreferenceexplorer.streamlit.app/",
        scope="playlist-read-private playlist-read-collaborative"
    )


    token_info = sp_oauth.get_cached_token()
    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        st.warning("Please authenticate with Spotify below:")
        st.markdown(f"[Click here to authorize]({auth_url})")
        auth_code = st.text_input("After authorizing, paste the full redirected URL here:")

        if auth_code:
            parsed = urlparse(auth_code)
            code = parse_qs(parsed.query).get("code", [None])[0]

            if not code:
                raise ValueError("Could not extract authorization code.")

            token_info = sp_oauth.get_access_token(code)

    if not token_info:
        raise ValueError("Authentication failed. Please check your client ID and URL.")

    sp = spotipy.Spotify(auth=token_info["access_token"])

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

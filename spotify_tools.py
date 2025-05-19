import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

def get_top_hits_data():
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
    playlist_id = "37i9dQZF1DXcBWIGoYBM5M"  # Today's Top Hits
    results = sp.playlist_items(playlist_id, market="US", limit=50)

    data = []
    for item in results["items"]:
        track = item["track"]
        features = sp.audio_features(track["id"])[0]
        if features:
            data.append({
                "name": track["name"],
                "artist": track["artists"][0]["name"],
                "popularity": track["popularity"],
                "danceability": features["danceability"],
                "energy": features["energy"],
                "valence": features["valence"],
                "tempo": features["tempo"]
            })
    return data

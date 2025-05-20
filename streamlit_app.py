import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotify_client import get_playlist_audio_features
from groq_agent import generate_commentary
import pandas as pd

st.set_page_config(page_title="AI Music Analyst", layout="centered")
st.title("\U0001F3B7 AI Music Analyst: Playlist Explorer")

with st.sidebar:
    st.header("Authentication Status")
    
    if 'SPOTIFY_CLIENT_ID' in st.secrets and 'SPOTIFY_CLIENT_SECRET' in st.secrets:
        st.success("✅ Spotify credentials configured")
    else:
        st.error("❌ Missing Spotify credentials")
        
    if 'GROQ_API_KEY' in st.secrets:
        st.success("✅ Groq API key configured")
    else:
        st.error("❌ Missing Groq API key")
    
    st.divider()
    st.markdown("### How to use")
    st.markdown("""
    1. Enter a **public** Spotify playlist URL
    2. The app will analyze audio features
    3. View insights and AI commentary
    """)

def get_spotify_client():
    """Initialize and return a Spotify client"""
    try:
        SPOTIFY_CLIENT_ID = st.secrets["SPOTIFY_CLIENT_ID"]
        SPOTIFY_CLIENT_SECRET = st.secrets["SPOTIFY_CLIENT_SECRET"]
        
        auth_manager = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        sp.search("test", limit=1)
        return sp
        
    except Exception as e:
        st.error(f"Failed to initialize Spotify client: {e}")
        if "401" in str(e):
            st.warning("Authentication failed. Please check your Spotify API credentials.")
        return None

sp = get_spotify_client()

if not sp:
    st.warning("⚠️ Please add valid Spotify credentials to continue.")
else:
    st.markdown("Enter a public Spotify playlist URL to analyze its audio characteristics and get AI-generated insights.")
    
    example_playlists = {
        "Today's Top Hits": "37i9dQZF1DXcBWIGoYBM5M",
        "Peaceful Piano": "37i9dQZF1DXZAiB3NVBWnY",
        "Indie Pop": "37i9dQZF1DWWEcRhUVtL8n", 
        "Rock Classics": "37i9dQZF1DWXRqgorJj26U"
    }
    
    selected_example = st.selectbox(
        "Try a sample playlist:", 
        [""] + list(example_playlists.keys()),
        index=0
    )
    
    if selected_example:
        playlist_id = example_playlists[selected_example]
        st.info(f"Using example playlist: {selected_example} (ID: {playlist_id})")
        playlist_url = playlist_id
    else:
        playlist_url = st.text_input("Or enter a Spotify playlist URL or ID:")
    
    if playlist_url:
        with st.spinner("Fetching playlist data..."):
            try:
                df, top_attributes = get_playlist_audio_features(sp, playlist_url)
                
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.subheader("Top Audio Attributes")
                    st.bar_chart(top_attributes)
                
                with col2:
                    st.subheader("Audio Features")
                    feature_descriptions = {
                        "danceability": "How suitable for dancing (0.0 = least, 1.0 = most)",
                        "energy": "Intensity and activity level (0.0 = least, 1.0 = most)",
                        "valence": "Musical positiveness (0.0 = sad, 1.0 = happy)",
                        "tempo": "Estimated BPM",
                        "acousticness": "Acoustic vs. electric (0.0 = electric, 1.0 = acoustic)",
                        "instrumentalness": "Vocal vs. instrumental (1.0 = instrumental)"
                    }
                    
                    for feature, value in top_attributes.items():
                        st.metric(
                            feature.title(), 
                            f"{value:.2f}", 
                            help=feature_descriptions.get(feature, "")
                        )
                
                st.subheader("Tracks in Playlist")
                if 'name' in df.columns and 'artist' in df.columns:
                    tracks_df = df[['name', 'artist']].reset_index(drop=True)
                    tracks_df.index = tracks_df.index + 1 
                    st.dataframe(tracks_df)
                
                st.subheader("\U0001F916 AI Commentary")
                with st.spinner("Generating insights..."):
                    commentary = generate_commentary(top_attributes)
                    st.markdown(commentary)

                st.download_button(
                    "Download Data as CSV",
                    df.to_csv(index=False).encode('utf-8'),
                    "playlist_audio_features.csv",
                    "text/csv",
                    key='download-csv'
                )

            except Exception as e:
                st.error(f"Failed to load playlist data")
                st.error(f"Error details: {str(e)}")

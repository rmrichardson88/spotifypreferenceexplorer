import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from spotify_client import (
    extract_playlist_id, 
    setup_spotify_oauth,
    get_playlist_audio_features,
    get_recommendations
)
from groq_agent import generate_commentary

# Set up page configuration with improved styling
st.set_page_config(
    page_title="AI Music Analyst",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    h1, h2, h3 {
        margin-bottom: 0.5rem;
    }
    .stAlert {
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .plot-container {
        border-radius: 5px;
        box-shadow: rgba(0, 0, 0, 0.05) 0px 6px 24px 0px;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.title("🎵 AI Music Analyst: Playlist Explorer")
st.markdown("""
Analyze any Spotify playlist to discover its musical characteristics and get AI-powered insights.
Connect with your Spotify account to analyze your personal playlists or use the example playlists.
""")

# Create tabs for app sections
tabs = st.tabs(["Analyze Playlist", "Compare Playlists", "About"])

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'comparison_mode' not in st.session_state:
    st.session_state.comparison_mode = False

def auth_spotify():
    """Handle Spotify OAuth authentication flow"""
    auth_manager = setup_spotify_oauth()
    
    # Check if token is already cached and valid
    token_info = auth_manager.cache_handler.get_cached_token()
    if token_info and not auth_manager.is_token_expired(token_info):
        st.session_state.authenticated = True
        return spotipy.Spotify(auth_manager=auth_manager)
    
    # If there's no valid token, we need to get one
    if 'code' in st.query_params:
        code = st.query_params['code']  # Direct access, no need for [0]
        auth_manager.get_access_token(code)
        st.session_state.authenticated = True
        st.query_params.clear()  # Clear all query params
        st.rerun()
    
    # If no code and no valid token, we need to show the auth link
    if not st.session_state.authenticated:
        auth_url = auth_manager.get_authorize_url()
        st.markdown(f"""
        ### Connect Your Spotify Account
        
        Connect your Spotify account to analyze your personal playlists.
        
        <a href="{auth_url}" class="button" 
            style="background-color: #1DB954; 
                  color: white; 
                  padding: 10px 20px; 
                  text-align: center; 
                  text-decoration: none; 
                  display: inline-block; 
                  font-size: 16px; 
                  margin: 4px 2px; 
                  border-radius: 12px;">
            Connect with Spotify
        </a>
        """, unsafe_allow_html=True)
        
        return None
    
    return spotipy.Spotify(auth_manager=auth_manager)

def get_user_playlists(_sp):
    """Fetch the current user's playlists"""
    if sp is None:
        return []
    
    try:
        current_user = sp.current_user()
        st.session_state.user_data = current_user
        
        results = sp.current_user_playlists(limit=50)
        playlists = results['items']
        
        while results['next']:
            results = sp.next(results)
            playlists.extend(results['items'])
            
        return playlists
    except Exception as e:
        st.error(f"Error fetching playlists: {str(e)}")
        return []

def create_radar_chart(top_attributes):
    """Create a radar chart of audio features"""
    # Select features for the radar chart
    features = ["danceability", "energy", "valence", 
                "acousticness", "instrumentalness", "speechiness"]
    
    # Filter top_attributes to only include the features we want
    feature_values = {k: v for k, v in top_attributes.items() if k in features}
    
    # Create data for the radar chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=list(feature_values.values()),
        theta=list(feature_values.keys()),
        fill='toself',
        name='Audio Features',
        line_color='#1DB954'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=40, b=40)
    )
    
    return fig

def create_feature_distribution(df):
    """Create boxplots showing the distribution of audio features"""
    features = ["danceability", "energy", "valence", 
               "acousticness", "instrumentalness", "speechiness"]
    
    # Melt the dataframe to long format for easier plotting
    df_melted = pd.melt(
        df[features], 
        var_name='Feature', 
        value_name='Value'
    )
    
    fig = px.box(
        df_melted, 
        x="Feature", 
        y="Value", 
        color="Feature",
        color_discrete_sequence=px.colors.qualitative.Plotly,
        points="all",
        title="Distribution of Audio Features"
    )
    
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Value (0-1 Scale)",
        showlegend=False,
        margin=dict(l=40, r=40, t=60, b=40)
    )
    
    return fig

def show_track_analysis(df):
    """Show detailed analysis of tracks in the playlist"""
    # Get the top and bottom 3 tracks for each major attribute
    attributes = {
        "Most Danceable": df.sort_values("danceability", ascending=False).head(3),
        "Least Danceable": df.sort_values("danceability").head(3),
        "Most Energetic": df.sort_values("energy", ascending=False).head(3),
        "Most Acoustic": df.sort_values("acousticness", ascending=False).head(3),
        "Happiest (High Valence)": df.sort_values("valence", ascending=False).head(3),
        "Saddest (Low Valence)": df.sort_values("valence").head(3),
    }
    
    # Create two columns
    col1, col2 = st.columns(2)
    
    # Display track insights in the columns
    for i, (label, tracks) in enumerate(attributes.items()):
        col = col1 if i % 2 == 0 else col2
        with col:
            st.subheader(label)
            for _, track in tracks.iterrows():
                st.markdown(f"""
                **{track['name']}** by {track['artist']}  
                """)

def display_playlist_info(playlist_name, playlist_image_url=None):
    """Display playlist header with image and name"""
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if playlist_image_url:
            st.image(playlist_image_url, width=150)
        else:
            st.image("https://via.placeholder.com/150", width=150)
    
    with col2:
        st.header(playlist_name)

def main():
    """Main application function"""
    # Set up sidebar
    with st.sidebar:
        st.header("Authentication Status")
        
        # Display configuration info
        if 'SPOTIFY_CLIENT_ID' in st.secrets and 'SPOTIFY_CLIENT_SECRET' in st.secrets:
            st.success("✅ Spotify credentials configured")
        else:
            st.error("❌ Missing Spotify credentials")
            
        if 'GROQ_API_KEY' in st.secrets:
            st.success("✅ Groq API key configured")
        else:
            st.error("❌ Missing Groq API key")
        
        st.divider()
        
        # If user is authenticated, show their info
        if st.session_state.authenticated and st.session_state.user_data:
            user = st.session_state.user_data
            st.write(f"Logged in as: **{user['display_name']}**")
            
            # Add logout button
            if st.button("Logout", use_container_width=True):
                # Clear cache and session state
                auth_manager = setup_spotify_oauth()
                auth_manager.cache_handler.clear()
                st.session_state.authenticated = False
                st.session_state.user_data = None
                st.experimental_rerun()
        
        st.divider()
        st.markdown("### Analysis Options")
        
        # Analysis focus
        analysis_focus = st.multiselect(
            "Focus on these attributes:",
            ["danceability", "energy", "valence", "tempo", "acousticness", "instrumentalness"],
            default=["danceability", "energy", "valence", "acousticness"]
        )
        
        # Track limit
        track_limit = st.slider(
            "Number of tracks to analyze:",
            min_value=10,
            max_value=100,
            value=50,
            step=10
        )
        
        # Commentary depth
        commentary_depth = st.select_slider(
            "Commentary detail:",
            options=["Brief", "Standard", "Detailed"],
            value="Standard"
        )
        
        # Display app info
        st.divider()
        st.markdown("### How to use")
        st.markdown("""
        1. Enter a Spotify playlist URL
        2. The app will analyze audio features
        3. View insights and AI commentary
        """)

    # Initialize Spotify client
    sp = auth_spotify()
    
    # Analyze Playlist Tab
    with tabs[0]:
        if not sp:
            st.info("Please connect your Spotify account to analyze playlists.")
        else:
            # Example playlists
            example_playlists = {
                "Today's Top Hits": "37i9dQZF1DXcBWIGoYBM5M",
                "Peaceful Piano": "37i9dQZF1DXZAiB3NVBWnY",
                "Indie Pop": "37i9dQZF1DWWEcRhUVtL8n", 
                "Rock Classics": "37i9dQZF1DWXRqgorJj26U"
            }
            
            # Fetch user playlists
            user_playlists = get_user_playlists(sp)
            
            # Create tabs for playlist selection
            playlist_tabs = st.tabs(["Your Playlists", "Example Playlists", "Enter URL"])
            
            playlist_url = None
            
            # Your Playlists tab
            with playlist_tabs[0]:
                if user_playlists:
                    st.write(f"Found {len(user_playlists)} playlists in your account.")
                    
                    # Group playlists by owner (Your vs. Followed)
                    own_playlists = []
                    followed_playlists = []
                    
                    for playlist in user_playlists:
                        if playlist['owner']['id'] == st.session_state.user_data['id']:
                            own_playlists.append(playlist)
                        else:
                            followed_playlists.append(playlist)
                    
                    # Display own playlists
                    if own_playlists:
                        st.subheader("Your Playlists")
                        cols = st.columns(3)
                        for i, playlist in enumerate(own_playlists):
                            with cols[i % 3]:
                                image_url = playlist['images'][0]['url'] if playlist['images'] else None
                                
                                if image_url:
                                    st.image(image_url, width=150)
                                
                                if st.button(f"Analyze {playlist['name']}", key=f"own_{i}"):
                                    playlist_url = playlist['id']
                    
                    # Display followed playlists
                    if followed_playlists:
                        st.subheader("Followed Playlists")
                        cols = st.columns(3)
                        for i, playlist in enumerate(followed_playlists):
                            with cols[i % 3]:
                                image_url = playlist['images'][0]['url'] if playlist['images'] else None
                                
                                if image_url:
                                    st.image(image_url, width=150)
                                
                                if st.button(f"Analyze {playlist['name']}", key=f"followed_{i}"):
                                    playlist_url = playlist['id']
                else:
                    st.info("No playlists found in your account or not logged in.")
            
            # Example Playlists tab
            with playlist_tabs[1]:
                st.write("Select an example playlist to analyze:")
                
                # Create a nice grid of example playlists
                cols = st.columns(2)
                for i, (name, pid) in enumerate(example_playlists.items()):
                    with cols[i % 2]:
                        st.write(f"### {name}")
                        if st.button(f"Analyze", key=f"example_{i}"):
                            playlist_url = pid
            
            # Enter URL tab
            with playlist_tabs[2]:
                st.write("Enter a Spotify playlist URL or ID:")
                manual_url = st.text_input(
                    "Spotify playlist URL or ID",
                    placeholder="https://open.spotify.com/playlist/...",
                    key="playlist_url_input"
                )
                
                if st.button("Analyze Playlist", key="analyze_url_button"):
                    if manual_url:
                        playlist_url = manual_url
                    else:
                        st.warning("Please enter a valid playlist URL or ID.")
            
            # If a playlist is selected or entered, analyze it
            if playlist_url:
                try:
                    with st.spinner("Fetching playlist data..."):
                        # Get playlist details first
                        try:
                            playlist_details = sp.playlist(playlist_url, fields="name,images")
                            playlist_name = playlist_details['name']
                            playlist_image = playlist_details['images'][0]['url'] if playlist_details['images'] else None
                        except:
                            # Default values if we can't get playlist details
                            playlist_name = "Playlist"
                            playlist_image = None
                        
                        # Display playlist header
                        display_playlist_info(playlist_name, playlist_image)
                        
                        # Get audio features
                        df, top_attributes = get_playlist_audio_features(sp, playlist_url)
                        
                    if df is not None and len(df) > 0:
                        # Create a tabbed interface for different views
                        analysis_tabs = st.tabs(["Overview", "Tracks", "Detailed Analysis", "Recommendations"])
                        
                        # Overview tab
                        with analysis_tabs[0]:
                            col1, col2 = st.columns([1, 1])
                            
                            with col1:
                                st.subheader("Audio Feature Radar")
                                radar_fig = create_radar_chart(top_attributes)
                                st.plotly_chart(radar_fig, use_container_width=True)
                            
                            with col2:
                                st.subheader("Top Audio Attributes")
                                st.bar_chart(top_attributes)
                                
                                # Add metrics for key attributes
                                metric_cols = st.columns(3)
                                key_metrics = {
                                    "Danceability": top_attributes.get("danceability", 0),
                                    "Energy": top_attributes.get("energy", 0),
                                    "Positivity": top_attributes.get("valence", 0)
                                }
                                
                                for i, (label, value) in enumerate(key_metrics.items()):
                                    with metric_cols[i % 3]:
                                        st.metric(label, f"{value:.2f}")
                            
                            # AI Commentary
                            st.subheader("🤖 AI Commentary")
                            with st.spinner("Generating insights..."):
                                # Include commentary depth in the request
                                commentary = generate_commentary(top_attributes, depth=commentary_depth.lower())
                                st.markdown(commentary)
                        
                        # Tracks tab
                        with analysis_tabs[1]:
                            st.subheader("Tracks in Playlist")
                            
                            # Prepare track data for display
                            if 'name' in df.columns and 'artist' in df.columns:
                                # Include more attributes in the display
                                display_cols = [
                                    'name', 'artist', 'album', 
                                    'danceability', 'energy', 'valence'
                                ]
                                
                                # Filter columns that exist in the dataframe
                                display_cols = [col for col in display_cols if col in df.columns]
                                
                                # Create track dataframe
                                tracks_df = df[display_cols].copy()
                                
                                # Format numeric columns
                                for col in ['danceability', 'energy', 'valence']:
                                    if col in tracks_df.columns:
                                        tracks_df[col] = tracks_df[col].apply(lambda x: f"{x:.2f}")
                                
                                # Add index for proper numbering
                                tracks_df.index = tracks_df.index + 1
                                
                                # Display with data editor for sorting/filtering
                                st.dataframe(
                                    tracks_df,
                                    use_container_width=True,
                                    height=400
                                )
                            
                                # Add download button
                                st.download_button(
                                    "Download Complete Data as CSV",
                                    df.to_csv(index=False).encode('utf-8'),
                                    "playlist_audio_features.csv",
                                    "text/csv",
                                    key='download-csv'
                                )
                        
                        # Detailed Analysis tab
                        with analysis_tabs[2]:
                            st.subheader("Feature Distribution")
                            distribution_fig = create_feature_distribution(df)
                            st.plotly_chart(distribution_fig, use_container_width=True)
                            
                            # Show Track Analysis
                            st.subheader("Track Highlights")
                            show_track_analysis(df)
                            
                            # Tempo Analysis
                            if 'tempo' in df.columns:
                                st.subheader("Tempo Distribution")
                                tempo_fig = px.histogram(
                                    df, 
                                    x="tempo", 
                                    nbins=20,
                                    color_discrete_sequence=['#1DB954'],
                                    title="BPM Distribution"
                                )
                                tempo_fig.update_layout(
                                    xaxis_title="Tempo (BPM)",
                                    yaxis_title="Number of Tracks"
                                )
                                st.plotly_chart(tempo_fig, use_container_width=True)
                        
                        # Recommendations tab
                        with analysis_tabs[3]:
                            st.subheader("🎵 Recommended Tracks Based on This Playlist")
                            
                            with st.spinner("Finding similar tracks..."):
                                # Get a few random track IDs from the playlist
                                if len(df) >= 5:
                                    seed_tracks = df['id'].sample(5).tolist()
                                else:
                                    seed_tracks = df['id'].tolist()
                                
                                recommended_tracks = get_recommendations(sp, top_attributes, seed_tracks)
                                
                                if recommended_tracks:
                                    # Display recommendations
                                    rec_data = []
                                    for track in recommended_tracks:
                                        rec_data.append({
                                            'Track': track['name'],
                                            'Artist': track['artists'][0]['name'],
                                            'Album': track['album']['name'],
                                            'Preview URL': track['preview_url'],
                                            'Spotify URL': track['external_urls']['spotify']
                                        })
                                    
                                    rec_df = pd.DataFrame(rec_data)
                                    
                                    # Display tracks with preview buttons
                                    for i, (_, track) in enumerate(rec_df.iterrows()):
                                        col1, col2 = st.columns([3, 1])
                                        
                                        with col1:
                                            st.markdown(f"""
                                            **{track['Track']}**  
                                            {track['Artist']} • {track['Album']}
                                            """)
                                        
                                        with col2:
                                            spotify_url = track['Spotify URL']
                                            st.markdown(f"[Open in Spotify]({spotify_url})")
                                            
                                            # Add audio preview if available
                                            if track['Preview URL']:
                                                st.audio(track['Preview URL'])
                                        
                                        if i < len(rec_df) - 1:
                                            st.divider()
                                else:
                                    st.info("No recommendations found for this playlist.")
                    else:
                        st.error("Failed to get playlist data. The playlist may be empty or not accessible.")
                
                except Exception as e:
                    st.error(f"Error analyzing playlist: {str(e)}")
    
    # Compare Playlists Tab
    with tabs[1]:
        st.header("Compare Two Playlists")
        
        if not sp:
            st.info("Please connect your Spotify account to compare playlists.")
        else:
            # Create two columns for playlist selection
            col1, col2 = st.columns(2)
            
            playlist_url_1 = None
            playlist_url_2 = None
            
            with col1:
                st.subheader("First Playlist")
                # Example playlists dropdown
                selected_example_1 = st.selectbox(
                    "Select an example playlist:",
                    [""] + list(example_playlists.keys()),
                    key="example_1"
                )
                
                if selected_example_1:
                    playlist_url_1 = example_playlists[selected_example_1]
                
                # Or enter URL manually
                manual_url_1 = st.text_input(
                    "Or enter a Spotify playlist URL:",
                    key="manual_url_1"
                )
                
                if manual_url_1:
                    playlist_url_1 = manual_url_1
            
            with col2:
                st.subheader("Second Playlist")
                # Example playlists dropdown
                selected_example_2 = st.selectbox(
                    "Select an example playlist:",
                    [""] + list(example_playlists.keys()),
                    key="example_2"
                )
                
                if selected_example_2:
                    playlist_url_2 = example_playlists[selected_example_2]
                
                # Or enter URL manually
                manual_url_2 = st.text_input(
                    "Or enter a Spotify playlist URL:",
                    key="manual_url_2"
                )
                
                if manual_url_2:
                    playlist_url_2 = manual_url_2
            
            # Compare button
            if st.button("Compare Playlists", use_container_width=True):
                if playlist_url_1 and playlist_url_2:
                    try:
                        with st.spinner("Analyzing playlists..."):
                            # Get audio features for both playlists
                            df1, attributes1 = get_playlist_audio_features(sp, playlist_url_1)
                            df2, attributes2 = get_playlist_audio_features(sp, playlist_url_2)
                            
                            if df1 is not None and df2 is not None:
                                # Get playlist names
                                try:
                                    playlist1_details = sp.playlist(playlist_url_1, fields="name")
                                    playlist1_name = playlist1_details['name']
                                except:
                                    playlist1_name = "Playlist 1"
                                    
                                try:
                                    playlist2_details = sp.playlist(playlist_url_2, fields="name")
                                    playlist2_name = playlist2_details['name']
                                except:
                                    playlist2_name = "Playlist 2"
                                
                                # Create comparison visualization
                                st.subheader("Audio Feature Comparison")
                                
                                # Prepare comparison data
                                comparison_data = {
                                    'Feature': [],
                                    'Value': [],
                                    'Playlist': []
                                }
                                
                                features = ["danceability", "energy", "valence", 
                                           "acousticness", "instrumentalness", "speechiness"]
                                
                                for feature in features:
                                    if feature in attributes1:
                                        comparison_data['Feature'].append(feature)
                                        comparison_data['Value'].append(attributes1[feature])
                                        comparison_data['Playlist'].append(playlist1_name)
                                    
                                    if feature in attributes2:
                                        comparison_data['Feature'].append(feature)
                                        comparison_data['Value'].append(attributes2[feature])
                                        comparison_data['Playlist'].append(playlist2_name)
                                
                                comparison_df = pd.DataFrame(comparison_data)
                                
                                # Create grouped bar chart
                                fig = px.bar(
                                    comparison_df,
                                    x='Feature',
                                    y='Value',
                                    color='Playlist',
                                    barmode='group',
                                    title="Audio Feature Comparison",
                                    color_discrete_sequence=['#1DB954', '#FF6B6B']
                                )
                                
                                fig.update_layout(
                                    xaxis_title="",
                                    yaxis_title="Value (0-1 Scale)",
                                    legend_title="Playlist"
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Create radar comparison
                                st.subheader("Radar Comparison")
                                
                                fig = go.Figure()
                                
                                # Add traces for each playlist
                                fig.add_trace(go.Scatterpolar(
                                    r=[attributes1.get(f, 0) for f in features],
                                    theta=features,
                                    fill='toself',
                                    name=playlist1_name,
                                    line_color='#1DB954'
                                ))
                                
                                fig.add_trace(go.Scatterpolar(
                                    r=[attributes2.get(f, 0) for f in features],
                                    theta=features,
                                    fill='toself',
                                    name=playlist2_name,
                                    line_color='#FF6B6B'
                                ))
                                
                                fig.update_layout(
                                    polar=dict(
                                        radialaxis=dict(
                                            visible=True,
                                            range=[0, 1]
                                        )
                                    ),
                                    showlegend=True,
                                    margin=dict(l=40, r=40, t=40, b=40)
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Track count comparison
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric(f"{playlist1_name}", f"{len(df1)} tracks")
                                with col2:
                                    st.metric(f"{playlist2_name}", f"{len(df2)} tracks")
                                
                                # Generate comparative analysis
                                st.subheader("🤖 AI Comparative Analysis")
                                
                                # Prepare attributes for both playlists
                                playlist1_attrs = {k: f"{v:.3f}" for k, v in attributes1.items()}
                                playlist2_attrs = {k: f"{v:.3f}" for k, v in attributes2.items()}
                                
                                # Use the LLM to generate a comparison
                                comparison_prompt = f"""Compare these two Spotify playlists:

Playlist 1 ({playlist1_name}) audio features:
{playlist1_attrs}

Playlist 2 ({playlist2_name}) audio features:
{playlist2_attrs}

Write a comparison focusing on:
1. The main differences in mood and energy
2. How the listening experience would differ
3. Which contexts each playlist would be better suited for

Be specific and analytical in your comparison.
"""
                                # Use Groq API to generate comparison
                                from groq_agent import generate_groq_response
                                
                                with st.spinner("Generating comparison..."):
                                    comparison_analysis = generate_groq_response(comparison_prompt)
                                    st.markdown(comparison_analysis)
                            else:
                                st.error("Failed to get data for one or both playlists.")
                    except Exception as e:
                        st.error(f"Error comparing playlists: {str(e)}")
                else:
                    st.warning("Please select or enter two playlists to compare.")
    
    # About Tab
    with tabs[2]:
        st.header("About AI Music Analyst")
        
        st.markdown("""
            ## How It Works
            
            **AI Music Analyst** uses the Spotify API to analyze the audio features of tracks in any public playlist. These features help describe the musical and emotional qualities of each track:
            
            - **Danceability**: How suitable a track is for dancing (0.0 = least danceable, 1.0 = most danceable)
            - **Energy**: A measure of intensity and activity (0.0 = least energetic, 1.0 = most energetic)
            - **Valence**: The musical positiveness conveyed by a track (0.0 = sad/serious, 1.0 = happy/cheerful)
            - **Acousticness**: Confidence measure of whether the track is acoustic (0.0 = electric, 1.0 = acoustic)
            - **Instrumentalness**: Predicts the likelihood a track has no vocals (1.0 = purely instrumental)
            - **Speechiness**: Detects the presence of spoken words (higher values = more speech-like content)
            
            After connecting your Spotify account, select a playlist to begin exploring its musical DNA through visualizations and AI-generated commentary.
            """)
if __name__ == "__main__":
    main()

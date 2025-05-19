from langchain.agents import Tool, initialize_agent
from langchain.agents.agent_types import AgentType
from langchain.llms import LlamaCpp
from spotify_tools import get_top_hits_data

# Define tool
def analyze_top_hits(_):
    data = get_top_hits_data()
    commentary = []

    high_dance = sorted(data, key=lambda x: x["danceability"], reverse=True)[:3]
    high_valence = sorted(data, key=lambda x: x["valence"], reverse=True)[:3]
    
    commentary.append("🎶 **Most danceable tracks:**")
    for t in high_dance:
        commentary.append(f"- {t['name']} by {t['artist']} (Danceability: {t['danceability']:.2f})")

    commentary.append("\n😄 **Happiest sounding tracks (valence):**")
    for t in high_valence:
        commentary.append(f"- {t['name']} by {t['artist']} (Valence: {t['valence']:.2f})")

    return "\n".join(commentary)

tools = [
    Tool(
        name="SpotifyTopHitsAnalyzer",
        func=analyze_top_hits,
        description="Analyzes Today's Top Hits on Spotify and returns trends in audio features."
    )
]

# Point to your GGUF model
llm = LlamaCpp(
    model_path="./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    temperature=0.7,
    max_tokens=1024,
    n_ctx=2048,
    verbose=True
)

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

import streamlit as st
from agent_runner import agent

st.set_page_config(page_title="Music Industry Analyst AI", page_icon="🎧")
st.title("🎧 Music Analyst AI Agent")

query = st.text_input("Ask the music analyst agent:", 
                      "What should we look for in our next signed artist?")

if st.button("Run Agent"):
    with st.spinner("Analyzing..."):
        response = agent.run(query)
        st.success("Done!")
        st.write(response)

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Streamlit web app for interacting with the Financial Advisor Agent."""

import asyncio
import os
import uuid
import vertexai
import streamlit as st # type: ignore
from dotenv import load_dotenv, dotenv_values
from vertexai import agent_engines


# --- Configuration ---

# Load environment variables from .env file
config = dotenv_values(".env")

PROJECT_ID = config.get("GOOGLE_CLOUD_PROJECT")
LOCATION = config.get("GOOGLE_CLOUD_LOCATION")
AGENT_ENGINE_NAME = config.get("AGENT_ENGINE_NAME")

# This is the specific agent engine deployment we will connect to.
# AGENT_ENGINE_NAME = "projects/799954743226/locations/us-central1/reasoningEngines/4933874811202961408"

# --- Page Setup ---

st.set_page_config(
    page_title="Financial Advisor Agent",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

# --- Initialization ---

@st.cache_resource
def init_vertexai():
    """Initialize the Vertex AI SDK."""
    print("Initializing Vertex AI...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    print("Vertex AI Initialized.")

@st.cache_resource
def init_agent_engine() -> agent_engines.AgentEngine:
    """Initialize the Agent Engine client."""
    print("Initializing AgentEngine...")
    if not AGENT_ENGINE_NAME:
        st.error(
            "AGENT_ENGINE_NAME environment variable is not set. "
            "Please set it to your deployed agent engine's resource name. "
            "e.g. projects/your-project-id/locations/us-central1/reasoningEngines/your-agent-id"
        )
        st.stop()
    print(f"Getting agent engine: {AGENT_ENGINE_NAME}")
    agent = agent_engines.get(AGENT_ENGINE_NAME)
    print("AgentEngine Initialized.")
    return agent

init_vertexai()
agent = init_agent_engine()

def create_new_session():
    """Creates a new session and updates the session state."""
    print("Creating a new session...")
    st.info("Creating a new session...")
    new_session_obj = agent.create_session(user_id=st.session_state.user_id)
    st.session_state.session_id = new_session_obj["id"]
    st.session_state.sessions.append(new_session_obj)
    st.session_state.messages[st.session_state.session_id] = []
    print(f"New session created: {st.session_state.session_id}")
# --- Session State Management ---

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "sessions" not in st.session_state:
    st.session_state.sessions = []
if "messages" not in st.session_state:
    st.session_state.messages = {}
if "user_id" not in st.session_state:
    st.session_state.user_id = f"streamlit-user-{uuid.uuid4()}"

# --- Sidebar for Session Control ---

with st.sidebar:
    st.title("Conversation")

    # Button to create a new session
    if st.button("New Chat"):
        create_new_session()
        st.rerun()

    # Dropdown to select a session
    if st.session_state.sessions:
        # Create a list of session IDs for the dropdown
        session_options = [s["id"] for s in st.session_state.sessions]
        # If there's an active session, find its index
        try:
            current_session_index = session_options.index(st.session_state.session_id)
        except (ValueError, TypeError):
            current_session_index = 0 # Default to the first session if not found

        # Display the dropdown
        selected_session_id = st.selectbox(
            "Choose a session:",
            session_options,
            index=current_session_index,
            key="session_selector"
        )

        # If the selected session is different from the active one, update it
        if selected_session_id and selected_session_id != st.session_state.session_id:
            st.session_state.session_id = selected_session_id
            st.rerun()

# --- Main Chat Interface ---

st.title("📈 Financial Advisor Agent")
st.write(
    "Welcome! I can help you analyze market tickers, develop trading strategies, and more."
)

# Create a new session
if not st.session_state.session_id:
    create_new_session()
    st.rerun()

chat_tab, state_tab = st.tabs(["Chat", "Session State"])

# Handle user input at the bottom of the page
if prompt := st.chat_input("What would you like to analyze?"):
    print("\n--- New User Input ---")
    # Display user message and add to history
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.setdefault(st.session_state.session_id, []).append(
        {"role": "user", "content": prompt}
    )

    # Stream agent response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        # Use an async function to handle the streaming call
        async def get_response_and_session(prompt: str) -> tuple[str, dict]:
            """Streams the agent's response and returns the full content and updated session."""
            full_response_content = ""
            print("Streaming agent response...")
            response_stream = agent.async_stream_query(
                message=prompt,
                user_id=st.session_state.user_id,
                session_id=st.session_state.session_id,
            )
            print("--- Agent Chunks ---")
            async for chunk in response_stream:
                print(chunk)
                # Handle dictionary chunks with content
                if isinstance(chunk, dict) and "content" in chunk and "parts" in chunk["content"]:
                    for part in chunk["content"]["parts"]:
                        if "text" in part:
                            full_response_content += part["text"]
                            message_placeholder.markdown(full_response_content + "▌")
                # Handle simple string chunks
                elif isinstance(chunk, str):
                    full_response_content += chunk
                    message_placeholder.markdown(full_response_content + "▌")
            message_placeholder.markdown(full_response_content)
            print("--- End of Agent Chunks ---")
            print("Stream complete.")

            print("Getting updated session...")
            updated_session = await agent.async_get_session(
                session_id=st.session_state.session_id, user_id=st.session_state.user_id
            )
            print("Session retrieved.")
            return full_response_content, updated_session

        print("Running get_response_and_session...")
        full_response, updated_session_obj = asyncio.run(get_response_and_session(prompt))
        print("get_response_and_session finished.")

    # Add agent response to history
    st.session_state.messages[st.session_state.session_id].append(
        {"role": "assistant", "content": full_response}
    )

    # Update the session object in the list
    for i, s in enumerate(st.session_state.sessions):
        if s["id"] == st.session_state.session_id:
            st.session_state.sessions[i] = updated_session_obj
            break

    # Rerun to display the new agent message
    st.rerun()

with chat_tab:
    # Display chat messages for the active session
    if st.session_state.session_id:
        for message in st.session_state.messages.get(st.session_state.session_id, []):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

with state_tab:
    st.header("Current ADK Session State")
    if st.session_state.session_id:
        # Find the current session object
        current_session_obj = next((s for s in st.session_state.sessions if s["id"] == st.session_state.session_id), None)
        if current_session_obj:
            st.json(current_session_obj)
        else:
            st.warning("Could not find the selected session object.")
    else:
        st.info("No active session.")

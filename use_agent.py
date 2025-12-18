"""
Simple script to use the deployed Financial Advisor Agent with streaming and session support.
"""

import sys
import os
import asyncio
import uuid
import vertexai
from dotenv import load_dotenv
from vertexai import agent_engines

async def main():
    # 0. Load environment variables
    load_dotenv()
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"

    # 1. Parse Agent Engine Resource ID
    if len(sys.argv) < 2:
        print('Usage: python use_agent.py <AGENT_ENGINE_RESOURCE_ID>')
        print('Example: python use_agent.py projects/my-project/locations/us-central1/reasoningEngines/123456')
        sys.exit(1)

    engine_name = sys.argv[1]
    
    # Format the engine name if only the numeric ID was provided
    if not engine_name.startswith("projects/"):
        if not project_id:
            print("Error: GOOGLE_CLOUD_PROJECT environment variable is required if only the ID is provided.")
            sys.exit(1)
        engine_name = f"projects/{project_id}/locations/{location}/reasoningEngines/{engine_name}"

    print(f"Connecting to Agent Engine: {engine_name}")
    print(f"Project: {project_id}, Location: {location}")
    
    # 2. Initialize Vertex AI
    vertexai.init(project=project_id, location=location)

    # 3. Get the Remote Agent
    try:
        remote_agent = agent_engines.get(engine_name)
        print(f"Successfully connected to: {remote_agent.resource_name}")
    except Exception as e:
        print(f"Error connecting to agent: {e}")
        return

    # 4. Create a Session
    # Use USER_ID from environment if available, otherwise generate a demo one.
    user_id = os.getenv("USER_ID") or ("demo_user_" + str(uuid.uuid4())[:4])
    try:
        session = remote_agent.create_session(user_id=user_id)
        session_id = session["id"]
        print(f"Created session: {session_id} for user: {user_id}")
    except Exception as e:
        print(f"Error creating session: {e}")
        return

    # 5. Query the Agent with Streaming
    user_query = "I want to invest in tech stocks. Can you suggest a strategy for a 10-year horizon with moderate risk?"
    
    print(f"\n--- User Query ---\n{user_query}")
    print("\n--- Agent Response (Streaming...) ---\n")
    
    try:
        # Use async_stream_query with session support
        async for event in remote_agent.async_stream_query(
            user_id=user_id,
            session_id=session_id,
            message=user_query
        ):
            # Extract text from translation/content events
            if "content" in event and "parts" in event["content"]:
                for part in event["content"]["parts"]:
                    if "text" in part:
                        print(part["text"], end="", flush=True)
            elif isinstance(event, str):
                print(event, end="", flush=True)
                
        print("\n\n--- Stream Completed ---")
    except Exception as e:
        print(f"\nError during streaming query: {e}")

if __name__ == "__main__":
    asyncio.run(main())

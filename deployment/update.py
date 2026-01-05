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

"""Update script for Financial Advisor"""

import os
import sys

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import vertexai
from dotenv import dotenv_values
from agent.agent import root_agent
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp


def update(engine_name: str) -> None:
    """Updates an existing agent engine deployment."""
    # AdkApp wraps our agent logic for deployment.
    # enable_tracing=True enables application-level tracing.
    adk_app = AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )

    print(f"Updating agent engine: {engine_name} with agent: {root_agent.name}...")

    # Update the agent in Vertex AI Agent Engine
    remote_agent = agent_engines.update(
        resource_name=engine_name,
        agent_engine=adk_app,
    )
    print(f"Successfully updated remote agent: {remote_agent.resource_name}")


def main() -> None:
    """Main update flow."""
    config = dotenv_values(".env")

    project_id = config.get("GOOGLE_CLOUD_PROJECT")
    location = config.get("GOOGLE_CLOUD_LOCATION")
    bucket = config.get("GOOGLE_CLOUD_STORAGE_BUCKET")

    if len(sys.argv) < 2:
        print("Usage: python update.py <AGENT_ENGINE_RESOURCE_ID>")
        sys.exit(1)

    engine_name = sys.argv[1]

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=f"gs://{bucket}",
    )

    update(engine_name=engine_name)


if __name__ == "__main__":
    main()


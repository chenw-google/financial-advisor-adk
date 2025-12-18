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

"""Deployment script for Financial Advisor"""

import os

import vertexai
from dotenv import load_dotenv
from financial_advisor.agent import root_agent
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

def create() -> None:
    """Creates an agent engine for Financial Advisors with telemetry enabled."""
    # AdkApp wraps our agent logic for deployment. 
    # enable_tracing=True enables application-level tracing.
    adk_app = AdkApp(agent=root_agent, enable_tracing=True)

    print(f"Deploying agent: {root_agent.name}...")

    # Deploy the agent to Vertex AI Agent Engine
    remote_agent = agent_engines.create(
        adk_app,
        display_name=root_agent.name,
        requirements=[
            "google-adk (>=0.0.2)",
            "google-cloud-aiplatform[agent_engines] (>=1.91.0,!=1.92.0)",
            "google-genai (>=1.5.0,<2.0.0)",
            "pydantic (>=2.10.6,<3.0.0)",
            "absl-py (>=2.2.1,<3.0.0)",
        ],
        # Enable tracing and telemetry via environment variables
        env_vars={
            "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
        }
    )
    print(f"Successfully created remote agent: {remote_agent.resource_name}")


def delete(resource_id: str) -> None:
    """Deletes an existing agent."""
    remote_agent = agent_engines.get(resource_id)
    remote_agent.delete(force=True)
    print(f"Deleted remote agent: {resource_id}")


def list_agents() -> None:
    """Lists all remote agents."""
    remote_agents = agent_engines.list()
    template = """
{agent.name} ("{agent.display_name}")
- Create time: {agent.create_time}
- Update time: {agent.update_time}
"""
    remote_agents_string = "\n".join(
        template.format(agent=agent) for agent in remote_agents
    )
    print(f"All remote agents:\n{remote_agents_string}")


def main() -> None:
    """Main deployment flow."""
    load_dotenv()

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    bucket = os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")

    print(f"PROJECT: {project_id}")
    print(f"LOCATION: {location}")
    print(f"BUCKET: {bucket}")

    if not project_id:
        print("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
        return
    if not location:
        print("Missing required environment variable: GOOGLE_CLOUD_LOCATION")
        return
    if not bucket:
        print("Missing required environment variable: GOOGLE_CLOUD_STORAGE_BUCKET")
        return

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=f"gs://{bucket}",
    )

    # Simplified to always create by default in the main demo flow
    create()



if __name__ == "__main__":
    main()

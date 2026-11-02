"""Microsoft Foundry agent client."""

from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from src.services.foundry.response import parse_response


class FoundryClient:
    """Send prompts to a Microsoft Foundry agent."""

    def __init__(
        self,
        project_endpoint: str,
        agent_name: str,
        agent_version: str | None = None,
    ) -> None:
        """Create a Foundry client using the current Azure identity."""
        self.agent_name = agent_name
        self.agent_version = agent_version
        project = AIProjectClient(
            endpoint=project_endpoint,
            credential=DefaultAzureCredential(),
        )
        self._openai = project.get_openai_client()

    def run(self, prompt: str) -> Any:
        """Send a prompt and parse the agent response."""
        agent_reference = {
            "type": "agent_reference",
            "name": self.agent_name,
        }
        if self.agent_version:
            agent_reference["version"] = self.agent_version
        response = self._openai.responses.create(
            input=prompt,
            extra_body={"agent_reference": agent_reference},
        )
        return parse_response(response.output_text)

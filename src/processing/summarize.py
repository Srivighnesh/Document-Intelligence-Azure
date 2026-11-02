"""Document text summarization through Foundry."""

from typing import Any

from src.processing.extractors import EXTRACTORS
from src.processing.profiles import Profile
from src.services.foundry.client import FoundryClient


def run_agent(
    analysis: dict[str, Any],
    profile: Profile,
    client: FoundryClient,
) -> Any:
    """Extract analysis text and send the profile prompt to Foundry."""
    text = EXTRACTORS[profile.kind](analysis, profile)
    return client.run(profile.prompt.replace("{data}", text))

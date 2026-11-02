"""Send a Document Intelligence OCR result to a Foundry agent."""

import argparse
import json
import os
from typing import Any

from src import config
from src.processing.profiles import get_profile
from src.processing.summarize import run_agent
from src.services.foundry.client import FoundryClient


def save_response(response: Any, source_name: str) -> str:
    """Save the agent response beside the OCR result."""
    result_directory = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "results",
    )
    os.makedirs(result_directory, exist_ok=True)
    output_path = os.path.join(
        result_directory,
        f"{os.path.splitext(os.path.basename(source_name))[0]}_foundry_result.json",
    )
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(response, output_file, indent=2, ensure_ascii=False)
    return output_path


def main() -> None:
    """Invoke the configured Foundry agent with an OCR JSON file."""
    parser = argparse.ArgumentParser(
        description="Send OCR output to a Microsoft Foundry agent."
    )
    parser.add_argument("ocr_file", help="Path to an OCR result JSON file.")
    parser.add_argument("--endpoint", default=config.FOUNDRY_PROJECT_ENDPOINT)
    parser.add_argument("--agent-name", default=config.FOUNDRY_AGENT_NAME)
    parser.add_argument(
        "--agent-version",
        default=config.FOUNDRY_AGENT_VERSION,
    )
    parser.add_argument("--model-id", default=config.DOCUMENT_INTELLIGENCE_MODEL_ID)
    arguments = parser.parse_args()

    if not arguments.endpoint:
        raise ValueError("Set FOUNDRY_PROJECT_ENDPOINT or pass --endpoint.")
    if not arguments.agent_name:
        raise ValueError("Set FOUNDRY_AGENT_NAME or pass --agent-name.")

    profile = get_profile(arguments.model_id)
    with open(arguments.ocr_file, encoding="utf-8") as ocr_file:
        ocr = json.load(ocr_file)
    client = FoundryClient(
        project_endpoint=arguments.endpoint,
        agent_name=arguments.agent_name,
        agent_version=arguments.agent_version,
    )
    response = run_agent(ocr, profile, client)
    output_path = save_response(response, arguments.ocr_file)
    print(f"Foundry response saved to: {output_path}")


if __name__ == "__main__":
    main()

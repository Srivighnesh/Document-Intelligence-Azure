"""Send a Document Intelligence OCR result to a Foundry agent."""

import argparse

from src import config
from src.services.foundry_agent import FoundryAgentClient


def main() -> None:
    """Invoke the configured Foundry agent with an OCR JSON file."""
    parser = argparse.ArgumentParser(
        description="Send OCR output to a Microsoft Foundry agent."
    )
    parser.add_argument("ocr_file", help="Path to an OCR result JSON file.")
    parser.add_argument("--endpoint", default=config.FOUNDRY_PROJECT_ENDPOINT)
    parser.add_argument("--agent-name", default=config.FOUNDRY_AGENT_NAME)
    parser.add_argument("--agent-version", default=config.FOUNDRY_AGENT_VERSION)
    parser.add_argument(
        "--fields",
        default=",".join(config.FOUNDRY_REQUESTED_FIELDS),
        help="Comma-separated output field names.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=config.FOUNDRY_MAX_OCR_CHARS,
        help="Maximum selected OCR characters sent to Foundry.",
    )
    arguments = parser.parse_args()

    if not arguments.endpoint:
        raise ValueError("Set FOUNDRY_PROJECT_ENDPOINT or pass --endpoint.")
    if not arguments.agent_name:
        raise ValueError("Set FOUNDRY_AGENT_NAME or pass --agent-name.")

    client = FoundryAgentClient(
        project_endpoint=arguments.endpoint,
        agent_name=arguments.agent_name,
        agent_version=arguments.agent_version,
        max_ocr_chars=arguments.max_chars,
        requested_fields=[
            field.strip()
            for field in arguments.fields.split(",")
            if field.strip()
        ],
    )
    response = client.analyze_ocr_file(arguments.ocr_file)
    output_path = client.save_response(response, arguments.ocr_file)
    print(f"Foundry response saved to: {output_path}")


if __name__ == "__main__":
    main()

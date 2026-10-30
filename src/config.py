"""Application configuration backed by environment variables and Azure Key Vault."""

import os
from functools import lru_cache

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv

load_dotenv()


def _required_environment(name: str) -> str:
    """Return a required non-secret environment value."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@lru_cache(maxsize=1)
def _secret_client() -> SecretClient:
    """Create one Key Vault client using Microsoft Entra authentication."""
    return SecretClient(
        vault_url=_required_environment("AZURE_KEY_VAULT_URL"),
        credential=DefaultAzureCredential(),
    )


@lru_cache(maxsize=None)
def get_secret(name: str) -> str:
    """Retrieve a non-empty secret without exposing its value."""
    try:
        secret = _secret_client().get_secret(name)
    except ResourceNotFoundError as error:
        raise RuntimeError(f"Key Vault secret is missing: {name}") from error
    except AzureError as error:
        raise RuntimeError(
            f"Unable to retrieve Key Vault secret '{name}'. "
            "Check Azure authentication and Key Vault permissions."
        ) from error

    if not secret.value:
        raise RuntimeError(f"Key Vault secret is empty: {name}")
    return secret.value


def _get_endpoint(name: str, legacy_name: str | None = None) -> str:
    """Retrieve an endpoint from Key Vault, with a legacy-name fallback."""
    try:
        return get_secret(name)
    except RuntimeError as error:
        if legacy_name and "secret is missing" in str(error):
            return get_secret(legacy_name)
        raise


# Endpoints and the Document Intelligence key are never read from .env.
DOCUMENT_INTELLIGENCE_ENDPOINT = _get_endpoint("DocumentIntelligenceEndpoint")
DOCUMENT_INTELLIGENCE_KEY = get_secret(
    os.getenv(
        "DOCUMENT_INTELLIGENCE_KEY_SECRET_NAME",
        "DocumentIntelligenceKey",
    )
)
FOUNDRY_PROJECT_ENDPOINT = _get_endpoint("FoundryEndpoint")
AZURE_STORAGE_ACCOUNT_URL = _get_endpoint(
    "AzureBlobStorageUrl",
    legacy_name="AzureBlobStorageURl",
)

# These are non-secret application settings.
AZURE_STORAGE_CONTAINER_NAME = _required_environment(
    "AZURE_STORAGE_CONTAINER_NAME"
)
DOCUMENT_INTELLIGENCE_MODEL_ID = os.getenv(
    "DOCUMENT_INTELLIGENCE_MODEL_ID",
    "prebuilt-layout",
)
FOUNDRY_AGENT_NAME = _required_environment("FOUNDRY_AGENT_NAME")
FOUNDRY_AGENT_VERSION = os.getenv("FOUNDRY_AGENT_VERSION")
FOUNDRY_MAX_OCR_CHARS = int(os.getenv("FOUNDRY_MAX_OCR_CHARS", "1500"))
FOUNDRY_REQUESTED_FIELDS = tuple(
    field.strip()
    for field in os.getenv("FOUNDRY_REQUESTED_FIELDS", "").split(",")
    if field.strip()
)

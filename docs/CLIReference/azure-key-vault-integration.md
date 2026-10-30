# Azure Key Vault Integration Guide

Modify your Python application to retrieve endpoints and API keys from **Azure Key Vault** instead of storing secrets in `.env`.

The existing **Document Intelligence → Microsoft Foundry** workflow should remain unchanged. Use `DefaultAzureCredential` for authentication.

## Step 1 — Install the required packages

Run this in your activated virtual environment:

```powershell
python -m pip install azure-identity azure-keyvault-secrets python-dotenv
```

## Step 2 — Update `.env`

Keep only the Key Vault URL and non-secret configuration in `.env`:

```dotenv
AZURE_KEY_VAULT_URL=https://kv-docintel-sv-2026-01.vault.azure.net/
AZURE_STORAGE_ACCOUNT_URL=https://rstoredi2026.blob.core.windows.net/
AZURE_STORAGE_CONTAINER_NAME=documents
```

Do not remove the existing Document Intelligence or Foundry API keys until you have confirmed that Key Vault integration works. After verification, remove them from `.env` and ensure `.env` is excluded from Git.

## Step 3 — Create `src/config.py`

This file loads configuration and secrets from Key Vault:

```python
import os

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv

# Load non-secret configuration for local development.
load_dotenv()

# Authenticate using Azure CLI locally or managed identity in Azure.
credential = DefaultAzureCredential()

# Connect to the existing Key Vault.
vault_url = os.environ["AZURE_KEY_VAULT_URL"]
secret_client = SecretClient(
    vault_url=vault_url,
    credential=credential,
)


def get_secret(name: str) -> str:
    """Retrieve the latest secret value from Key Vault."""
    secret = secret_client.get_secret(name)

    if not secret.value:
        raise ValueError(f"Key Vault secret '{name}' is empty.")

    return secret.value


# Load service endpoints and credentials securely.
DOCUMENT_INTELLIGENCE_ENDPOINT = get_secret(
    "DocumentIntelligenceEndpoint"
)
DOCUMENT_INTELLIGENCE_KEY = get_secret(
    "DocumentIntelligenceKey"
)
FOUNDRY_ENDPOINT = get_secret("FoundryEndpoint")
```

Create these secrets in your Key Vault with the exact names:

- `DocumentIntelligenceEndpoint`
- `DocumentIntelligenceKey`
- `FoundryEndpoint`

If your existing Foundry client uses key-based authentication, store its API key as a Key Vault secret too, and retrieve it through `get_secret()`. Do not add a Foundry API key unless the current SDK configuration requires one.

## Step 4 — Give your application permission

### Local development

In the Azure Portal:

1. Open your Key Vault.
2. Select **Access control (IAM)**.
3. Select **Add → Add role assignment**.
4. Assign **Key Vault Secrets User** to your Azure account.

In the CLI: [keyValultAcess](docs\CLIReference\keyValultAcess.md)


Then sign in from PowerShell:

```powershell
az login
```

The account selected by `DefaultAzureCredential` must have permission to read secrets.

### Production

Assign **Key Vault Secrets User** to the application's managed identity. Enable the managed identity for the hosting service first. Avoid storing credentials in source code.

## Step 5 — Update your existing service files

### Document Intelligence service

In `src/services/document_service.py` (or wherever the Document Intelligence client is initialized), import the configuration:

```python
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

from src.config import (
    DOCUMENT_INTELLIGENCE_ENDPOINT,
    DOCUMENT_INTELLIGENCE_KEY,
)

document_client = DocumentIntelligenceClient(
    endpoint=DOCUMENT_INTELLIGENCE_ENDPOINT,
    credential=AzureKeyCredential(DOCUMENT_INTELLIGENCE_KEY),
)
```

Adapt the import path to your existing package structure. If the project already creates the client in a different module, update that initialization rather than creating a duplicate client.

### Microsoft Foundry service

Import `FOUNDRY_ENDPOINT` from `src.config` and use it in the existing client initialization. If the Foundry client requires an API key, retrieve that key from Key Vault using `get_secret()`.

**Important:** Do not replace the Foundry client constructor blindly. Foundry projects and model deployments can use different SDKs and authentication patterns. Preserve the existing Document Intelligence → Foundry workflow and its current business logic.

## Step 6 — Test the integration

Run the existing FastAPI application using the entry point that matches your project.

For example, if `api.py` exposes `app` from the project root:

```powershell
uvicorn api:app --reload
```

If your entry point is `src/main.py`, use the appropriate module path, such as:

```powershell
uvicorn src.main:app --reload
```

Then process a test document and confirm that the existing workflow succeeds.

### Troubleshooting

- **Authentication error:** Run `az login` and verify the intended Azure subscription/account.
- **403 Forbidden:** Confirm the signed-in account or managed identity has the **Key Vault Secrets User** role on the correct vault.
- **Secret not found:** Verify the secret names and that the secrets are enabled.
- **`PublicAccessNotPermitted` storage error:** Check that `AZURE_KEY_VAULT_URL` is the Key Vault URI returned by `az keyvault show`, not the Blob Storage URL. Do not enable anonymous Blob access to work around this error.
- **Import error:** Run the application from the project root and use imports that match the existing package structure.

## Security checklist

- [ ] Confirm all required secrets can be retrieved from Key Vault.
- [ ] Confirm the document-processing workflow works end to end.
- [ ] Remove old API keys from `.env` only after successful verification.
- [ ] Ensure `.env` is listed in `.gitignore`.
- [ ] Check that API keys have not been committed to Git; rotate any exposed keys.
- [ ] Never print secret values in logs or terminal output.

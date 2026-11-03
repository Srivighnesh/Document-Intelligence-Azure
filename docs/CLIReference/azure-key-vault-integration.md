# Azure Key Vault Integration Guide

This repository already reads Document Intelligence and Blob Storage settings
from **Azure Key Vault** through `src/config.py` and authenticates with
`DefaultAzureCredential`.

The existing **Document Intelligence → Microsoft Foundry** workflow should remain unchanged. Use `DefaultAzureCredential` for authentication.

## Step 1 — Install the required packages

Install the repository dependencies in the project virtual environment:

```powershell
python -m pip install -r requirements.txt
```

## Step 2 — Update `.env`

Keep only the Key Vault URL and non-secret configuration in `.env`:

```dotenv
AZURE_KEY_VAULT_URL=https://<key-vault-name>.vault.azure.net/
AZURE_STORAGE_CONTAINER_NAME=<existing-container>
DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-layout
FOUNDRY_ENABLED=false
```

The Blob account URL, Document Intelligence endpoint, and Document Intelligence
key are read from Key Vault. Foundry settings are optional and loaded only
when `FOUNDRY_ENABLED=true`.

## Step 3 — Configure the existing `src/config.py`

The application already loads the required secrets. Create these in Key Vault
with the exact names:

- `DocumentIntelligenceEndpoint`
- `DocumentIntelligenceKey`
- `AzureBlobStorageUrl` (legacy fallback: `AzureBlobStorageURl`)
- `FoundryEndpoint` (only when Foundry is enabled)

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

## Step 5 — Use the existing service wrappers

### Document Intelligence service

The project already creates the Document Intelligence client in
`src/services/document_intelligence.py` and Blob client in
`src/services/blob_storage.py`. These wrappers use the configured Key Vault
values and `DefaultAzureCredential`; do not create duplicate clients.

Foundry remains disabled by default. When enabling it, configure the
`FoundryEndpoint` secret and agent settings described in `.env.example`.

## Step 6 — Test the integration

Run the existing FastAPI application using the entry point that matches your project.

Start the API from the project root:

```powershell
uvicorn Backend.api:app --reload
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

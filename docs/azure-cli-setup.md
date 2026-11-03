# Create Azure Resources with Azure CLI

This guide creates the Azure resources used by this project and assigns the
roles needed by the local developer account:

- Azure AI Document Intelligence
- Azure Blob Storage and a container
- Azure Key Vault
- Optional: a Microsoft Foundry account and project (only if enabling Foundry)

The API uses `DefaultAzureCredential`, so these role assignments are for the
identity you sign in with using `az login`. You need Azure CLI 2.80.0 or later
for Foundry project commands, and permission to create resources and assign
roles. An Owner can do both; Contributor can create resources but cannot assign
roles.

## 1. Sign in and set names

Replace the sample names and choose a region supported by the Azure services in
your subscription. Storage account names must be globally unique and contain
only lowercase letters and numbers. Key Vault and Foundry names must also be
globally unique.

```powershell
az version
az login
az account set --subscription "<subscription-id>"
az account show --query "{subscription:name,id:id}" --output table

$LOCATION = "eastus"
$RESOURCE_GROUP = "rg-document-intelligence-dev"
$DI_NAME = "<unique-document-intelligence-name>"
$STORAGE_NAME = "<globally-unique-storage-name>"
$CONTAINER = "documents"
$KEY_VAULT = "<globally-unique-key-vault-name>"
# Optional: only if enabling Foundry
$FOUNDRY_NAME = "<globally-unique-foundry-name>"
$FOUNDRY_PROJECT = "document-summary"
```

If `az version` is older than 2.80.0, run `az upgrade` before continuing.

## 2. Create the resources

```powershell
az group create --name $RESOURCE_GROUP --location $LOCATION
az provider register --namespace Microsoft.CognitiveServices

az cognitiveservices account create `
  --name $DI_NAME `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --kind FormRecognizer `
  --sku S0 `
  --yes

az storage account create `
  --name $STORAGE_NAME `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --sku Standard_LRS `
  --kind StorageV2 `
  --allow-blob-public-access false

az keyvault create `
  --name $KEY_VAULT `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --enable-rbac-authorization true `
  --enable-purge-protection true

# Optional: only if enabling Foundry
az cognitiveservices account create `
  --name $FOUNDRY_NAME `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --kind AIServices `
  --sku S0 `
  --custom-domain $FOUNDRY_NAME `
  --assign-identity `
  --allow-project-management true `
  --yes

az cognitiveservices account project create `
  --name $FOUNDRY_NAME `
  --resource-group $RESOURCE_GROUP `
  --project-name $FOUNDRY_PROJECT `
  --location $LOCATION
```

## 3. Assign roles to your signed-in account

Run these commands as an account that can create role assignments. The role
assignments can take a few minutes to take effect.

```powershell
$USER_ID = az ad signed-in-user show --query id --output tsv
$STORAGE_ID = az storage account show `
  --name $STORAGE_NAME --resource-group $RESOURCE_GROUP --query id --output tsv
$VAULT_ID = az keyvault show `
  --name $KEY_VAULT --resource-group $RESOURCE_GROUP --query id --output tsv
# Optional: only if enabling Foundry
$PROJECT_ID = az cognitiveservices account project show `
  --name $FOUNDRY_NAME `
  --resource-group $RESOURCE_GROUP `
  --project-name $FOUNDRY_PROJECT `
  --query id --output tsv

az role assignment create --assignee-object-id $USER_ID --assignee-principal-type User --role "Storage Blob Data Contributor" --scope $STORAGE_ID
az role assignment create --assignee-object-id $USER_ID --assignee-principal-type User --role "Key Vault Secrets User" --scope $VAULT_ID
az role assignment create --assignee-object-id $USER_ID --assignee-principal-type User --role "Key Vault Secrets Officer" --scope $VAULT_ID
# Optional: only if enabling Foundry
az role assignment create --assignee-object-id $USER_ID --assignee-principal-type User --role "53ca6127-db72-4b80-b1b0-d745d6d5456d" --scope $PROJECT_ID
```

`Key Vault Secrets User` lets the app read secrets. `Key Vault Secrets Officer`
lets your account add the secrets in the next step. The Foundry role ID is the
current `Foundry User` role. The project-level assignment lets the signed-in
account invoke the configured project agent.

Create the Blob container using Microsoft Entra authentication:

```powershell
az storage container create `
  --name $CONTAINER `
  --account-name $STORAGE_NAME `
  --auth-mode login
```

## 4. Save the app settings in Key Vault

The app expects these exact secret names. The Document Intelligence key is
captured in a PowerShell variable and sent directly to Key Vault; don't print
it or save it in `.env`.

```powershell
$DI_ENDPOINT = az cognitiveservices account show `
  --name $DI_NAME --resource-group $RESOURCE_GROUP `
  --query properties.endpoint --output tsv
$DI_KEY = az cognitiveservices account keys list `
  --name $DI_NAME --resource-group $RESOURCE_GROUP `
  --query key1 --output tsv
# Optional: only if enabling Foundry
$FOUNDRY_ENDPOINT = az cognitiveservices account project show `
  --name $FOUNDRY_NAME `
  --resource-group $RESOURCE_GROUP `
  --project-name $FOUNDRY_PROJECT `
  --query 'properties.endpoints."AI Foundry API"' --output tsv
$STORAGE_URL = az storage account show `
  --name $STORAGE_NAME --resource-group $RESOURCE_GROUP `
  --query primaryEndpoints.blob --output tsv

az keyvault secret set --vault-name $KEY_VAULT --name DocumentIntelligenceEndpoint --value $DI_ENDPOINT --output none
az keyvault secret set --vault-name $KEY_VAULT --name DocumentIntelligenceKey --value $DI_KEY --output none
# Optional: only if enabling Foundry
az keyvault secret set --vault-name $KEY_VAULT --name FoundryEndpoint --value $FOUNDRY_ENDPOINT --output none
az keyvault secret set --vault-name $KEY_VAULT --name AzureBlobStorageUrl --value $STORAGE_URL --output none

$env:AZURE_KEY_VAULT_URL = "https://$KEY_VAULT.vault.azure.net/"
$env:AZURE_STORAGE_CONTAINER_NAME = $CONTAINER
$env:DOCUMENT_INTELLIGENCE_MODEL_ID = "prebuilt-layout"
# Optional: only if enabling Foundry
$env:FOUNDRY_ENABLED = "false"
# Set true and configure these when enabling Foundry.
# $env:FOUNDRY_AGENT_NAME = "<agent-name-created-in-foundry>"
# $env:FOUNDRY_AGENT_VERSION = "1"
```

Put the non-secret environment values in the project-root `.env` for future
sessions. Do not put the Document Intelligence key or other credentials in
`.env`:

```env
AZURE_KEY_VAULT_URL=https://<key-vault-name>.vault.azure.net/
AZURE_STORAGE_CONTAINER_NAME=documents
DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-layout
FOUNDRY_ENABLED=false
# Optional: only if enabling Foundry
# FOUNDRY_AGENT_NAME=<agent-name-created-in-foundry>
# FOUNDRY_AGENT_VERSION=1
```

## 5. Optional: only if enabling Foundry — create the Foundry agent

The project code calls an agent by name and version. Sign in at
[Microsoft Foundry](https://ai.azure.com), open the project you created, deploy
a model available in your region, and create an agent that uses that model.
Then set `FOUNDRY_AGENT_NAME` and `FOUNDRY_AGENT_VERSION` in `.env` to match.

## Roles at a glance

| Identity | Scope | Role | Why |
|---|---|---|---|
| Signed-in developer | Storage account | Storage Blob Data Contributor | Upload original files and OCR JSON |
| Signed-in developer | Key Vault | Key Vault Secrets User | Read app configuration secrets |
| Signed-in developer | Key Vault | Key Vault Secrets Officer | Create/update the app secrets |
| Signed-in developer | Foundry project | Foundry User | Use the project agent |

For a deployed API, assign the same runtime roles to the API's managed identity
instead of a developer user. Do not give the deployed API `Key Vault Secrets
Officer`; it only needs `Key Vault Secrets User`. Role assignments must be made
by an identity with role-assignment permission at each resource scope.

## Verify and clean up

Check the resources and role assignments:

```powershell
az cognitiveservices account show --name $DI_NAME --resource-group $RESOURCE_GROUP --query "{name:name,kind:kind,state:properties.provisioningState}" --output table
az storage account show --name $STORAGE_NAME --resource-group $RESOURCE_GROUP --query "{name:name,location:location}" --output table
az keyvault show --name $KEY_VAULT --resource-group $RESOURCE_GROUP --query "{name:name,location:location}" --output table
az role assignment list --assignee $USER_ID --resource-group $RESOURCE_GROUP --query "[].{role:roleDefinitionName,scope:scope}" --output table
```

To delete everything created in this guide, delete the resource group. This
permanently deletes every resource inside it:

```powershell
az group delete --name $RESOURCE_GROUP --yes --no-wait
```

For app startup and API usage, see the [README](../README.md).

## References

- [Microsoft Foundry resource and project quickstart](https://learn.microsoft.com/azure/foundry/tutorials/quickstart-create-foundry-resources?tabs=azurecli)
- [Azure CLI: Cognitive Services accounts and projects](https://learn.microsoft.com/cli/azure/cognitiveservices/account/project?view=azure-cli-latest)
- [Azure CLI: Storage accounts](https://learn.microsoft.com/cli/azure/storage/account?view=azure-cli-latest)
- [Azure CLI: Key Vault secrets](https://learn.microsoft.com/cli/azure/keyvault/secret?view=azure-cli-latest)
- [Microsoft Foundry RBAC](https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry)
- [Azure Blob Storage role assignment](https://learn.microsoft.com/azure/storage/common/storage-auth-aad-rbac-cli)

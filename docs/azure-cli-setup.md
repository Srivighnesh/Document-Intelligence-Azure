# Azure CLI Resource Setup

This guide provisions the Azure resources used by this project:

1. A resource group.
2. An Azure AI Document Intelligence resource for OCR.
3. Optionally, a Microsoft Foundry account and project for agent summaries.

The commands are written for PowerShell. Replace every value in angle brackets
before running them.

## Prerequisites

Install and sign in to Azure CLI:

```powershell
az login
az account set --subscription "<subscription-id>"
az extension add --name cognitiveservices
```

Confirm the active subscription:

```powershell
az account show --query "{name:name,id:id,tenantId:tenantId}" -o table
```

## Set deployment variables

Choose a region available for your subscription. The region is important:
Document Intelligence and Foundry project availability can differ by region.

```powershell
$LOCATION = "eastus"
$RESOURCE_GROUP = "rg-document-intelligence-dev"
$DOCUMENT_RESOURCE = "docintel-dev"
$FOUNDRY_ACCOUNT = "foundry-dev"
$FOUNDRY_PROJECT = "document-summary"
```

Azure resource names must be globally unique where required. Use only letters,
numbers, and hyphens for names that require DNS-compatible naming.

## Create the resource group

```powershell
az group create `
  --name $RESOURCE_GROUP `
  --location $LOCATION
```

## Create the Document Intelligence resource

Create a Cognitive Services account with the Document Intelligence kind:

```powershell
az cognitiveservices account create `
  --name $DOCUMENT_RESOURCE `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --kind FormRecognizer `
  --sku S0 `
  --yes
```

Retrieve its endpoint and key:

```powershell
$DOCUMENT_ENDPOINT = az cognitiveservices account show `
  --name $DOCUMENT_RESOURCE `
  --resource-group $RESOURCE_GROUP `
  --query properties.endpoint `
  --output tsv

$DOCUMENT_KEY = az cognitiveservices account keys list `
  --name $DOCUMENT_RESOURCE `
  --resource-group $RESOURCE_GROUP `
  --query key1 `
  --output tsv

Write-Output $DOCUMENT_ENDPOINT
```

`S0` is the standard paid tier. Review pricing and quota before using it in
production.

## Optional: create a Microsoft Foundry account

Use this only when the project needs Foundry agent summarization or other
generative AI features. OCR does not require Foundry.

```powershell
az cognitiveservices account create `
  --name $FOUNDRY_ACCOUNT `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --kind AIServices `
  --sku S0 `
  --yes
```

## Optional: create a Foundry project

The project command and available options can vary with the installed Azure
CLI extension. Inspect the current command first:

```powershell
az cognitiveservices account project -h
```

On subscriptions that support the project command:

```powershell
az cognitiveservices account project create `
  --name $FOUNDRY_ACCOUNT `
  --resource-group $RESOURCE_GROUP `
  --project-name $FOUNDRY_PROJECT `
  --location $LOCATION
```

Get the project resource ID:

```powershell
$PROJECT_ID = az cognitiveservices account project show `
  --name $FOUNDRY_ACCOUNT `
  --resource-group $RESOURCE_GROUP `
  --project-name $FOUNDRY_PROJECT `
  --query id `
  --output tsv
```

If the project command is unavailable, create the project from the Microsoft
Foundry portal, then continue with the endpoint and RBAC steps below.

## Grant local developer access

Find the signed-in user object ID:

```powershell
$USER_ID = az ad signed-in-user show --query id --output tsv
```

Grant access to the Document Intelligence resource:

```powershell
$DOCUMENT_ID = az cognitiveservices account show `
  --name $DOCUMENT_RESOURCE `
  --resource-group $RESOURCE_GROUP `
  --query id `
  --output tsv

az role assignment create `
  --assignee-object-id $USER_ID `
  --assignee-principal-type User `
  --role "Cognitive Services User" `
  --scope $DOCUMENT_ID
```

If using a Foundry project with `DefaultAzureCredential`, grant the Foundry
User role:

```powershell
az role assignment create `
  --assignee-object-id $USER_ID `
  --assignee-principal-type User `
  --role "Foundry User" `
  --scope $PROJECT_ID
```

Role assignments can take several minutes to become effective.

## Get the Foundry project endpoint

```powershell
$FOUNDRY_ENDPOINT = az cognitiveservices account project show `
  --name $FOUNDRY_ACCOUNT `
  --resource-group $RESOURCE_GROUP `
  --project-name $FOUNDRY_PROJECT `
  --query properties.endpoints `
  --output json

Write-Output $FOUNDRY_ENDPOINT
```

Copy the project endpoint shown by the command. Do not assume the account
endpoint is the same as the project endpoint.

## Configure `.env`

Create or update the project-root `.env` file:

```env
DOCUMENT_INTELLIGENCE_ENDPOINT=<document-intelligence-endpoint>
DOCUMENT_INTELLIGENCE_KEY=<document-intelligence-key>
DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-read

# Optional Foundry integration
FOUNDRY_PROJECT_ENDPOINT=<foundry-project-endpoint>
FOUNDRY_AGENT_NAME=<agent-name>
FOUNDRY_AGENT_VERSION=1
FOUNDRY_MAX_OCR_CHARS=1500
```

Do not commit `.env`. The project `.gitignore` already excludes it.

## Verify the resources

```powershell
az cognitiveservices account show `
  --name $DOCUMENT_RESOURCE `
  --resource-group $RESOURCE_GROUP `
  --query "{name:name,kind:kind,location:location,sku:sku.name}" `
  --output table
```

Then run OCR:

```powershell
.\.venv\Scripts\python.exe -m scripts.document_ocr `
  "C:\path\to\document.pdf"
```

Optionally run Foundry summarization:

```powershell
.\.venv\Scripts\python.exe -m scripts.foundry_ocr `
  ".\data\results\document_ocr_result.json"
```

## Cleanup

Delete all resources created by this guide:

```powershell
az group delete `
  --name $RESOURCE_GROUP `
  --yes `
  --no-wait
```

This deletes the resource group and every resource inside it. Confirm the
resource group contains only resources that are safe to delete.

## Notes

- `prebuilt-read` does not require a custom model.
- `prebuilt-invoice` can be passed with `--model-id prebuilt-invoice`.
- Custom model availability depends on the Document Intelligence region.
- Foundry is optional for this project.
- Never print or commit API keys.

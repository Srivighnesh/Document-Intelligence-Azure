You can create all three Azure RBAC role assignments using Azure CLI (PowerShell or VS Code terminal).

I'll use your currently signed-in Azure developer identity.

## 1. Login to Azure

```
az login
```

Check your active subscription:

```
az account show --output table
```

If required:

```
az account set --subscription "<SUBSCRIPTION_ID>"
```

## 2. Set resource details

Replace the placeholders with your actual Azure resource names.

```
$RESOURCE_GROUP = "research-agent-v1-resource-Group"

$STORAGE_ACCOUNT = "<YOUR_STORAGE_ACCOUNT_NAME>"

$KEY_VAULT = "<YOUR_KEY_VAULT_NAME>"
```

Get your signed-in developer identity:

```
$USER_ID = az ad signed-in-user show --query id -o tsv
```

Get the resource IDs:

```
$STORAGE_ID = az storage account show `
    --name $STORAGE_ACCOUNT `
    --resource-group $RESOURCE_GROUP `
    --query id -o tsv

$KV_ID = az keyvault show `
    --name $KEY_VAULT `
    --resource-group $RESOURCE_GROUP `
    --query id -o tsv
```

## 3. Create the three role assignments

3 RBAC assignments

Role 1: Storage Blob Data Contributor

Allows the developer to upload source documents, compact results, full OCR
analysis JSON, and cache manifests into Blob Storage.

```
az role assignment create `
    --assignee-object-id $USER_ID `
    --assignee-principal-type User `
    --role "Storage Blob Data Contributor" `
    --scope $STORAGE_ID
```

Role 2: Key Vault Secrets User

Allows the developer to read application configuration secrets.

```
az role assignment create `
    --assignee-object-id $USER_ID `
    --assignee-principal-type User `
    --role "Key Vault Secrets User" `
    --scope $KV_ID
```

Role 3: Key Vault Secrets Officer

Allows the developer to create, update and delete secrets.

```
az role assignment create `
    --assignee-object-id $USER_ID `
    --assignee-principal-type User `
    --role "Key Vault Secrets Officer" `
    --scope $KV_ID
```

## 4. Verify role assignments

Check Storage Account permissions:

```
az role assignment list `
    --assignee $USER_ID `
    --scope $STORAGE_ID `
    --output table
```

Check Key Vault permissions:

```
az role assignment list `
    --assignee $USER_ID `
    --scope $KV_ID `
    --output table
```

## 5. Important Key Vault configuration

For Key Vault RBAC permissions to work, check that permission model is set to Azure RBAC:

```
az keyvault show `
    --name $KEY_VAULT `
    --resource-group $RESOURCE_GROUP `
    --query properties.enableRbacAuthorization
```

Expected:

```
true
```

If it returns `false`, the vault is using the access-policy model. Don't switch it blindly, because existing access policies may need migration.

## Final permission structure

| Identity  | Resource        | Role                          |
| --------- | --------------- | ----------------------------- |
| Developer | Storage Account | Storage Blob Data Contributor |
| Developer | Key Vault       | Key Vault Secrets User        |
| Developer | Key Vault       | Key Vault Secrets Officer     |

Security recommendation: Key Vault Secrets Officer already includes secret read permissions. Assigning both Key Vault roles is therefore redundant. You can use Secrets Officer alone if the developer needs both reading and managing secrets.

Also, these commands require sufficient permissions to create role assignments, typically Owner or User Access Administrator.

If you share your Storage Account name and Key Vault name, I can prepare the exact copy-paste PowerShell commands without placeholders.

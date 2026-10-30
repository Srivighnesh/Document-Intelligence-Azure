Use these Azure CLI commands in PowerShell to give your account permission to read secrets from Key Vault.

### 1. Sign in to Azure

```
az login
```

### 2. Get your user ID and Key Vault resource ID

```
$userId = az ad signed-in-user show --query id --output tsv

$vaultId = az keyvault show `
  --name kv-docintel-sv-2026-01 `
  --resource-group rg-student-ai-korea `
  --query id `
  --output tsv
```

### 3. Assign Key Vault Secrets User

```
az role assignment create `
  --assignee-object-id $userId `
  --assignee-principal-type User `
  --role "Key Vault Secrets User" `
  --scope $vaultId
```

### 4. Verify the assignment

```
az role assignment list `
  --assignee $userId `
  --scope $vaultId `
  --include-inherited `
  --query "[].{Role:roleDefinitionName,Scope:scope}" `
  --output table
```

You should see `Key Vault Secrets User` in the output.

Note: Your account must have permission to assign Azure roles, such as Owner or Role Based Access Control Administrator. Allow a few minutes for the new permission to take effect, then restart your FastAPI application.
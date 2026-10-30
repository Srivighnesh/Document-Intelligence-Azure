from config import (
    DOCUMENT_INTELLIGENCE_ENDPOINT,
    DOCUMENT_INTELLIGENCE_KEY,
    FOUNDRY_PROJECT_ENDPOINT,
    AZURE_STORAGE_ACCOUNT_URL
)

if __name__ == "__main__":
    print("Testing Azure Key Vault connection...")

    for name, value in [
        ("Document Intelligence endpoint", DOCUMENT_INTELLIGENCE_ENDPOINT),
        ("Document Intelligence key", DOCUMENT_INTELLIGENCE_KEY),
        ("Foundry endpoint", FOUNDRY_PROJECT_ENDPOINT),
        ("Stroage URl",AZURE_STORAGE_ACCOUNT_URL )
    ]:
        assert value.strip(), f"{name} is empty."
        print(f"PASS: {name} loaded successfully.")

    print("SUCCESS: All three values loaded from Key Vault.")
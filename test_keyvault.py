if __name__ == "__main__":
    from src.config import (
        AZURE_STORAGE_ACCOUNT_URL,
        DOCUMENT_INTELLIGENCE_ENDPOINT,
        DOCUMENT_INTELLIGENCE_KEY,
        FOUNDRY_ENABLED,
        FOUNDRY_PROJECT_ENDPOINT,
    )

    print("Testing Azure Key Vault connection...")

    for name, value in [
        ("Document Intelligence endpoint", DOCUMENT_INTELLIGENCE_ENDPOINT),
        ("Document Intelligence key", DOCUMENT_INTELLIGENCE_KEY),
        ("Storage URL", AZURE_STORAGE_ACCOUNT_URL),
    ]:
        assert value.strip(), f"{name} is empty."
        print(f"PASS: {name} loaded successfully.")

    if FOUNDRY_ENABLED:
        assert FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_PROJECT_ENDPOINT.strip()
        print("PASS: Foundry endpoint loaded successfully.")

    print("SUCCESS: All required values loaded from Key Vault.")

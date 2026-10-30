"""Azure Blob Storage operations for uploaded documents."""

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings


class BlobStorageService:
    """Upload and download documents from an existing Blob container."""

    def __init__(self, account_url: str, container_name: str) -> None:
        """Create a Blob client using the current Azure identity."""
        self.container_name = container_name
        
        # Authenticate using Azure credentials.
        # Connect to the existing storage account.
        self._service = BlobServiceClient(
            account_url=account_url,
            credential=DefaultAzureCredential(),
        )
        self._container = self._service.get_container_client(container_name)

    def upload(self, blob_name: str, content: bytes, content_type: str) -> str:
        """Upload bytes and return the blob URL."""
        blob_client = self._container.get_blob_client(blob_name)
        blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        return blob_client.url

    def download(self, blob_name: str) -> bytes:
        """Download the uploaded blob as bytes for analysis."""
        blob_client = self._container.get_blob_client(blob_name)
        return blob_client.download_blob().readall()

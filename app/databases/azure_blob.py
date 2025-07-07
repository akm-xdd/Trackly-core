import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from fastapi import HTTPException
import mimetypes
from typing import BinaryIO


class AzureBlobClient:
    """Azure Blob Storage client"""

    def __init__(self):
        self.account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
        self.account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

        if not all([self.account_name, self.container_name]):
            raise ValueError("Azure storage configuration missing")

        # Initialize blob service client
        if self.connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string)
        elif self.account_key:
            self.blob_service_client = BlobServiceClient(
                account_url=f"https://{self.account_name}.blob.core.windows.net",
                credential=self.account_key)
        else:
            raise ValueError(
                "Either AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_KEY is required")

    def generate_blob_path(self, filename: str, uploaded_by: str) -> str:
        """Generate blob path with directory structure: issue-files/2025/07/05/file/user_id/filename"""
        now = datetime.utcnow()
        date_path = now.strftime("%Y/%m/%d")
        return f"{date_path}/file/{uploaded_by}/{filename}"

    def upload_file(
            self,
            file_content: BinaryIO,
            filename: str,
            uploaded_by: str,
            content_type: str = None) -> str:
        """Upload file to Azure Blob Storage and return the blob URL"""
        try:
            # Generate blob path
            blob_path = self.generate_blob_path(filename, uploaded_by)
            print(f"Generated blob path: {blob_path}")

            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_path
            )

            # Determine content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(filename)
                if not content_type:
                    content_type = "application/octet-stream"

            print(f"Content type: {content_type}")

            # Import ContentSettings properly
            from azure.storage.blob import ContentSettings

            # Upload file
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type)
            )

            # Return the blob URL
            return blob_client.url

        except Exception as e:
            print(f"Azure upload error: {str(e)}")
            raise HTTPException(status_code=500,
                                detail=f"Failed to upload file: {str(e)}")

    def delete_file(self, blob_url: str) -> bool:
        """Delete file from Azure Blob Storage using blob URL"""
        try:
            # Extract blob path from URL
            # URL format:
            # https://account.blob.core.windows.net/container/blob_path
            blob_path = blob_url.split(f"{self.container_name}/", 1)[1]

            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_path
            )

            # Delete blob
            blob_client.delete_blob()
            return True

        except Exception as e:
            # Log error but don't raise exception - file might already be
            # deleted
            print(f"Warning: Failed to delete blob {blob_url}: {str(e)}")
            return False

    def file_exists(self, blob_url: str) -> bool:
        """Check if file exists in Azure Blob Storage"""
        try:
            # Extract blob path from URL
            blob_path = blob_url.split(f"{self.container_name}/", 1)[1]

            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_path
            )

            # Check if blob exists
            return blob_client.exists()

        except Exception:
            return False


# Singleton instance
azure_client = AzureBlobClient()

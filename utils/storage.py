"""
Azure Blob Storage integration for artifact management.
Falls back to local storage if Azure credentials are not configured.
"""
import os
from typing import Optional
from runner.logger import log

# Try to import Azure SDK
try:
    from azure.storage.blob import BlobServiceClient, ContentSettings
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    log("WARN", "azure_sdk_missing", "Azure Storage SDK not available - install azure-storage-blob for cloud storage")

STORAGE_CONNECTION_STRING = os.getenv("STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("STORAGE_CONTAINER_NAME", "artifacts")


class ArtifactStorage:
    """
    Manages artifact storage with automatic fallback to local filesystem.
    """
    
    def __init__(self):
        self.use_blob = False
        self.blob_service = None
        self.container_client = None
        
        if AZURE_AVAILABLE and STORAGE_CONNECTION_STRING:
            try:
                self.blob_service = BlobServiceClient.from_connection_string(
                    STORAGE_CONNECTION_STRING
                )
                self.container_client = self.blob_service.get_container_client(
                    CONTAINER_NAME
                )
                # Try to create container if it doesn't exist
                try:
                    self.container_client.create_container()
                except Exception:
                    pass  # Container already exists
                
                self.use_blob = True
                log("INFO", "storage_init", "Using Azure Blob Storage for artifacts", container=CONTAINER_NAME)
            except Exception as e:
                log("ERROR", "storage_init_failed", "Failed to initialize Azure Blob Storage", error=str(e))
                self.use_blob = False
        else:
            reason = "Azure SDK not installed" if not AZURE_AVAILABLE else "No connection string configured"
            log("INFO", "storage_init", f"Using local storage for artifacts: {reason}")
    
    def upload_file(self, local_path: str, blob_path: str) -> str:
        """
        Upload file to blob storage and return URL.
        Falls back to returning local path if blob storage is not available.
        
        Args:
            local_path: Path to local file
            blob_path: Destination path in blob storage (e.g., "session_123/screenshot.png")
            
        Returns:
            URL to access the file (blob URL or local path)
        """
        if not self.use_blob:
            return local_path
        
        try:
            # Determine content type
            content_type = "application/octet-stream"
            if blob_path.endswith('.png'):
                content_type = "image/png"
            elif blob_path.endswith('.jpg') or blob_path.endswith('.jpeg'):
                content_type = "image/jpeg"
            elif blob_path.endswith('.mp4'):
                content_type = "video/mp4"
            elif blob_path.endswith('.json'):
                content_type = "application/json"
            elif blob_path.endswith('.txt') or blob_path.endswith('.log'):
                content_type = "text/plain"
            
            blob_client = self.container_client.get_blob_client(blob_path)
            
            with open(local_path, "rb") as data:
                blob_client.upload_blob(
                    data, 
                    overwrite=True,
                    content_settings=ContentSettings(content_type=content_type)
                )
            
            url = blob_client.url
            log("DEBUG", "blob_upload_success", "Uploaded file to blob storage", 
                blob_path=blob_path, url=url)
            return url
            
        except Exception as e:
            log("ERROR", "blob_upload_failed", "Failed to upload to blob storage", 
                blob_path=blob_path, error=str(e))
            return local_path
    
    def download_file(self, blob_path: str, local_path: str) -> bool:
        """
        Download file from blob storage.
        
        Args:
            blob_path: Path in blob storage
            local_path: Destination local path
            
        Returns:
            True if successful, False otherwise
        """
        if not self.use_blob:
            log("WARN", "blob_download_skipped", "Blob storage not available")
            return False
        
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            
            # Create directory if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, "wb") as f:
                blob_data = blob_client.download_blob()
                f.write(blob_data.readall())
            
            log("DEBUG", "blob_download_success", "Downloaded file from blob storage",
                blob_path=blob_path, local_path=local_path)
            return True
            
        except Exception as e:
            log("ERROR", "blob_download_failed", "Failed to download from blob storage",
                blob_path=blob_path, error=str(e))
            return False
    
    def delete_file(self, blob_path: str) -> bool:
        """
        Delete file from blob storage.
        
        Args:
            blob_path: Path in blob storage
            
        Returns:
            True if successful, False otherwise
        """
        if not self.use_blob:
            return False
        
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            blob_client.delete_blob()
            log("DEBUG", "blob_delete_success", "Deleted file from blob storage",
                blob_path=blob_path)
            return True
            
        except Exception as e:
            log("ERROR", "blob_delete_failed", "Failed to delete from blob storage",
                blob_path=blob_path, error=str(e))
            return False
    
    def list_files(self, prefix: str = "") -> list:
        """
        List files in blob storage with optional prefix filter.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List of blob paths
        """
        if not self.use_blob:
            return []
        
        try:
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            log("ERROR", "blob_list_failed", "Failed to list blobs",
                prefix=prefix, error=str(e))
            return []


# Singleton instance
artifact_storage = ArtifactStorage()


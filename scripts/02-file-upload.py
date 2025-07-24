#!/usr/bin/env python3
"""
Azure Blob Storage Bulk File Upload Script

This script uploads multiple files to Azure Blob Storage with progress tracking,
error handling, and configurable options.

Requirements:
    pip install azure-storage-blob python-dotenv

Usage:
    python azure_upload.py --folder /path/to/files --container mycontainer
"""

import os
import sys
import argparse
import logging
import time
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import AzureError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging
log_filename = logs_dir / f'file_upload_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class AzureBlobUploader:
    """Handle bulk uploads to Azure Blob Storage."""
    
    def __init__(self, connection_string: str, container_name: str):
        """
        Initialize the uploader.
        
        Args:
            connection_string: Azure Storage connection string
            container_name: Target container name
        """
        self.connection_string = connection_string
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.uploaded_files = []
        self.failed_files = []
        self.upload_times = []  # Track individual upload times
        
    def create_container_if_not_exists(self) -> bool:
        """Create container if it doesn't exist."""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.create_container()
            logger.info(f"Container '{self.container_name}' created successfully")
            return True
        except Exception as e:
            if "ContainerAlreadyExists" in str(e):
                logger.info(f"Container '{self.container_name}' already exists")
                return True
            else:
                logger.error(f"Failed to create container: {e}")
                return False
    
    def upload_single_file(self, file_path: Path, blob_name: Optional[str] = None, 
                          overwrite: bool = True) -> bool:
        """
        Upload a single file to Azure Blob Storage.
        
        Args:
            file_path: Path to the local file
            blob_name: Name for the blob (defaults to filename)
            overwrite: Whether to overwrite existing blobs
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
            
        if blob_name is None:
            blob_name = file_path.name
            
        start_time = time.time()  # Start timing the upload
        
        try:
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            
            # Upload file
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=overwrite)
                
            upload_time = time.time() - start_time  # Calculate upload time
            file_size = file_path.stat().st_size
            
            # Calculate upload speed
            upload_speed_mbps = (file_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0
            
            logger.info(f"✓ Uploaded: {file_path.name} ({file_size:,} bytes) -> {blob_name} "
                       f"in {upload_time:.2f}s ({upload_speed_mbps:.2f} MB/s)")
            
            self.uploaded_files.append(str(file_path))
            self.upload_times.append(upload_time)
            return True
            
        except AzureError as e:
            logger.error(f"✗ Azure error uploading {file_path.name}: {e}")
            self.failed_files.append(str(file_path))
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error uploading {file_path.name}: {e}")
            self.failed_files.append(str(file_path))
            return False
    
    def get_files_to_upload(self, source_path: Path, 
                           file_extensions: Optional[List[str]] = None,
                           recursive: bool = True) -> List[Path]:
        """
        Get list of files to upload from source path.
        
        Args:
            source_path: Source directory or file path
            file_extensions: List of file extensions to include (e.g., ['.txt', '.pdf'])
            recursive: Whether to search subdirectories
            
        Returns:
            List of file paths to upload
        """
        files_to_upload = []
        
        if source_path.is_file():
            files_to_upload.append(source_path)
        elif source_path.is_dir():
            pattern = "**/*" if recursive else "*"
            for file_path in source_path.glob(pattern):
                if file_path.is_file():
                    if file_extensions is None or file_path.suffix.lower() in file_extensions:
                        files_to_upload.append(file_path)
        
        return files_to_upload
    
    def upload_files(self, source_path: Path, 
                    file_extensions: Optional[List[str]] = None,
                    recursive: bool = True,
                    preserve_structure: bool = True,
                    max_workers: int = 5,
                    overwrite: bool = True) -> dict:
        """
        Upload multiple files to Azure Blob Storage.
        
        Args:
            source_path: Source directory or file path
            file_extensions: List of file extensions to include
            recursive: Whether to search subdirectories
            preserve_structure: Whether to preserve directory structure in blob names
            max_workers: Number of concurrent upload threads
            overwrite: Whether to overwrite existing blobs
            
        Returns:
            dict: Upload summary with counts and lists
        """
        # Get files to upload
        files_to_upload = self.get_files_to_upload(source_path, file_extensions, recursive)
        
        if not files_to_upload:
            logger.warning("No files found to upload")
            return {"total": 0, "successful": 0, "failed": 0}
        
        logger.info(f"Found {len(files_to_upload)} files to upload")
        
        # Start timing the entire upload process
        total_start_time = time.time()
        
        # Create container if needed
        if not self.create_container_if_not_exists():
            logger.error("Failed to access/create container")
            return {"total": len(files_to_upload), "successful": 0, "failed": len(files_to_upload)}
        
        # Upload files concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit upload tasks
            future_to_file = {}
            for file_path in files_to_upload:
                # Determine blob name
                if preserve_structure and source_path.is_dir():
                    # Preserve directory structure
                    blob_name = str(file_path.relative_to(source_path)).replace('\\', '/')
                else:
                    blob_name = file_path.name
                
                future = executor.submit(self.upload_single_file, file_path, blob_name, overwrite)
                future_to_file[future] = file_path
            
            # Process completed uploads
            successful_uploads = 0
            for future in as_completed(future_to_file):
                if future.result():
                    successful_uploads += 1
        
        # Calculate total elapsed time
        total_elapsed_time = time.time() - total_start_time
        
        # Calculate average upload time per file
        avg_upload_time = sum(self.upload_times) / len(self.upload_times) if self.upload_times else 0
        
        # Summary
        total_files = len(files_to_upload)
        failed_uploads = total_files - successful_uploads
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Upload Summary:")
        logger.info(f"Total files: {total_files}")
        logger.info(f"Successful: {successful_uploads}")
        logger.info(f"Failed: {failed_uploads}")
        logger.info(f"Total elapsed time: {total_elapsed_time:.2f} seconds ({total_elapsed_time/60:.2f} minutes)")
        logger.info(f"Average upload time per file: {avg_upload_time:.2f} seconds")
        if successful_uploads > 0:
            logger.info(f"Throughput: {successful_uploads/total_elapsed_time:.2f} files/second")
        logger.info(f"Container: {self.container_name}")
        logger.info(f"{'='*50}")
        
        if self.failed_files:
            logger.info(f"Failed files: {', '.join(self.failed_files)}")
        
        return {
            "total": total_files,
            "successful": successful_uploads,
            "failed": failed_uploads,
            "uploaded_files": self.uploaded_files,
            "failed_files": self.failed_files,
            "total_elapsed_time": total_elapsed_time,
            "average_upload_time": avg_upload_time,
            "throughput": successful_uploads/total_elapsed_time if total_elapsed_time > 0 else 0
        }

def main():
    """Main function to handle command line arguments and execute upload."""
    parser = argparse.ArgumentParser(description="Upload files to Azure Blob Storage")
    parser.add_argument("--folder", "-f", type=str, required=True,
                       help="Path to folder or file to upload")
    parser.add_argument("--container", "-c", type=str, required=True,
                       help="Azure Storage container name")
    parser.add_argument("--connection-string", type=str,
                       help="Azure Storage connection string (or set AZURE_STORAGE_CONNECTION_STRING)")
    parser.add_argument("--extensions", type=str, nargs="+",
                       help="File extensions to include (e.g., .txt .pdf .jpg)")
    parser.add_argument("--no-recursive", action="store_true",
                       help="Don't search subdirectories")
    parser.add_argument("--no-preserve-structure", action="store_true",
                       help="Don't preserve directory structure in blob names")
    parser.add_argument("--max-workers", type=int, default=5,
                       help="Maximum concurrent uploads (default: 5)")
    parser.add_argument("--no-overwrite", action="store_true",
                       help="Don't overwrite existing blobs")
    
    args = parser.parse_args()
    
    # Get connection string
    connection_string = (args.connection_string or 
                        os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
    
    if not connection_string:
        logger.error("Azure Storage connection string is required. "
                    "Set AZURE_STORAGE_CONNECTION_STRING environment variable "
                    "or use --connection-string argument")
        sys.exit(1)
    
    # Validate source path
    source_path = Path(args.folder)
    if not source_path.exists():
        logger.error(f"Source path does not exist: {source_path}")
        sys.exit(1)
    
    # Process file extensions
    file_extensions = None
    if args.extensions:
        file_extensions = [ext if ext.startswith('.') else f'.{ext}' 
                          for ext in args.extensions]
        logger.info(f"Filtering for extensions: {file_extensions}")
    
    # Create uploader and run upload
    uploader = AzureBlobUploader(connection_string, args.container)
    
    try:
        result = uploader.upload_files(
            source_path=source_path,
            file_extensions=file_extensions,
            recursive=not args.no_recursive,
            preserve_structure=not args.no_preserve_structure,
            max_workers=args.max_workers,
            overwrite=not args.no_overwrite
        )
        
        # Exit with error code if any uploads failed
        if result["failed"] > 0:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Upload interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
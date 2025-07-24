#!/usr/bin/env python3
"""
Azure Storage Connection Test Script

This script tests connectivity to Azure Storage resources including:
- Blob Storage
- Basic account information retrieval
- Container listing (if permissions allow)

Requirements:
- pip install azure-storage-blob azure-identity python-dotenv
"""

import os
import sys
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError, ClientAuthenticationError, ResourceNotFoundError
from pathlib import Path
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # This will load variables from .env file in current directory
    print("✓ Loaded environment variables from .env file")
except ImportError:
    print("⚠ python-dotenv not installed. Install with: pip install python-dotenv")
    print("⚠ Falling back to system environment variables only")
except Exception as e:
    print(f"⚠ Could not load .env file: {e}")
    print("⚠ Falling back to system environment variables only")

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging
log_filename = logs_dir / f'connection_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(log_filename),
    logging.StreamHandler(sys.stdout)
])
logger = logging.getLogger(__name__)

class AzureStorageConnectionTester:
    def __init__(self, connection_string=None, account_name=None, account_key=None, account_url=None):
        """
        Initialize the connection tester with various authentication methods
        
        Args:
            connection_string: Full Azure Storage connection string
            account_name: Storage account name (requires account_key)
            account_key: Storage account key (requires account_name)
            account_url: Storage account URL (for managed identity auth)
        """
        self.connection_string = connection_string
        self.account_name = account_name
        self.account_key = account_key
        self.account_url = account_url
        self.blob_service_client = None
        
    def create_client(self):
        """Create BlobServiceClient using available authentication method"""
        try:
            if self.connection_string:
                logger.info("Connecting using connection string...")
                self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            elif self.account_name and self.account_key:
                logger.info("Connecting using account name and key...")
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self.blob_service_client = BlobServiceClient(account_url=account_url, credential=self.account_key)
            elif self.account_url:
                logger.info("Connecting using managed identity...")
                from azure.identity import DefaultAzureCredential
                credential = DefaultAzureCredential()
                self.blob_service_client = BlobServiceClient(account_url=self.account_url, credential=credential)
            else:
                raise ValueError("No valid authentication method provided")
                
            return True
        except Exception as e:
            logger.error(f"Failed to create client: {str(e)}")
            return False
    
    def test_connection(self):
        """Test basic connection to Azure Storage"""
        try:
            logger.info("Testing basic connection...")
            # Try to get account information
            account_info = self.blob_service_client.get_account_information()
            logger.info(f"✓ Connection successful!")
            logger.info(f"  Account kind: {account_info.get('account_kind', 'Unknown')}")
            logger.info(f"  SKU name: {account_info.get('sku_name', 'Unknown')}")
            return True
        except ClientAuthenticationError as e:
            logger.error(f"✗ Authentication failed: {str(e)}")
            return False
        except AzureError as e:
            logger.error(f"✗ Azure error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error: {str(e)}")
            return False
    
    def test_list_containers(self, max_containers=10):
        """Test listing containers (requires appropriate permissions)"""
        try:
            logger.info("Testing container listing...")
            containers = list(self.blob_service_client.list_containers())
            
            if containers:
                logger.info(f"✓ Found {len(containers)} container(s):")
                for i, container in enumerate(containers[:max_containers]):
                    logger.info(f"  - {container.name}")
                    if i >= max_containers - 1 and len(containers) > max_containers:
                        logger.info(f"  ... and {len(containers) - max_containers} more")
                        break
            else:
                logger.info("✓ No containers found (or no list permissions)")
            return True
        except Exception as e:
            logger.warning(f"⚠ Container listing failed: {str(e)}")
            return False
    
    def test_create_test_container(self, test_container_name="connection-test"):
        """Test creating a temporary container (requires write permissions)"""
        try:
            logger.info(f"Testing container creation with '{test_container_name}'...")
            container_client = self.blob_service_client.get_container_client(test_container_name)
            
            # Try to create container
            container_client.create_container()
            logger.info(f"✓ Test container '{test_container_name}' created successfully")
            
            # Clean up - delete the test container
            container_client.delete_container()
            logger.info(f"✓ Test container '{test_container_name}' deleted successfully")
            return True
            
        except ResourceNotFoundError:
            logger.warning("⚠ Container creation test skipped - insufficient permissions")
            return False
        except Exception as e:
            logger.warning(f"⚠ Container creation test failed: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all connection tests"""
        logger.info("=" * 50)
        logger.info("Azure Storage Connection Test Started")
        logger.info("=" * 50)
        
        # Create client
        if not self.create_client():
            logger.error("Failed to create Azure Storage client")
            return False
        
        # Test basic connection
        connection_ok = self.test_connection()
        if not connection_ok:
            logger.error("Basic connection test failed")
            return False
        
        # Test container operations
        self.test_list_containers()
        self.test_create_test_container()
        
        logger.info("=" * 50)
        logger.info("Azure Storage Connection Test Completed")
        logger.info("=" * 50)
        return True

def main():
    """Main function to run the connection test"""
    
    # Try to get connection details from environment variables first
    connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
    account_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')
    account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
    
    # If no environment variables, prompt for connection string
    if not any([connection_string, (account_name and account_key), account_url]):
        print("No Azure Storage credentials found in environment variables or .env file.")
        print("\nPlease create a .env file in the current directory with one of the following:")
        print("1. AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net")
        print("2. AZURE_STORAGE_ACCOUNT_NAME=yourstorageaccount")
        print("   AZURE_STORAGE_ACCOUNT_KEY=your-account-key")
        print("3. AZURE_STORAGE_ACCOUNT_URL=https://yourstorageaccount.blob.core.windows.net")
        print("\nOr provide connection string now:")
        
        connection_string = input("Enter Azure Storage connection string (or press Enter to exit): ").strip()
        if not connection_string:
            print("No connection string provided. Exiting.")
            sys.exit(1)
    
    # Create and run the tester
    tester = AzureStorageConnectionTester(
        connection_string=connection_string,
        account_name=account_name,
        account_key=account_key,
        account_url=account_url
    )
    
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All connection tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some connection tests failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

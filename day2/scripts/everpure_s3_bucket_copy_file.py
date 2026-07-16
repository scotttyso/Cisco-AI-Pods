#!/usr/bin/env python3
"""
Upload file to Everpure FlashBlade S3 bucket.

Environment Variables:
    AWS_S3_ENDPOINT: FlashBlade S3 endpoint (e.g., flashblade.example.com)
    AWS_ACCESS_KEY_ID: S3 access key ID
    AWS_SECRET_ACCESS_KEY: S3 secret access key
    AWS_S3_BUCKET: S3 bucket name

Examples:
    # Upload with auto-generated S3 key
    python everpure_s3_bucket_copy_file.py /path/to/file.txt
    
    # Upload with custom S3 key
    python everpure_s3_bucket_copy_file.py /path/to/file.txt -k custom-name.txt
    
    # Upload to subdirectory
    python everpure_s3_bucket_copy_file.py /path/to/file.txt -k folder/file.txt
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import boto3
import urllib3
from botocore.exceptions import ClientError, NoCredentialsError

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_environment() -> dict:
    """Validate and retrieve required environment variables."""
    required_vars = {
        'AWS_S3_ENDPOINT': os.environ.get('AWS_S3_ENDPOINT'),
        'AWS_ACCESS_KEY_ID': os.environ.get('AWS_ACCESS_KEY_ID'),
        'AWS_SECRET_ACCESS_KEY': os.environ.get('AWS_SECRET_ACCESS_KEY'),
        'AWS_S3_BUCKET': os.environ.get('AWS_S3_BUCKET'),
    }
    
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        print("\n" + "="*70)
        print("To set the missing environment variables, run:")
        print("="*70)
        
        for var in missing:
            if var == 'AWS_S3_ENDPOINT':
                print(f"export {var}=<flashblade-hostname>  # e.g., flashblade.example.com")
            elif var == 'AWS_ACCESS_KEY_ID':
                print(f"export {var}=<your-access-key>")
            elif var == 'AWS_SECRET_ACCESS_KEY':
                print(f"export {var}=<your-secret-key>")
            elif var == 'AWS_S3_BUCKET':
                print(f"export {var}=<bucket-name>")
        
        print("\nOr set them all at once:")
        print("export AWS_S3_ENDPOINT=<endpoint> AWS_ACCESS_KEY_ID=<key> \\\\")
        print("       AWS_SECRET_ACCESS_KEY=<secret> AWS_S3_BUCKET=<bucket>")
        print("="*70 + "\n")
        sys.exit(1)
    
    return required_vars


def setup_proxy_bypass() -> None:
    """Disable proxy settings for direct S3 endpoint connection."""
    for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
        os.environ[proxy_var] = ''
    os.environ['NO_PROXY'] = '*'


def create_s3_client(endpoint: str, access_key: str, secret_key: str) -> boto3.client:
    """Create and return S3 client."""
    try:
        return boto3.client(
            's3',
            endpoint_url=f"https://{endpoint}:443",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            verify=False
        )
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        sys.exit(1)


def validate_file(filepath: str) -> Path:
    """
    Validate that file exists and is readable.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Path object
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(filepath)
    
    if not file_path.exists():
        logger.error(f"File not found: {filepath}")
        sys.exit(1)
    
    if not file_path.is_file():
        logger.error(f"Path is not a file: {filepath}")
        sys.exit(1)
    
    if not os.access(file_path, os.R_OK):
        logger.error(f"File is not readable: {filepath}")
        sys.exit(1)
    
    return file_path


def upload_file(
    s3_client: boto3.client,
    bucket_name: str,
    file_path: Path,
    s3_key: Optional[str] = None
) -> bool:
    """
    Upload file to S3 bucket.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the bucket
        file_path: Path to file to upload
        s3_key: S3 object key (defaults to filename)
        
    Returns:
        True if successful, False otherwise
    """
    # Use provided key or default to filename
    object_key = s3_key or file_path.name
    file_size = file_path.stat().st_size
    
    try:
        logger.info(f"Uploading {file_path.name} ({file_size:,} bytes) to s3://{bucket_name}/{object_key}")
        
        s3_client.upload_file(
            Filename=str(file_path),
            Bucket=bucket_name,
            Key=object_key,
            ExtraArgs={'Metadata': {'uploaded-by': 'everpure-s3-script'}}
        )
        
        logger.info(f"✓ Successfully uploaded to s3://{bucket_name}/{object_key}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"S3 error ({error_code}): {e}")
        return False
    except NoCredentialsError:
        logger.error("AWS credentials not found or invalid")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        return False


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Upload file to Pure Storage FlashBlade S3 bucket',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'filename',
        help='Local file path to upload'
    )
    parser.add_argument(
        '-k', '--key',
        help='S3 object key (defaults to filename)',
        default=None
    )
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Validate environment and file
    env_vars = validate_environment()
    file_path = validate_file(args.filename)
    setup_proxy_bypass()
    
    # Create S3 client
    s3_client = create_s3_client(
        endpoint=env_vars['AWS_S3_ENDPOINT'],
        access_key=env_vars['AWS_ACCESS_KEY_ID'],
        secret_key=env_vars['AWS_SECRET_ACCESS_KEY']
    )
    
    # Upload file
    success = upload_file(
        s3_client=s3_client,
        bucket_name=env_vars['AWS_S3_BUCKET'],
        file_path=file_path,
        s3_key=args.key
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
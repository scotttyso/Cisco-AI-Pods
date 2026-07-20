#!/usr/bin/env python3
"""
List files in Everpure FlashBlade S3 bucket.

Environment Variables:
    AWS_S3_ENDPOINT: FlashBlade S3 endpoint (e.g., flashblade.example.com)
    AWS_ACCESS_KEY_ID: S3 access key ID
    AWS_SECRET_ACCESS_KEY: S3 secret access key
    AWS_S3_BUCKET: S3 bucket name
"""

import argparse
import logging
import os
import sys
from typing import Optional

import boto3
import urllib3
from botocore.exceptions import ClientError

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
        logger.error("Missing environment variables: %s", ', '.join(missing))
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
        logger.error("Failed to create S3 client: %s", e)
        sys.exit(1)


def list_bucket_contents(
    s3_client: boto3.client,
    bucket_name: str,
    prefix: Optional[str] = None,
    verbose: bool = False
) -> None:
    """
    List all objects in S3 bucket with pagination support.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the bucket
        prefix: Optional prefix to filter objects
        verbose: If True, show file sizes and timestamps
    """
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=bucket_name,
            Prefix=prefix or ''
        )
        
        object_count = 0
        total_size = 0

        for page in page_iterator:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                object_count += 1
                total_size += obj.get('Size', 0)

                if verbose:
                    modified = obj.get('LastModified', 'N/A')
                    size = obj.get('Size', 0)
                    print(f"  {obj['Key']:60s} | Size: {size:12d} | Modified: {modified}")
                else:
                    print(f"  {obj['Key']}")
        
        logger.info("Total: %d objects, %d bytes", object_count, total_size)

    except ClientError as e:
        logger.error("S3 error listing bucket: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='List files in Pure Storage FlashBlade S3 bucket',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '-p', '--prefix',
        help='Filter objects by prefix (e.g., subfolder/)',
        default=None
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show file sizes and modification times'
    )
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Validate environment
    env_vars = validate_environment()
    setup_proxy_bypass()

    # Create S3 client
    s3_client = create_s3_client(
        endpoint=env_vars['AWS_S3_ENDPOINT'],
        access_key=env_vars['AWS_ACCESS_KEY_ID'],
        secret_key=env_vars['AWS_SECRET_ACCESS_KEY']
    )
    
    # List bucket contents
    logger.info("Listing objects in bucket: %s", env_vars['AWS_S3_BUCKET'])
    if args.prefix:
        logger.info("Filter prefix: %s", args.prefix)
    
    list_bucket_contents(
        s3_client=s3_client,
        bucket_name=env_vars['AWS_S3_BUCKET'],
        prefix=args.prefix,
        verbose=args.verbose
    )


if __name__ == '__main__':
    main()


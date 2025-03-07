"""Utility functions for Terabox link processing."""

import re
from urllib.parse import urlparse

def validate_terabox_url(url: str) -> bool:
    """
    Validate if the given URL is a valid Terabox link.
    
    Args:
        url (str): The URL to validate
        
    Returns:
        bool: True if valid Terabox URL, False otherwise
    """
    try:
        parsed = urlparse(url)
        return (
            parsed.netloc in ['www.terabox.com', 'terabox.com', 'terasharelink.com', 'www.terasharelink.com'] and
            bool(parsed.path)
        )
    except Exception:
        return False

def extract_file_id(url: str) -> str:
    """
    Extract the file ID from a Terabox URL.
    
    Args:
        url (str): The Terabox URL
        
    Returns:
        str: The extracted file ID or empty string if not found
    """
    try:
        # Handle both /s/ and /sharing/ URL formats
        pattern = r'/(?:s|sharing)/([a-zA-Z0-9_-]+)'
        match = re.search(pattern, url)
        return match.group(1) if match else ''
    except Exception:
        return ''

def format_size(size_bytes: int) -> str:
    """
    Format file size from bytes to human readable format.
    
    Args:
        size_bytes (int): Size in bytes
        
    Returns:
        str: Formatted size string (e.g., "1.23 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

"""Main entry point for Terabox video downloader."""

import os
import time
import asyncio
import argparse
from src.utils import validate_terabox_url
from src.extractor import TeraboxExtractor
from src.generator import LinkGenerator

async def process_video(url: str, output_dir: str = "videos") -> None:
    """
    Process video from Terabox URL with interactive browser automation.
    
    Args:
        url (str): Terabox share URL
        output_dir (str): Directory to save downloaded videos
    """
    # Validate URL
    if not validate_terabox_url(url):
        print("Error: Invalid Terabox URL")
        return
    
    print("\nOpening browser to extract video information...")
    print("Please wait while the page loads...")
    
    # Extract video information
    extractor = TeraboxExtractor()
    video_info, error = await extractor.get_video_info(url)
    
    if error:
        print(f"Error: {error}")
        return
        
    if not video_info:
        print("Error: Failed to extract video information")
        return
        
    # Display video information
    print("\nVideo Information:")
    print(f"Name: {video_info['name']}")
    print(f"Size: {video_info['size']}")
    
    print("\nGenerating download link...")
    print("If a verification page appears, please complete it.")
    
    # Generate download link
    generator = LinkGenerator()
    download_link, cookies, error = await generator.generate_download_link(url, video_info)
    
    if error:
        print(f"Error: {error}")
        return
        
    if not download_link:
        print("Error: Failed to generate download link")
        return
    
    print("\nStarting download...")
    success, result = await generator.download_video(download_link, cookies, video_info, output_dir)
    
    if not success:
        print(f"Error: {result}")
        return
        
    print(f"\nVideo successfully downloaded to: {result}")

def main():
    """Main function to handle Terabox video downloads."""
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Download videos from Terabox share links with browser automation"
    )
    parser.add_argument(
        "url",
        help="Terabox share URL"
    )
    parser.add_argument(
        "-o", "--output",
        default="videos",
        help="Output directory for downloaded videos (default: videos)"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    try:
        # Run async process
        asyncio.run(process_video(args.url, args.output))
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    
    print("\nDone.")

if __name__ == "__main__":
    main()

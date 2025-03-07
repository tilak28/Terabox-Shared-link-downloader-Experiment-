"""Data extraction module for Terabox files using Playwright."""

import asyncio
from typing import Dict, Optional, Tuple
from playwright.async_api import async_playwright
from .utils import extract_file_id

class TeraboxExtractor:
    """Handle extraction of video data from Terabox links using Playwright."""
    
    async def get_video_info(self, url: str) -> Tuple[Optional[Dict], str]:
        """
        Extract video information from Terabox URL using Playwright.
        
        Args:
            url (str): Terabox share URL
            
        Returns:
            Tuple[Optional[Dict], str]: (Video info dict or None, Error message if any)
        """
        async with async_playwright() as p:
            try:
                # Launch browser
                browser = await p.chromium.launch(
                    headless=False,  # Show browser for debugging
                )
                context = await browser.new_context()
                page = await context.new_page()
                
                # Navigate to URL
                await page.goto(url)
                
                # Wait for file information to load
                await page.wait_for_load_state('networkidle')
                
                # Extract video information from the page
                video_info = await page.evaluate("""() => {
                    const nameElement = document.querySelector('[class*="file-name"]');
                    const sizeElement = document.querySelector('[class*="file-size"]');
                    
                    return {
                        name: nameElement ? nameElement.textContent.trim() : '',
                        size: sizeElement ? sizeElement.textContent.trim() : '',
                        path: window.location.pathname,
                        file_id: window.__INITIAL_STATE__?.shareInfo?.shareid || ''
                    };
                }""")
                
                if not video_info['name']:
                    return None, "Could not find video information on page"
                
                # Return video information
                return video_info, ""
                
            except Exception as e:
                return None, f"Extraction error: {str(e)}"
            
            finally:
                try:
                    await browser.close()
                except:
                    pass

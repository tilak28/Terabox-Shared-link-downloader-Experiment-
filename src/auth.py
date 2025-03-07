"""Authentication and session management for Terabox using Playwright."""

import asyncio
from typing import Dict
from playwright.async_api import async_playwright

class TeraboxAuth:
    async def get_cookies(self, url: str) -> Dict[str, str]:
        """
        Get authentication cookies using Playwright.
        
        Args:
            url (str): Terabox URL to authenticate
            
        Returns:
            Dict[str, str]: Cookie data
        """
        async with async_playwright() as p:
            try:
                # Launch browser
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Navigate to URL and wait for page load
                await page.goto(url, wait_until='networkidle')
                await page.wait_for_timeout(5000)  # Wait for dynamic content
                
                # Get cookies
                cookies = await context.cookies()
                cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                
                # Print cookies for debugging
                print("Debug - Cookies obtained:")
                for name, value in cookie_dict.items():
                    print(f"{name}: {value}")
                
                return cookie_dict
                
            except Exception as e:
                print(f"Error getting cookies: {str(e)}")
                return {}
                
            finally:
                try:
                    await browser.close()
                except:
                    pass

    def get_cookies_sync(self, url: str) -> Dict[str, str]:
        """
        Synchronous wrapper for get_cookies.
        
        Args:
            url (str): Terabox URL to authenticate
            
        Returns:
            Dict[str, str]: Cookie data
        """
        return asyncio.run(self.get_cookies(url))

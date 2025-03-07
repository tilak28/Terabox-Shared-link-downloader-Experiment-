"""Direct link generation and video downloading using Terabox API."""

import os
import sys
import json
import aiohttp
import re
import requests
from typing import Dict, Optional, Tuple
from tqdm import tqdm
from playwright.async_api import async_playwright

class LinkGenerator:
    """Generate direct download links using Terabox API."""

    # Define multiple possible API bases to try
    API_BASES = [
        "https://www.terabox.app",
        "https://www.teraboxapp.com",
        "https://terabox.com",
        "https://terasharelink.com"
    ]
    
    async def generate_download_link(self, url: str, file_info: Dict) -> Tuple[Optional[str], str]:
        """
        Generate a direct download link using Terabox API.
        
        Args:
            url (str): Original Terabox share URL
            file_info (Dict): File information from extractor
            
        Returns:
            Tuple[Optional[str], str]: (Download URL or None, Error message if any)
        """
        try:
            print("\nFetching file information from API...")
            
            # First get CSRF token and cookies using Playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Use visible browser to help with debugging
                context = await browser.new_context()
                page = await context.new_page()
                
                print("Getting page information...")
                await page.goto(url)
                await page.wait_for_load_state('networkidle')
                
                # Extract CSRF token from page - improved extraction methods
                csrf_token = await page.evaluate("""() => {
                    // Method 1: Look for csrfToken in scripts
                    const scripts = document.getElementsByTagName('script');
                    for (const script of scripts) {
                        if (!script.textContent) continue;
                        const match = script.textContent.match(/csrfToken\\s*:\\s*['"]([^'"]+)['"]/);
                        if (match) return match[1];
                    }
                    
                    // Method 2: Check for meta tag
                    const metaTag = document.querySelector('meta[name="csrf-token"]');
                    if (metaTag) return metaTag.getAttribute('content');
                    
                    // Method 3: Check global variables
                    if (window.csrfToken) return window.csrfToken;
                    
                    // Method 4: Check for any token-like hidden inputs
                    const tokenInputs = document.querySelectorAll('input[type="hidden"]');
                    for (const input of tokenInputs) {
                        if (input.name && (input.name.includes('csrf') || input.name.includes('token'))) {
                            return input.value;
                        }
                    }
                    
                    // Method 5: Look for token in any data attributes
                    const elementsWithDataAttr = document.querySelectorAll('[data-csrf], [data-token]');
                    if (elementsWithDataAttr.length > 0) {
                        const el = elementsWithDataAttr[0];
                        return el.dataset.csrf || el.dataset.token;
                    }
                    
                    return null;
                }""")
                
                # If still no CSRF token, try to extract it from the HTML content
                if not csrf_token:
                    html_content = await page.content()
                    # Try different regex patterns
                    patterns = [
                        r'csrfToken\s*:\s*[\'"]([^\'"]+)[\'"]',
                        r'csrf[_-]?token[\'"]?\s*[:=]\s*[\'"]([^\'"]+)[\'"]',
                        r'<meta\s+name=[\'"]csrf-token[\'"]\s+content=[\'"]([^\'"]+)[\'"]',
                        r'_csrf_token\s*=\s*[\'"]([^\'"]+)[\'"]'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, html_content, re.IGNORECASE)
                        if match:
                            csrf_token = match.group(1)
                            break
                
                # Try to get direct download link from page with alternative method
                direct_download = await page.evaluate("""() => {
                    // Look for download buttons
                    const downloadLinks = Array.from(document.querySelectorAll('a[href*="download"]'));
                    if (downloadLinks.length > 0) return downloadLinks[0].href;
                    
                    // Try to find any button that looks like a download button and click it
                    const downloadButtons = Array.from(document.querySelectorAll('button')).filter(
                        b => b.textContent.toLowerCase().includes('download')
                    );
                    if (downloadButtons.length > 0) {
                        return downloadButtons[0].getAttribute('data-link') || 
                               downloadButtons[0].getAttribute('href') ||
                               null;
                    }
                    
                    return null;
                }""")
                
                if direct_download:
                    print("Found direct download link on page!")
                
                # Extract share ID from URL
                share_id = url.split('/')[-1]
                
                # Try to extract file ID from the page
                file_id = await page.evaluate("""() => {
                    if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.shareInfo) {
                        return window.__INITIAL_STATE__.shareInfo.shareid || 
                               window.__INITIAL_STATE__.shareInfo.file_id || '';
                    }
                    return '';
                }""")
                
                if not file_id:
                    file_id = share_id
                
                # Get cookies
                cookies = await context.cookies()
                cookie_dict = {c['name']: c['value'] for c in cookies}
                
                # Wait for user to potentially solve captcha
                print("If you see a verification page, please complete it, then wait 10 seconds...")
                print("You may need to click any download button on the page if you see one.")
                await page.wait_for_timeout(15000)
                
                # Get cookies again after potential verification
                cookies = await context.cookies()
                cookie_dict = {c['name']: c['value'] for c in cookies}
                
                # Take a screenshot for debugging
                await page.screenshot(path="terabox_page.png")
                print("Screenshot saved as terabox_page.png")
                
                # Try direct download method if available
                if direct_download:
                    print("Attempting direct download from page...")
                    try:
                        await page.click('a[download], button:has-text("Download")')
                        await page.wait_for_timeout(5000)
                        await page.screenshot(path="download_attempt.png")
                        print("Screenshot of download attempt saved as download_attempt.png")
                    except Exception as e:
                        print(f"Direct download click failed: {str(e)}")
                
                await browser.close()
                
            # If direct download link was found, return it
            if direct_download:
                return direct_download, ""

            # If CSRF token is still not found, try to proceed with empty token
            if not csrf_token:
                csrf_token = ""
                print("Warning: Could not find CSRF token, trying to proceed anyway...")

            # Try multiple API endpoints
            last_error = "Unknown error"
            
            for api_base in self.API_BASES:
                try:
                    print(f"Trying API endpoint: {api_base}")
                    share_download_api = f"{api_base}/api/sharedownload"
                    list_api = f"{api_base}/share/list"
                    
                    # Set up headers and cookies for API requests
                    headers = {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/100.0.0.0 Safari/537.36',
                        'Referer': url,
                        'Origin': api_base
                    }
                    
                    # Add CSRF token to headers if found
                    if csrf_token:
                        headers['X-CSRF-Token'] = csrf_token
                    
                    # Convert Playwright cookies to dict format
                    cookies_dict = {}
                    for cookie in cookies:
                        cookies_dict[cookie['name']] = cookie['value']
                    
                    # Get file list using API
                    params = {'shareid': share_id, 'root': '1'}
                    print("\nGetting file information...")
                    async with aiohttp.ClientSession(cookies=cookies_dict) as session:
                        async with session.get(list_api, params=params, headers=headers) as response:
                            list_data = await response.json()

                        if list_data.get('errno', -1) != 0:
                            last_error = f"List API error: {list_data.get('errmsg', 'Unknown error')}"
                            print(last_error)
                            continue

                        # Get first file's fs_id
                        files = list_data.get('list', [])
                        if not files:
                            last_error = "No files found"
                            print(last_error)
                            continue

                        fs_id = files[0]['fs_id']

                        # Now get download link
                        data = {
                            'shareid': share_id,
                            'sign': cookies_dict.get('sign', ''),
                            'timestamp': cookies_dict.get('timestamp', ''),
                            'file_ids': [fs_id],
                            'type': 'video',
                            'channel': 'dubox',
                            'clienttype': 0,
                            'web': 1
                        }

                        print("Requesting download link...")
                        async with session.post(share_download_api, json=data, headers=headers) as response:
                            download_data = await response.json()

                        if download_data.get('errno', -1) != 0:
                            last_error = f"Download API error: {download_data.get('errmsg', 'Unknown error')}"
                            print(last_error)
                            continue

                        dlink = download_data.get('list', [{}])[0].get('dlink')
                        if not dlink:
                            last_error = "No download link found in response"
                            print(last_error)
                            continue

                        print("Successfully got download link!")
                        return dlink, ""
                        
                except Exception as e:
                    last_error = f"API error with {api_base}: {str(e)}"
                    print(last_error)
                    continue
            
            # If we've tried all API endpoints and none worked, try the direct method
            print("API methods failed, trying direct download method...")
            
            # Create a session with cookies
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            # Visit the URL directly to look for download links
            response = session.get(url)
            if response.status_code == 200:
                download_pattern = r'href=[\'"]([^\'"]+(?:download|dlink)[^\'"]*)[\'"]'
                matches = re.findall(download_pattern, response.text)
                if matches:
                    return matches[0], ""
            
            return None, last_error

        except Exception as e:
            return None, f"API error: {str(e)}"
    
    async def download_video(self, video_url: str, file_info: Dict, output_dir: str = "videos") -> Tuple[bool, str]:
        """
        Download video to specified directory using HTTP requests.
        
        Args:
            video_url (str): Direct video download URL
            file_info (Dict): Video file information
            output_dir (str): Output directory path
            
        Returns:
            Tuple[bool, str]: (Success status, Error message if any)
        """
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Clean and sanitize filename
            filename = file_info.get("name", "video").strip()
            # Remove invalid characters
            import re
            filename = re.sub(r'[<>:"/\\|?*]', '', filename)
            # Remove excess spaces and dots
            filename = re.sub(r'\s+', '_', filename)
            filename = re.sub(r'\.+', '.', filename)
            # Ensure .mp4 extension
            if not filename.lower().endswith('.mp4'):
                filename += '.mp4'
            # Truncate if too long
            if len(filename) > 200:
                filename = filename[:196] + '.mp4'
            
            output_path = os.path.join(output_dir, filename)
            print(f"Saving to: {output_path}")
            
            # Download the file with progress bar
            print(f"\nDownloading: {filename}")
            sys.stdout.flush()
            
            # Use requests.get with stream for downloading
            from tqdm.auto import tqdm
            
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            
            with open(output_path, 'wb') as f, tqdm(
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for data in response.iter_content(block_size):
                    size = f.write(data)
                    pbar.update(size)
            
            return True, output_path
            
        except Exception as e:
            return False, f"Download error: {str(e)}"

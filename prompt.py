import html
import time
import os
import pandas as pd
import requests
import random
from bs4 import BeautifulSoup
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options

def fetch_product_info_selenium(asin: str, max_retries: int = 2) -> tuple:
    """Fetch product information using Selenium with retries."""
    url = f"https://www.amazon.com/dp/{asin}"
    
    # More robust Edge options to avoid detection
    edge_options = Options()
    edge_options.add_argument("--headless")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    edge_options.add_argument("--disable-extensions")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    edge_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    edge_options.add_experimental_option('useAutomationExtension', False)
    
    for attempt in range(max_retries):
        driver = None
        try:
            print(f"Attempting to crawl ASIN {asin} (attempt {attempt + 1}/{max_retries})...")
            
            # Try to use EdgeChromiumDriverManager, fallback to system Edge
            try:
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                service = EdgeService(EdgeChromiumDriverManager().install())
            except Exception as e:
                print(f"WebDriver manager failed, trying system Edge: {e}")
                service = EdgeService()
            
            driver = webdriver.Edge(service=service, options=edge_options)
            
            # Add script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print(f"Navigating to: {url}")
            driver.get(url)
            
            # Wait a bit for page to load
            time.sleep(3)
            
            page_source = driver.page_source
            print(f"Page source length: {len(page_source)}")

            # Check for common blocking indicators
            if "Type the characters you see in this image" in page_source:
                print("❌ Blocked by CAPTCHA")
                raise ConnectionRefusedError("Blocked by CAPTCHA")
            
            if "Robot Check" in page_source:
                print("❌ Blocked by Robot Check")
                raise ConnectionRefusedError("Blocked by Robot Check")
            
            if len(page_source) < 1000:
                print("❌ Page source too short, likely blocked")
                raise ConnectionRefusedError("Page source too short")
            
            # ⭐ THÊM: Check for invalid/non-existent product pages (simple image count method)
            soup = BeautifulSoup(page_source, "html.parser")
            
            # Count images on the page
            all_images = soup.find_all('img')
            image_count = len(all_images)
            
            print(f"Found {image_count} images on page")
            
            # Error pages typically have only 2-3 images (sorry text image + dog image + maybe Amazon logo)
            # Real product pages have many more images (product photos, thumbnails, etc.)
            if image_count <= 3:
                print(f"❌ Too few images ({image_count}), likely an error page for ASIN {asin}")
                return asin, "INVALID_ASIN", []  # Special marker for invalid ASIN
            
            # Additional quick check: real product pages have product-related elements
            product_elements = soup.find_all(['div', 'span'], class_=lambda x: x and any(term in x.lower() for term in ['product', 'item', 'detail']))
            if len(product_elements) < 5:  # Real product pages have many product-related elements
                print(f"❌ Too few product elements ({len(product_elements)}), likely error page")
                return asin, "INVALID_ASIN", []
            
            # Try multiple selectors for title
            title = ""
            title_selectors = [
                "span#productTitle",
                "h1.a-size-large",
                "h1 span",
                ".product-title",
                "[data-automation-id='product-title']"
            ]
            
            for selector in title_selectors:
                title_tag = soup.select_one(selector)
                if title_tag:
                    title = html.unescape(title_tag.get_text(strip=True))
                    print(f"✅ Found title using selector '{selector}': {title[:50]}...")
                    break
            
            if not title:
                print("❌ No title found with any selector")
                # Debug: Print some page content
                print("Page title:", soup.title.string if soup.title else "No title tag")
                print("Available IDs:", [tag.get('id') for tag in soup.find_all(id=True)][:10])
            
            # Try multiple selectors for bullet points
            bullets = []
            bullet_selectors = [
                "div#feature-bullets ul li span.a-list-item",
                "div#feature-bullets span.a-list-item",
                ".a-unordered-list .a-list-item",
                "#productDetails_feature_div li",
                ".feature .a-list-item"
            ]
            
            for selector in bullet_selectors:
                bullet_elements = soup.select(selector)
                if bullet_elements:
                    print(f"Found {len(bullet_elements)} bullet elements using selector '{selector}'")
                    for element in bullet_elements:
                        txt = html.unescape(element.get_text(" ", strip=True))
                        if txt and len(txt) > 10 and not txt.startswith("See more"):
                            bullets.append(txt)
                    if bullets:
                        break
            
            print(f"Found {len(bullets)} bullet points")
            
            if title:  # Success if we have at least a title
                print(f"✅ Successfully crawled {asin}")
                return asin, title, bullets
            else:
                print(f"❌ No title found for {asin}")
                
        except Exception as e:
            print(f"❌ Error crawling ASIN {asin} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3  # Progressive delay
                print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    print(f"❌ Failed to crawl ASIN {asin} after {max_retries} attempts.")
    return asin, "", []

def fetch_product_info_requests(asin: str) -> tuple:
    """Alternative method using requests library (as backup)."""
    try:
        import requests
        import random
        import time
        
        # List of user agents to rotate
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
        url = f"https://www.amazon.com/dp/{asin}"
        
        # Add small random delay to seem more human-like
        time.sleep(random.uniform(0.5, 2.0))
        
        print(f"Fetching {url} with requests...")
        
        # Create session for better connection handling
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=15)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Check for blocking
            if "Robot Check" in response.text or "Enter the characters you see below" in response.text:
                print(f"❌ Amazon blocked the request for {asin}")
                return asin, "", []
            
            # ⭐ THÊM: Check for invalid/non-existent product pages (simple image count method)
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Count images on the page
            all_images = soup.find_all('img')
            image_count = len(all_images)
            
            print(f"Found {image_count} images on page")
            
            # Error pages typically have only 2-3 images (sorry text image + dog image + maybe Amazon logo)
            # Real product pages have many more images (product photos, thumbnails, etc.)
            if image_count <= 3:
                print(f"❌ Too few images ({image_count}), likely an error page for ASIN {asin}")
                return asin, "INVALID_ASIN", []  # Special marker for invalid ASIN
            
            # Additional quick check: real product pages have product-related elements
            product_elements = soup.find_all(['div', 'span'], class_=lambda x: x and any(term in x.lower() for term in ['product', 'item', 'detail']))
            if len(product_elements) < 5:  # Real product pages have many product-related elements
                print(f"❌ Too few product elements ({len(product_elements)}), likely error page")
                return asin, "INVALID_ASIN", []
            
            # Extract title with multiple fallback selectors
            title = ""
            title_selectors = [
                "span#productTitle",
                "h1.a-size-large.a-spacing-none.a-color-base",
                "h1 span",
                ".product-title",
                "[data-automation-id='product-title']",
                "h1.a-size-large",
                "#productTitle"
            ]
            
            for selector in title_selectors:
                title_tag = soup.select_one(selector)
                if title_tag:
                    title = html.unescape(title_tag.get_text(strip=True))
                    print(f"✅ Found title using selector '{selector}': {title[:50]}...")
                    break
            
            # Extract bullets with multiple fallback selectors
            bullets = []
            bullet_selectors = [
                "div#feature-bullets ul li span.a-list-item",
                "div#feature-bullets span.a-list-item",
                ".a-unordered-list .a-list-item",
                "#productDetails_feature_div li",
                ".feature .a-list-item",
                "div[data-feature-name='featurebullets'] span.a-list-item"
            ]
            
            for selector in bullet_selectors:
                bullet_elements = soup.select(selector)
                if bullet_elements:
                    print(f"Found {len(bullet_elements)} bullet elements using '{selector}'")
                    for element in bullet_elements:
                        txt = html.unescape(element.get_text(" ", strip=True))
                        # Filter out unwanted text
                        if (txt and len(txt) > 10 and 
                            not any(skip in txt.lower() for skip in ['see more', 'make sure', 'important:', 'note:'])):
                            bullets.append(txt)
                    if bullets:
                        break
            
            print(f"Extracted: Title={bool(title)}, Bullets={len(bullets)}")
            return asin, title, bullets
            
        elif response.status_code == 503:
            print(f"❌ Amazon returned 503 (Service Unavailable) for {asin}")
            return asin, "", []
        elif response.status_code == 404:
            print(f"❌ Product not found (404) for {asin}")
            return asin, "", []
        else:
            print(f"❌ HTTP {response.status_code} for {asin}")
            return asin, "", []
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error for {asin}: {e}")
        return asin, "", []
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout error for {asin}: {e}")
        return asin, "", []
    except Exception as e:
        print(f"❌ Requests method failed for {asin}: {e}")
        return asin, "", []
    
def crawl_amazon_data(excel_file: str):
    """Step 1: Crawl product data and save to separate columns."""
    logs = []
    
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        logs.append(f"❌ Error reading Excel file: {e}")
        return logs
    
    # Ensure required columns exist
    if "ProductTitle" not in df.columns:
        df["ProductTitle"] = ""
    if "Bullets" not in df.columns:
        df["Bullets"] = ""
    
    # Get ASINs that need crawling
    asins_to_fetch = []
    asins_with_titles = []
    invalid_asins = []
    
    for idx, row in df.iterrows():
        asin = str(row.get("ASIN", "")).strip()
        existing_title = str(row.get("ProductTitle", "")).strip()
        
        # Fix: Treat 'nan', 'NaN', empty string, or None as no title
        has_valid_title = (
            existing_title and 
            existing_title.lower() not in ['nan', 'none', ''] and
            len(existing_title) > 3
        )
        
        # Only crawl if ASIN exists and no valid title is present
        if asin and len(asin) == 10 and asin.upper() != 'NAN':
            if not has_valid_title:
                asins_to_fetch.append(asin)
            else:
                asins_with_titles.append(asin)
        else:
            invalid_asins.append(asin if asin else f"Row {idx}: Empty ASIN")
    
    total_asins = len(asins_to_fetch) + len(asins_with_titles) + len(invalid_asins)
    logs.append(f"  • Invalid ASINs: {len(invalid_asins)}")
    
    if invalid_asins:
        logs.append(f"⚠️ **Invalid ASINs found:** {', '.join(invalid_asins[:5])}" + 
                   (f" and {len(invalid_asins)-5} more..." if len(invalid_asins) > 5 else ""))
    
    if not asins_to_fetch:
        logs.append("❌ **No ASINs need crawling** (all have existing titles or invalid ASINs).")
        
        # Clear invalid 'nan' titles so they can be crawled next time
        logs.append("🧹 Cleaning up 'nan' entries in ProductTitle...")
        nan_mask = df['ProductTitle'].astype(str).str.lower().isin(['nan', 'none'])
        nan_count = nan_mask.sum()
        if nan_count > 0:
            df.loc[nan_mask, 'ProductTitle'] = ""
            try:
                df.to_excel(excel_file, index=False)
                logs.append(f"✅ Cleaned up {nan_count} 'nan' entries. Try running crawl again.")
            except Exception as e:
                logs.append(f"❌ Error saving cleaned Excel: {e}")
        else:
            logs.append("No 'nan' entries found to clean.")
        return logs
    
    logs.append(f"🚀 **Starting crawl for {len(asins_to_fetch)} ASINs:** {', '.join(asins_to_fetch[:3])}" + 
               (f" and {len(asins_to_fetch)-3} more..." if len(asins_to_fetch) > 3 else ""))
    
    # Test single ASIN first to check connectivity
    if asins_to_fetch:
        logs.append(f"🧪 **Testing connectivity** with first ASIN: {asins_to_fetch[0]}")
        try:
            # Try the requests method first (simpler, often more reliable)
            test_asin, test_title, test_bullets = fetch_product_info_requests(asins_to_fetch[0])
            if test_title:
                logs.append(f"✅ **Requests method works!** Title: '{test_title[:50]}...'")
                use_requests_method = True
            else:
                # 2. Fallback sang Selenium nếu requests thất bại
                logs.append("❌ Requests method failed, trying Selenium...")
                test_asin, test_title, test_bullets = fetch_product_info_selenium(asins_to_fetch[0])
                if test_title:
                    logs.append(f"✅ **Selenium method works!** Title: '{test_title[:50]}...'")
                    use_requests_method = False
                else:
                    logs.append("❌ **Both methods failed.** Check internet connection and try again.")
                    use_requests_method = False
        except Exception as e:
                logs.append(f"❌ **Connectivity test failed:** {e}")
                return logs
    
    # Crawl using the chosen method and collect results
    product_info_map = {}
    successful_crawls = []
    failed_crawls = []
    invalid_asins = []  # ⭐ THÊM: Track invalid ASINs to be removed
    
    method_name = "requests" if 'use_requests_method' in locals() and use_requests_method else "Selenium"
    logs.append(f"🌐 **Using {method_name} method** for crawling...")
    
    if 'use_requests_method' in locals() and use_requests_method:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_asin = {
                executor.submit(fetch_product_info_requests, asin): asin 
                for asin in asins_to_fetch
            }
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_asin):
                fetched_asin, title, bullets = future.result()
                product_info_map[fetched_asin] = (title, bullets)
                completed += 1
                
                if title == "INVALID_ASIN":  # ⭐ THÊM: Handle invalid ASIN
                    invalid_asins.append(fetched_asin)
                    logs.append(f"🗑️ ({completed}/{len(asins_to_fetch)}) **Invalid ASIN - will be removed:** {fetched_asin}")
                elif title:
                    successful_crawls.append(fetched_asin)
                    logs.append(f"✅ ({completed}/{len(asins_to_fetch)}) **Success:** {fetched_asin}")
                else:
                    failed_crawls.append(fetched_asin)
                    logs.append(f"❌ ({completed}/{len(asins_to_fetch)}) **Failed:** {fetched_asin}")
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_to_asin = {
                executor.submit(fetch_product_info_selenium, asin): asin 
                for asin in asins_to_fetch
            }
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_asin):
                fetched_asin, title, bullets = future.result()
                product_info_map[fetched_asin] = (title, bullets)
                completed += 1
                
                if title == "INVALID_ASIN":  # ⭐ THÊM: Handle invalid ASIN
                    invalid_asins.append(fetched_asin)
                    logs.append(f"🗑️ ({completed}/{len(asins_to_fetch)}) **Invalid ASIN - will be removed:** {fetched_asin}")
                elif title:
                    successful_crawls.append(fetched_asin)
                    logs.append(f"✅ ({completed}/{len(asins_to_fetch)}) **Success:** {fetched_asin}")
                else:
                    failed_crawls.append(fetched_asin)
                    logs.append(f"❌ ({completed}/{len(asins_to_fetch)}) **Failed:** {fetched_asin}")
    
    # ⭐ THÊM: Remove invalid ASINs from DataFrame
    if invalid_asins:
        logs.append(f"🗑️ **Removing {len(invalid_asins)} invalid ASINs** from Excel file...")
        original_row_count = len(df)
        df = df[~df["ASIN"].isin(invalid_asins)]
        removed_count = original_row_count - len(df)
        logs.append(f"✅ **Removed {removed_count} rows** with invalid ASINs: {', '.join(invalid_asins[:5])}" + 
                   (f" and {len(invalid_asins)-5} more..." if len(invalid_asins) > 5 else ""))
    
    # Update DataFrame with crawled data (skip invalid ASINs)
    updated_count = 0
    for idx, row in df.iterrows():
        asin = str(row.get("ASIN", "")).strip()
        if asin in product_info_map:
            title, bullets = product_info_map[asin]
            # ⭐ SỬA: Chỉ update nếu có data hợp lệ (không phải INVALID_ASIN)
            if title and title != "INVALID_ASIN":
                df.at[idx, "ProductTitle"] = title
                df.at[idx, "Bullets"] = "\n".join(bullets) if bullets else ""
                updated_count += 1
    
    # Save back to Excel
    try:
        df.to_excel(excel_file, index=False)
        logs.append(f"💾 Successfully saved {updated_count} products to {excel_file}")
        
        # Verify the save
        df_verify = pd.read_excel(excel_file)
        valid_titles = 0
        if 'ProductTitle' in df_verify.columns:
            for title in df_verify['ProductTitle']:
                title_str = str(title).strip()
                if title_str and title_str.lower() not in ['nan', 'none'] and len(title_str) > 3:
                    valid_titles += 1
        
        # Final summary
        logs.append(f"  • ✅ **Successfully crawled:** {len(successful_crawls)} ASINs")
        logs.append(f"  • ❌ **Failed to crawl:** {len(failed_crawls)} ASINs")
        logs.append(f"  • ⁉️ **Invalid ASINs removed:** {len(invalid_asins)} ASINs")
        
        if invalid_asins:  # ⭐ THÊM: Show removed ASINs
            logs.append(f"🗑️ **Removed invalid ASINs:** {', '.join(invalid_asins[:5])}" + 
                       (f" and {len(invalid_asins)-5} more..." if len(invalid_asins) > 5 else ""))
        
        if failed_crawls:
            logs.append(f"⚠️ **Failed ASINs:** {', '.join(failed_crawls[:5])}" + 
                       (f" and {len(failed_crawls)-5} more..." if len(failed_crawls) > 5 else ""))
        
    except Exception as e:
        logs.append(f"❌ **Error saving Excel file:** {e}")
    
    return logs

def generate_base_prompts(excel_file: str, wpm: int = 160):
    """Step 2: Calculate word count and generate base prompts."""
    print("Generating base prompts...")
    
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return
    for idx, row in df.iterrows():
        wpm = float(row.get("WordsPerSecond", 160))
    # Ensure required columns exist
    if "Duration" not in df.columns:
        print("Warning: 'Duration' column not found. Setting default duration to 0.")
        df["Duration"] = 0
    if "WordCount" not in df.columns:
        df["WordCount"] = 0
    if "BasePrompt" not in df.columns:
        df["BasePrompt"] = ""
    
    updated_count = 0
    for idx, row in df.iterrows():
        duration = float(row.get("Duration", 0))
        existing_base_prompt = str(row.get("BasePrompt", "")).strip()
        
        # Only generate if duration exists and no base prompt exists
        if duration > 0 and not existing_base_prompt:
            word_count = round(duration / 60 * wpm)
            df.at[idx, "WordCount"] = word_count
            
            base_prompt = f"""You are an expert ad-copy writer specializing in Amazon product marketing. Your task is to create compelling, natural-sounding product advertisements that convert viewers into buyers.
REQUIREMENTS:
- Write EXACTLY {word_count} words (not more, not less)
- Use natural, conversational tone
- Focus on benefits, not just features
- Include emotional appeal and urgency
- Make it sound like a knowledgeable friend recommending the product
- Avoid overly salesy or promotional language
- Use simple, clear sentences
- Include a call-to-action at the end

STRUCTURE:
1. Hook: Start with a relatable problem or desire
2. Solution: Introduce the product as the perfect solution
3. Benefits: Highlight 2-3 key benefits with social proof
4. Urgency: Create mild urgency without being pushy
5. Call-to-action: End with a clear next step

Product information will be provided below:"""

            df.at[idx, "BasePrompt"] = base_prompt
            updated_count += 1
    
    # Save back to Excel
    try:
        df.to_excel(excel_file, index=False)
        print(f"✅ Generated base prompts for {updated_count} products.")
    except Exception as e:
        print(f"Error saving Excel file: {e}")

def generate_final_prompts(excel_file: str):
    """Step 3: Combine crawled data with base prompts to create final prompts."""
    print("Generating final prompts...")
    
    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return
    
    # Ensure required columns exist
    if "Prompt" not in df.columns:
        df["Prompt"] = ""
    
    updated_count = 0
    for idx, row in df.iterrows():
        base_prompt = str(row.get("BasePrompt", "")).strip()
        title = str(row.get("ProductTitle", "")).strip()
        bullets_str = str(row.get("Bullets", "")).strip()
        existing_final_prompt = str(row.get("Prompt", "")).strip()
        
        # Fix: Better validation for actual product data
        has_valid_title = (
            title and 
            title.lower() not in ['nan', 'none', ''] and
            len(title) > 3
        )
        
        has_valid_bullets = (
            bullets_str and 
            bullets_str.lower() not in ['nan', 'none', ''] and
            len(bullets_str) > 3
        )
        
        # Check if existing prompt already contains "Product Title: nan" (needs regeneration)
        needs_regeneration = (
            not existing_final_prompt or 
            "Product Title: nan" in existing_final_prompt or
            len(existing_final_prompt.strip()) < 50
        )
        
        print(f"Row {idx}: Title Valid: {has_valid_title}, Base Prompt: {bool(base_prompt)}, Needs Regeneration: {needs_regeneration}")
        
        # Only generate if we have base prompt, valid title, and need regeneration
        if base_prompt and has_valid_title and needs_regeneration:
            # Prepare product information block
            info_lines = [f"Product Title: {title}"]
            
            if has_valid_bullets:
                bullets = [b.strip() for b in bullets_str.split("\n") if b.strip()]
                if bullets:
                    info_lines.append("Key Features:")
                    for bullet in bullets[:5]:  # Limit to top 5 bullet points
                        if len(bullet) > 10:  # Filter out very short bullets
                            info_lines.append(f"- {bullet}")
            
            info_block = "\n".join(info_lines)
            
            # Combine information with base prompt
            final_prompt = f"{info_block}\n\n{base_prompt}"
            
            df.at[idx, "Prompt"] = final_prompt
            updated_count += 1
            print(f"✅ Generated final prompt for row {idx}")
            
        elif not base_prompt:
            print(f"⚠️ Row {idx}: No base prompt")
        elif not has_valid_title:
            print(f"⚠️ Row {idx}: Invalid or missing title: '{title}'")
        else:
            print(f"⏭️ Row {idx}: Already has valid prompt, skipping")
    
    # Save back to Excel
    try:
        df.to_excel(excel_file, index=False)
        print(f"✅ Generated final prompts for {updated_count} products.")
        
        # Verify results
        df_verify = pd.read_excel(excel_file)
        valid_prompts = 0
        if 'Prompt' in df_verify.columns:
            for prompt in df_verify['Prompt']:
                prompt_str = str(prompt).strip()
                if (prompt_str and 
                    "Product Title: nan" not in prompt_str and 
                    len(prompt_str) > 100):
                    valid_prompts += 1
        print(f"📊 Verification: {valid_prompts} rows now have valid final prompts")
        
    except Exception as e:
        print(f"Error saving Excel file: {e}")
        import traceback
        traceback.print_exc()

def add_prompt_column_to_excel(excel_file: str):
    """Legacy function for backward compatibility - runs all three steps."""
    print("Running complete prompt generation pipeline...")
    crawl_amazon_data(excel_file)
    generate_base_prompts(excel_file)
    generate_final_prompts(excel_file)
    print("✅ Complete prompt generation pipeline finished.")

def regenerate_invalid_prompts(excel_file: str):
    """Regenerate prompts that contain 'Product Title: nan' or are invalid."""
    try:
        df = pd.read_excel(excel_file)
        
        if "Prompt" not in df.columns:
            print("No Prompt column found.")
            return
        
        # Find rows with invalid prompts
        invalid_mask = df['Prompt'].astype(str).str.contains('Product Title: nan', na=False)
        invalid_count = invalid_mask.sum()
        
        
        if invalid_count > 0:
            # Clear invalid prompts so they can be regenerated
            df.loc[invalid_mask, 'Prompt'] = ""
            
            # Save and regenerate
            df.to_excel(excel_file, index=False)
            print(f"✅ Cleared {invalid_count} invalid prompts")
            
            generate_final_prompts(excel_file)
            
    except Exception as e:
        print(f"Error regenerating prompts: {e}")

def reset_product_titles(excel_file: str):
    """Reset all 'nan' and invalid ProductTitle entries to allow re-crawling."""
    try:
        df = pd.read_excel(excel_file)
        
        if "ProductTitle" not in df.columns:
            print("No ProductTitle column found.")
            return
        
        # Count current invalid entries
        invalid_mask = df['ProductTitle'].astype(str).str.lower().isin(['nan', 'none', ''])
        invalid_count = invalid_mask.sum()
        
        print(f"Found {invalid_count} invalid ProductTitle entries")
        
        if invalid_count > 0:
            # Clear invalid entries
            df.loc[invalid_mask, 'ProductTitle'] = ""
            df.loc[invalid_mask, 'Bullets'] = ""
            df.loc[invalid_mask, 'Prompt'] = ""  # Also clear prompts so they get regenerated
            
            # Save back to Excel
            df.to_excel(excel_file, index=False)
            print(f"✅ Cleared {invalid_count} invalid ProductTitle entries and their prompts")
        else:
            print("No invalid entries found to clear")
            
    except Exception as e:
        print(f"Error resetting product titles: {e}")

def regenerate_invalid_prompts(excel_file: str):
    """Regenerate prompts that contain 'Product Title: nan' or are invalid."""
    logs = []
    
    try:
        df = pd.read_excel(excel_file)
        
        if "Prompt" not in df.columns:
            logs.append("❌ No Prompt column found.")
            return logs
        
        # Find rows with invalid prompts
        invalid_mask = df['Prompt'].astype(str).str.contains('Product Title: nan', na=False)
        invalid_count = invalid_mask.sum()  
        
        if invalid_count > 0:
            # Clear invalid prompts so they can be regenerated
            df.loc[invalid_mask, 'Prompt'] = ""
            
            # Save and regenerate
            df.to_excel(excel_file, index=False)
            logs.append(f"🧹 Cleared {invalid_count} invalid prompts")
            
            # Now regenerate them
            logs.append("🔄 Regenerating prompts...")
            regen_logs = generate_final_prompts(excel_file)
            logs.extend(regen_logs)
            
    except Exception as e:
        logs.append(f"❌ Error regenerating prompts: {e}")
    
    return logs

def get_failed_asins_info(excel_file: str):
    """Get information about ASINs that failed to crawl or have invalid data."""
    try:
        df = pd.read_excel(excel_file)
        
        failed_asins = []
        for idx, row in df.iterrows():
            asin = str(row.get("ASIN", "")).strip()
            title = str(row.get("ProductTitle", "")).strip()
            
            # Check if ASIN is valid but has no title or invalid title
            if (asin and len(asin) == 10 and asin.upper() != 'NAN' and
                (not title or title.lower() in ['nan', 'none', ''] or len(title) <= 3)):
                failed_asins.append({
                    'asin': asin,
                    'amazon_url': f"https://www.amazon.com/dp/{asin}",
                    'current_title': title if title.lower() not in ['nan', 'none'] else '',
                    'current_bullets': str(row.get("Bullets", "")).strip() if str(row.get("Bullets", "")).strip().lower() not in ['nan', 'none'] else ''
                })
        
        return failed_asins
    except Exception as e:
        print(f"Error getting failed ASINs info: {e}")
        return []

def check_voice_duration_issues(excel_file: str):
    """Check for ASINs with voice duration issues and return suggestions for WPM adjustment."""
    try:
        df = pd.read_excel(excel_file)
        
        if "VoiceDurationCheck" not in df.columns or "Duration" not in df.columns:
            return []
        
        problem_asins = []
        for idx, row in df.iterrows():
            asin = str(row.get("ASIN", "")).strip()
            duration = float(row.get("Duration", 0))
            voice_check = str(row.get("VoiceDurationCheck", "")).strip()
            
            if "too long" in voice_check.lower() or "failed" in voice_check.lower():
                # Try to extract actual voice duration from Audio2 file
                audio2_path = str(row.get("Audio2", "")).strip()
                voice_duration = 0
                
                if audio2_path and os.path.exists(audio2_path):
                    try:
                        import soundfile as sf
                        f = sf.SoundFile(audio2_path)
                        voice_duration = f.frames / f.samplerate
                    except:
                        voice_duration = 0
                
                if voice_duration > 0 and duration > 0:
                    current_ratio = voice_duration / duration
                    if current_ratio > 1.15:  # Voice is more than 115% of video duration
                        # Calculate recommended WPM to fit within 110% of video duration
                        target_ratio = 1.10
                        current_wpm = int(row.get("WordsPerSecond", 155))
                        recommended_wpm = int(current_wpm * current_ratio / target_ratio)
                        
                        problem_asins.append({
                            'asin': asin,
                            'video_duration': duration,
                            'voice_duration': voice_duration,
                            'current_ratio': current_ratio,
                            'current_wpm': current_wpm,
                            'recommended_wpm': recommended_wpm,
                            'voice_check': voice_check
                        })
        
        return problem_asins
    except Exception as e:
        print(f"Error checking voice duration issues: {e}")
        return []

def adjust_wpm_for_problem_asins(excel_file: str, problem_asins: list):
    """Adjust WPM for problematic ASINs and regenerate their base prompts."""
    logs = []
    
    try:
        df = pd.read_excel(excel_file)
        
        if "WordsPerSecond" not in df.columns:
            df["WordsPerSecond"] = 155
        
        updated_count = 0
        for problem in problem_asins:
            asin = problem['asin']
            new_wpm = problem['recommended_wpm']
            
            # Find and update the ASIN row
            asin_mask = df['ASIN'].astype(str) == asin
            if asin_mask.any():
                df.loc[asin_mask, 'WordsPerSecond'] = new_wpm
                
                # Clear the existing base prompt and final prompt so they get regenerated
                df.loc[asin_mask, 'BasePrompt'] = ""
                df.loc[asin_mask, 'Prompt'] = ""
                df.loc[asin_mask, 'Script'] = ""  # Also clear script
                df.loc[asin_mask, 'VoiceDurationCheck'] = ""  # Reset voice check
                
                updated_count += 1
                logs.append(f"✅ Updated {asin}: WPM {problem['current_wpm']} → {new_wpm}")
        
        if updated_count > 0:
            df.to_excel(excel_file, index=False)
            logs.append(f"💾 **Updated {updated_count} ASINs** with adjusted WPM")
            
            # Now regenerate base prompts for these ASINs
            logs.append("🔄 Regenerating base prompts with new WPM...")
            base_logs = generate_base_prompts(excel_file)
            logs.extend(base_logs)
            
            # Regenerate final prompts
            logs.append("🔄 Regenerating final prompts...")
            final_logs = generate_final_prompts(excel_file)
            logs.extend(final_logs)
            
        else:
            logs.append("❌ No ASINs were updated")
            
    except Exception as e:
        logs.append(f"❌ Error adjusting WPM: {e}")
    
    return logs

def update_manual_product_data(excel_file: str, manual_data: dict):
    """Update Excel file with manually entered product data."""
    logs = []
    try:
        df = pd.read_excel(excel_file)
        
        updated_count = 0
        for asin, data in manual_data.items():
            title = data.get('title', '').strip()
            bullets = data.get('bullets', '').strip()
            
            if title:  # Only update if title is provided
                # Find the row with this ASIN
                asin_mask = df['ASIN'].astype(str) == asin
                if asin_mask.any():
                    df.loc[asin_mask, 'ProductTitle'] = title
                    df.loc[asin_mask, 'Bullets'] = bullets
                    updated_count += 1
                    logs.append(f"✅ Updated {asin}: {title[:50]}...")
                else:
                    logs.append(f"⚠️ ASIN {asin} not found in Excel")
            else:
                logs.append(f"⏭️ Skipped {asin}: No title provided")
        
        if updated_count > 0:
            df.to_excel(excel_file, index=False)
            logs.append(f"💾 **Successfully updated {updated_count} ASINs** in Excel file")
        else:
            logs.append("❌ No ASINs were updated")
            
    except Exception as e:
        logs.append(f"❌ Error updating manual data: {e}")
    
    return logs

# Main execution functions for individual steps
def main_crawl_data(excel_file: str = "all.xlsx"):
    """Main function for crawling product data."""
    return crawl_amazon_data(excel_file)

def main_reset_titles(excel_file: str = "all.xlsx"):
    """Main function for resetting invalid titles."""
    reset_product_titles(excel_file)

def main_regenerate_prompts(excel_file: str = "all.xlsx"):
    """Main function for regenerating invalid prompts."""
    return regenerate_invalid_prompts(excel_file)

def main_generate_base_prompts(excel_file: str = "all.xlsx", wpm: int = 155):
    """Main function for generating base prompts."""
    return generate_base_prompts(excel_file, wpm)

def main_generate_final_prompts(excel_file: str = "all.xlsx"):
    """Main function for generating final prompts."""
    return generate_final_prompts(excel_file)

def main_get_failed_asins(excel_file: str = "all.xlsx"):
    """Main function for getting failed ASINs info."""
    return get_failed_asins_info(excel_file)

def main_update_manual_data(excel_file: str = "all.xlsx", manual_data: dict = None):
    """Main function for updating manual product data."""
    if manual_data is None:
        manual_data = {}
    return update_manual_product_data(excel_file, manual_data)

def main_check_voice_issues(excel_file: str = "all.xlsx"):
    """Main function for checking voice duration issues."""
    return check_voice_duration_issues(excel_file)

def main_adjust_wpm_for_problems(excel_file: str = "all.xlsx", problem_asins: list = None):
    """Main function for adjusting WPM for problematic ASINs."""
    if problem_asins is None:
        problem_asins = []
    return adjust_wpm_for_problem_asins(excel_file, problem_asins)

def test_single_asin(asin: str = "B08N5WRWNW"):
    """Test function to debug crawling with a single ASIN."""
    print(f"🧪 Testing crawl for ASIN: {asin}")
    print("=" * 50)
    
    try:
        result_asin, title, bullets = fetch_product_info_selenium(asin, max_retries=1)
        
        print(f"Results:")
        print(f"ASIN: {result_asin}")
        print(f"Title: {title}")
        print(f"Bullets ({len(bullets)} found):")
        for i, bullet in enumerate(bullets, 1):
            print(f"  {i}. {bullet[:100]}...")
        
        if title:
            print("✅ Test PASSED - Product info retrieved successfully")
        else:
            print("❌ Test FAILED - No product info retrieved")
            
    except Exception as e:
        print(f"❌ Test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 50)
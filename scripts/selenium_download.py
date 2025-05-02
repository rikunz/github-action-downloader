import time
import sys
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

def setup_logging():
    """Set up logging to capture ChromeDriver and script errors."""
    logging.basicConfig(
        filename="selenium_download.log",
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger()
    logger.info("Logging initialized")
    return logger

def monitor_download(download_dir, timeout=600, logger=None):
    """Monitor download progress by checking for .crdownload or completed files."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        files = os.listdir(download_dir) if os.path.exists(download_dir) else []
        crdownload_files = [f for f in files if f.endswith(".crdownload")]
        completed_files = [f for f in files if not f.endswith((".crdownload", ".tmp")) and not f.startswith(".org.chromium.")]
        
        if completed_files:
            file_path = os.path.join(download_dir, completed_files[0])
            size = os.path.getsize(file_path)
            logger.info(f"Completed file found: {file_path}, size: {size} bytes")
            print(f"Completed file found: {file_path}, size: {size} bytes")
            return True
        elif crdownload_files:
            file_path = os.path.join(download_dir, crdownload_files[0])
            size = os.path.getsize(file_path)
            logger.info(f"Download in progress: {file_path}, size: {size} bytes")
            print(f"Download in progress: {file_path}, size: {size} bytes")
        else:
            logger.info("No download files found yet")
            print("No download files found yet")
        
        time.sleep(10)
    logger.error("Download timed out")
    print("Download timed out")
    return False

def trigger_1fichier_download(url):
    logger = setup_logging()
    logger.info(f"Starting download for URL: {url}")
    print(f"Starting download for URL: {url}")

    driver = None
    try:
        # Create and setup download directory
        download_dir = os.path.join(os.getenv("GITHUB_WORKSPACE", "/tmp"), "downloads")
        if not os.path.exists(download_dir):
            os.makedirs(download_dir, exist_ok=True)
            logger.info(f"Created download directory: {download_dir}")
            print(f"Created download directory: {download_dir}")
        
        # Ensure directory has proper permissions
        os.chmod(download_dir, 0o777)
        logger.info(f"Set permissions to 777 for {download_dir}")
        print(f"Set permissions to 777 for {download_dir}")

        # Check directory permissions
        if not os.access(download_dir, os.W_OK):
            logger.error(f"No write permission for {download_dir}")
            print(f"Error: No write permission for {download_dir}. Please check directory permissions.")
            return False

        # Configure Chrome options
        chrome_options = Options()
        chrome_options.page_load_strategy = 'normal'
        chrome_options.add_argument("--headless")  # Uncomment for headless mode
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        # Custom prefs: block everything except automatic_downloads and javascript
        custom_prefs = {
            'profile.default_content_setting_values': {
            'cookies': 2, 'images': 2, 'plugins': 2, 'popups': 2, 'geolocation': 2,
            'notifications': 2, 'auto_select_certificate': 2, 'fullscreen': 2,
            'mouselock': 2, 'mixed_script': 2, 'media_stream': 2,
            'media_stream_mic': 2, 'media_stream_camera': 2, 'protocol_handlers': 2,
            'ppapi_broker': 2, 'midi_sysex': 2, 'push_messaging': 2,
            'ssl_cert_decisions': 2, 'metro_switch_to_desktop': 2,
            'protected_media_identifier': 2, 'app_banner': 2, 'site_engagement': 2,
            'durable_storage': 2
            # 'automatic_downloads' and 'javascript' intentionally omitted
            }
        }
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": str(download_dir.resolve()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            **custom_prefs
        })


        try:
            service = Service('/usr/bin/chromedriver')
            logger.info("Attempting to initialize ChromeDriver")
            print("Attempting to initialize ChromeDriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Initialized ChromeDriver")
            print("Initialized ChromeDriver")
            
            # Take initial screenshot
            try:
                driver.save_screenshot("initial_screenshot.png")
                print("Saved initial screenshot to initial_screenshot.png")
                logger.info("Saved initial screenshot to initial_screenshot.png")
            except Exception as e:
                print(f"Failed to save initial screenshot: {str(e)}")
                logger.error(f"Failed to save initial screenshot: {str(e)}")
        except WebDriverException as e:
            logger.error(f"Error initializing ChromeDriver: {str(e)}")
            print(f"Error initializing ChromeDriver: {str(e)}")
            print("Ensure ChromeDriver version matches Chrome browser version.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during ChromeDriver initialization: {str(e)}")
            print(f"Unexpected error during ChromeDriver initialization: {str(e)}")
            return False

        try:
            # Navigate to the URL
            print(f"Navigating to {url}")
            logger.info(f"Navigating to {url}")
            driver.get(url)
            
            # Wait for page to fully load
            driver.implicitly_wait(10)

            # Handle cookie notification if present
            print("Waiting for cookie box close button...")
            try:
                cookie_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "cookie_box_close"))
                )
                cookie_button.click()
                print("Clicked cookie box close button")
                logger.info("Clicked cookie box close button")
            except (TimeoutException, NoSuchElementException):
                print("Cookie box close button not found or not clickable. Continuing...")
                logger.warning("Cookie box close button not found or not clickable")

            # Wait for free download button to appear
            print("Waiting for dlb input to be visible and clickable...")
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.ID, "dlb"))
                )
                
                try:
                    dlb_input = driver.find_element(By.ID, "dlb")
                    dlb_input.click()
                    print("Clicked dlb input directly")
                    logger.info("Clicked dlb input directly")
                except Exception as e:
                    print(f"Direct click failed: {str(e)}. Trying JavaScript click...")
                    try:
                        driver.execute_script("document.getElementById('dlb').click();")
                        print("Clicked dlb input via JavaScript getElementById")
                        logger.info("Clicked dlb input via JavaScript getElementById")
                    except Exception as e2:
                        print(f"JavaScript getElementById click failed: {str(e2)}. Final attempt...")
                        try:
                            driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "dlb"))
                            print("Clicked dlb input via JavaScript arguments[0]")
                            logger.info("Clicked dlb input via JavaScript arguments[0]")
                        except Exception as e3:
                            print(f"All click methods failed: {str(e3)}")
                            logger.error(f"All click methods failed: {str(e3)}")
                            raise Exception("Could not click download button after multiple attempts")
            except (TimeoutException, Exception) as e:
                print(f"Timeout or error waiting for dlb input: {str(e)}")
                logger.error(f"Timeout or error waiting for dlb input: {str(e)}")
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("Saved page source to debug_page.html for inspection")
                
                try:
                    driver.save_screenshot("debug_screenshot.png")
                    print("Saved debug screenshot to debug_screenshot.png")
                    logger.info("Saved debug screenshot to debug_screenshot.png")
                except Exception as e:
                    print(f"Failed to save debug screenshot: {str(e)}")
                    logger.error(f"Failed to save debug screenshot: {str(e)}")
                return False

            # Wait for the OK button to appear and click it
            print("Waiting for ok-btn-general link...")
            try:
                ok_button = WebDriverWait(driver, 30).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'ok') and contains(@class, 'btn-general')]"))
                )
                download_url = ok_button.get_attribute("href")
                print(f"Found download URL: {download_url}")
                logger.info(f"Found download URL: {download_url}")
                driver.execute_script("arguments[0].scrollIntoView(true);", ok_button)
                time.sleep(0.5)
                try:
                    ok_button.click()
                    print("Clicked ok-btn-general link")
                    logger.info("Clicked ok-btn-general link")
                except WebDriverException:
                    print("Normal click failed, attempting JavaScript click...")
                    driver.execute_script("arguments[0].click();", ok_button)
                    print("Clicked ok-btn-general link via JavaScript")
                    logger.info("Clicked ok-btn-general link via JavaScript")
            except TimeoutException:
                print("Timeout waiting for ok-btn-general link.")
                logger.error("Timeout waiting for ok-btn-general link")
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("Saved page source to debug_page.html for inspection")
                
                try:
                    driver.save_screenshot("debug_screenshot.png")
                    print("Saved debug screenshot to debug_screenshot.png")
                    logger.info("Saved debug screenshot to debug_screenshot.png")
                except Exception as e:
                    print(f"Failed to save debug screenshot: {str(e)}")
                    logger.error(f"Failed to save debug screenshot: {str(e)}")
                return False

            # Monitor download progress
            print("Monitoring download progress...")
            logger.info("Monitoring download progress")
            if not monitor_download(download_dir, timeout=600, logger=logger):
                print("Download failed or timed out")
                logger.error("Download failed or timed out")
                return False

            # Save final state
            with open("final_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Saved final page source to final_page.html for inspection")
            
            try:
                driver.save_screenshot("final_screenshot.png")
                print("Saved final screenshot to final_screenshot.png")
                logger.info("Saved final screenshot to final_screenshot.png")
            except Exception as e:
                print(f"Failed to save final screenshot: {str(e)}")
                logger.error(f"Failed to save final screenshot: {str(e)}")

            # Return success
            print(f"Download process completed successfully. File should be saved to {download_dir}")
            logger.info(f"Download process completed successfully. File should be saved to {download_dir}")
            return True

        except WebDriverException as e:
            print(f"Error during page navigation or interaction: {str(e)}")
            logger.error(f"WebDriver error: {str(e)}")
            
            if driver:
                print(f"Current page title: {driver.title}")
                print(f"Current page URL: {driver.current_url}")
                
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("Saved page source to debug_page.html for inspection")
                
                try:
                    driver.save_screenshot("debug_screenshot.png")
                    print("Saved debug screenshot to debug_screenshot.png")
                    logger.info("Saved debug screenshot to debug_screenshot.png")
                except Exception as e:
                    print(f"Failed to save debug screenshot: {str(e)}")
                    logger.error(f"Failed to save debug screenshot: {str(e)}")
            return False

        finally:
            # Close browser only after download is complete or timed out
            if driver:
                try:
                    driver.quit()
                    logger.info("Closed browser")
                    print("Closed browser")
                except Exception as e:
                    logger.error(f"Error closing browser: {str(e)}")
                    print(f"Error closing browser: {str(e)}")

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        logger.error(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python selenium_download.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    success = trigger_1fichier_download(url)
    if success:
        print("Download triggered successfully!")
        sys.exit(0)
    else:
        print("Failed to trigger download.")
        sys.exit(1)
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
        chrome_options.page_load_strategy = 'eager'
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
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
            print(f"Download triggered successfully. Browser left open.")
            logger.info(f"Download triggered successfully. Browser left open.")
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
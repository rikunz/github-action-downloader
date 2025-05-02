import time
import sys
import os
import logging
import tempfile
import shutil
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

def clean_chrome_processes():
    """Kill any existing Chrome and ChromeDriver processes and clean temp directories."""
    logger = setup_logging()
    try:
        logger.info("Checking running Chrome processes before cleanup")
        os.system("ps aux | grep -E 'chromedriver|chromium' > chrome_processes.log")
        print("Saved running processes to chrome_processes.log")

        os.system("pkill -9 -f chromedriver >/dev/null 2>&1 || true")
        os.system("pkill -9 -f chromium >/dev/null 2>&1 || true")
        time.sleep(2)

        temp_dirs = [d for d in os.listdir('/tmp') if d.startswith('.com.google.Chrome') or d.startswith('chrome-user-data')]
        for temp_dir in temp_dirs:
            try:
                shutil.rmtree(os.path.join('/tmp', temp_dir))
                logger.info(f"Removed temporary Chrome data directory: /tmp/{temp_dir}")
                print(f"Removed temporary Chrome data directory: /tmp/{temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove /tmp/{temp_dir}: {str(e)}")
                print(f"Warning: Failed to remove /tmp/{temp_dir}: {str(e)}")
    except Exception as e:
        logger.warning(f"Failed to clean Chrome processes: {str(e)}")
        print(f"Warning: Failed to clean Chrome processes: {str(e)}")

def trigger_1fichier_download(url, download_dir):
    logger = setup_logging()
    logger.info(f"Starting download for URL: {url}, Download dir: {download_dir}")
    print(f"Starting download for URL: {url}, Download dir: {download_dir}")

    try:
        if not os.path.exists(download_dir):
            os.makedirs(download_dir, mode=0o777)
            logger.info(f"Created download directory: {download_dir}")
            print(f"Created download directory: {download_dir}")
        if not os.access(download_dir, os.W_OK):
            logger.error(f"No write permission for {download_dir}")
            print(f"Error: No write permission for {download_dir}. Please check directory permissions.")
            return False
        os.chmod(download_dir, 0o777)
        logger.info(f"Set permissions to 777 for {download_dir}")
        print(f"Set permissions to 777 for {download_dir}")

        clean_chrome_processes()

        user_data_dir = tempfile.mkdtemp(prefix="chrome-user-data-")
        logger.info(f"Using temporary user data directory: {user_data_dir}")
        print(f"Using temporary user data directory: {user_data_dir}")

        chrome_options = Options()
        chrome_options.page_load_strategy = 'normal'
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "safebrowsing_for_trusted_sources_enabled": False,
            "profile.default_content_settings.popups": 0
        })
        chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL', 'driver': 'ALL'})

        try:
            service = Service('/usr/bin/chromedriver', log_path="chromedriver.log")
            logger.info("Attempting to initialize ChromeDriver")
            print("Attempting to initialize ChromeDriver")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Initialized ChromeDriver")
            print("Initialized ChromeDriver")
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
            print(f"Navigating to {url}")
            logger.info(f"Navigating to {url}")
            driver.get(url)

            print("Waiting for cookie box close button...")
            try:
                cookie_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "cookie_box_close"))
                )
                cookie_button.click()
                print("Clicked cookie box close button")
                logger.info("Clicked cookie box close button")
            except TimeoutException:
                print("Timeout waiting for cookie box close button. It may not be present.")
                logger.warning("Timeout waiting for cookie box close button")
            except NoSuchElementException:
                print("Cookie box close button not found on page.")
                logger.warning("Cookie box close button not found")

            print("Waiting for dlb input to be visible and clickable...")
            try:
                dlb_input = WebDriverWait(driver, 60).until(
                    EC.visibility_of_element_located((By.ID, "dlb"))
                )
                WebDriverWait(driver, 60).until(
                    EC.element_to_be_clickable((By.ID, "dlb"))
                )
                try:
                    dlb_input.click()
                    print("Clicked dlb input")
                    logger.info("Clicked dlb input")
                except WebDriverException:
                    print("Normal click failed, attempting JavaScript click...")
                    driver.execute_script("arguments[0].click();", dlb_input)
                    print("Clicked dlb input via JavaScript")
                    logger.info("Clicked dlb input via JavaScript")
            except TimeoutException:
                print("Timeout waiting for dlb input to be visible or clickable.")
                logger.error("Timeout waiting for dlb input")
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

            print("Checking for ad overlays...")
            try:
                ad_close_buttons = driver.find_elements(By.CSS_SELECTOR, ".st-placement.inScreen [id*='close'], .st-adunit [id*='close'], [id*='r89-'] [id*='close']")
                for btn in ad_close_buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        try:
                            driver.execute_script("arguments[0].click();", btn)
                            print("Closed ad overlay")
                            logger.info("Closed ad overlay")
                            time.sleep(1)
                        except:
                            print("Failed to close ad overlay, continuing...")
                            logger.warning("Failed to close ad overlay")
            except NoSuchElementException:
                print("No ad close buttons found.")
                logger.info("No ad close buttons found")

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

            print("Waiting for download to initiate...")
            time.sleep(60)
            browser_logs = driver.get_log('browser')
            print("Browser logs:")
            for entry in browser_logs:
                print(f"[{entry['level']}] {entry['message']}")
                logger.info(f"Browser log: [{entry['level']}] {entry['message']}")
            print(f"Contents of download directory {download_dir}:")
            dir_contents = os.listdir(download_dir) if os.path.exists(download_dir) else []
            print(dir_contents if dir_contents else "Empty")
            logger.info(f"Download directory contents: {dir_contents if dir_contents else 'Empty'}")
            print("Running Chrome processes:")
            os.system("ps aux | grep -E 'chromedriver|chromium' || true")
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

            return True

        except WebDriverException as e:
            print(f"Error during page navigation or interaction: {str(e)}")
            logger.error(f"WebDriver error: {str(e)}")
            print(f"Current page title: {driver.title if 'driver' in locals() else 'Driver not initialized'}")
            print(f"Current page URL: {driver.current_url if 'driver' in locals() else 'Driver not initialized'}")
            if 'driver' in locals():
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
            pass

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        logger.error(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python selenium_download.py <url> <download_dir>")
        sys.exit(1)

    url = sys.argv[1]
    download_dir = sys.argv[2]
    success = trigger_1fichier_download(url, download_dir)
    if success:
        print("Download triggered successfully!")
        sys.exit(0)
    else:
        print("Failed to trigger download.")
        sys.exit(1)
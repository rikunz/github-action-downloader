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
    return logging.getLogger()

def trigger_1fichier_download(url, download_dir):
    logger = setup_logging()
    try:
        # Ensure the download directory exists and is writable
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            logger.info(f"Created download directory: {download_dir}")
        if not os.access(download_dir, os.W_OK):
            logger.error(f"No write permission for {download_dir}")
            print(f"Error: No write permission for {download_dir}. Please check directory permissions.")
            return False, None

        # Configure Chrome options
        chrome_options = Options()
        chrome_options.page_load_strategy = 'normal'
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36")
        # Set download directory and disable download prompt
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "safebrowsing_for_trusted_sources_enabled": False,
            "profile.default_content_settings.popups": 0
        })
        # Enable browser logging
        chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL', 'driver': 'ALL'})
        # Prevent browser from closing immediately
        chrome_options.add_experimental_option("detach", True)

        try:
            service = Service('/usr/bin/chromedriver', log_path="chromedriver.log")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Initialized ChromeDriver")
        except WebDriverException as e:
            logger.error(f"Error initializing ChromeDriver: {str(e)}")
            print(f"Error initializing ChromeDriver: {str(e)}")
            print("Ensure ChromeDriver version matches Chrome browser version.")
            return False, None

        try:
            print(f"Navigating to {url}")
            logger.info(f"Navigating to {url}")
            driver.get(url)

            # Wait for cookie box close button and click it
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

            # Wait for the <input id="dlb"> to be visible and clickable
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
                return False, None

            # Attempt to dismiss any ad overlays
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

            # Wait for ok-btn-general <a> tag
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
                return False, None

            # Extract filename from page or URL
            print("Extracting filename...")
            try:
                filename_element = driver.find_element(By.XPATH, "//td[@class='normal'][contains(text(), '.')]")
                filename = filename_element.text.strip()
                print(f"Extracted filename: {filename}")
                logger.info(f"Extracted filename: {filename}")
            except NoSuchElementException:
                print("Could not find filename on page.")
                logger.warning("Could not find filename on page")
                filename = None

            # Monitor download initiation
            print("Waiting for download to initiate...")
            time.sleep(10)
            browser_logs = driver.get_log('browser')
            for entry in browser_logs:
                if "error" in entry.get("level", "").lower() or "something went wrong" in entry.get("message", "").lower():
                    print(f"Browser error detected: {entry['message']}")
                    logger.error(f"Browser error: {entry['message']}")

            return True, filename

        except WebDriverException as e:
            print(f"Error during page navigation or interaction: {str(e)}")
            logger.error(f"WebDriver error: {str(e)}")
            print(f"Current page title: {driver.title if 'driver' in locals() else 'Driver not initialized'}")
            print(f"Current page URL: {driver.current_url if 'driver' in locals() else 'Driver not initialized'}")
            if 'driver' in locals():
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("Saved page source to debug_page.html for inspection")
            return False, None

        finally:
            # Do not close the browser to allow download to complete
            if 'driver' in locals():
                browser_logs = driver.get_log('browser')
                for entry in browser_logs:
                    logger.debug(f"Browser log: {entry}")
                print("Browser left open for download. Close manually when download completes.")
                logger.info("Browser left open for download")

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        logger.error(f"Unexpected error: {str(e)}")
        return False, None

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python selenium_download.py <url> <download_dir>")
        sys.exit(1)

    url = sys.argv[1]
    download_dir = sys.argv[2]
    success, filename = trigger_1fichier_download(url, download_dir)
    if success and filename:
        print(f"Download triggered successfully! Filename: {filename}")
    else:
        print("Failed to trigger download or extract filename.")

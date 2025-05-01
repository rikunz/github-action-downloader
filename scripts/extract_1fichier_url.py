import requests
from bs4 import BeautifulSoup
import sys
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

def get_1fichier_cookies(url):
    try:
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
        ]
        selected_user_agent = random.choice(user_agents)

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={selected_user_agent}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.page_load_strategy = 'eager'

        try:
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except WebDriverException as e:
            print(f"Error initializing ChromeDriver: {str(e)}")
            return None, None, None

        try:
            print(f"Navigating to {url}")
            driver.get(url)

            print("Waiting for cookie box close button...")
            try:
                cookie_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "cookie_box_close"))
                )
                print("Cookie box found, clicking...")
                cookie_button.click()
            except (TimeoutException, NoSuchElementException) as e:
                print(f"Cookie box not found or timed out: {str(e)}")
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("Saved page source to debug_page.html")

            print("Waiting for cookies...")
            time.sleep(5)

            cookies = driver.get_cookies()
            shared_id = None
            shared_id_cst = None
            for cookie in cookies:
                if cookie['name'] == '_sharedID':
                    shared_id = cookie['value']
                elif cookie['name'] == '_sharedID_cst':
                    shared_id_cst = cookie['value']

            if shared_id and shared_id_cst:
                print(f"SHARED_ID={shared_id}")
                print(f"SHARED_ID_CST={shared_id_cst}")
                return shared_id, shared_id_cst, selected_user_agent
            else:
                print("Failed to find cookies")
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                return None, None, None

        except WebDriverException as e:
            print(f"Error during navigation: {str(e)}")
            if 'driver' in locals():
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            return None, None, None

        finally:
            if 'driver' in locals():
                driver.quit()
                print("Closed browser")

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None, None, None

def extract_1fichier_url(url, shared_id, shared_id_cst, user_agent):
    try:
        session = requests.Session()
        cookies_dict = {
            '_sharedID': shared_id,
            '_sharedID_cst': shared_id_cst
        }
        session.cookies.update(cookies_dict)

        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Referer': url
        }

        response = session.get(url, headers=headers, allow_redirects=True)
        if response.status_code != 200:
            print(f"Failed GET: Status {response.status_code}")
            with open("debug_get.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            return None, None, None, None

        with open("debug_get.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        soup = BeautifulSoup(response.content, 'html.parser')
        adz_input = soup.find('input', {'name': 'adz'})
        if not adz_input:
            print("Could not find adz input")
            return None, None, None, None
        adz = adz_input.get('value', '')

        filename_elements = soup.find_all('td', class_='normal')
        if len(filename_elements) < 2:
            print("Could not find filename")
            return None, None, None, None
        filename = filename_elements[1].text.strip()

        cookies_dict['show_cm'] = 'no'
        session.cookies.update(cookies_dict)
        data = {"adz": adz, "did": 0, "dlinline": "on"}
        post_response = session.post(url, headers=headers, data=data, allow_redirects=True)
        if post_response.status_code != 200:
            print(f"Failed POST: Status {post_response.status_code}")
            with open("debug_post.html", "w", encoding="utf-8") as f:
                f.write(post_response.text)
            return None, None, None, None

        with open("debug_post.html", "w", encoding="utf-8") as f:
            f.write(post_response.text)

        soup = BeautifulSoup(post_response.content, 'html.parser')
        links = soup.find_all('a', class_='ok btn-general btn-orange')
        download_url = None
        for link in links:
            if "Click here to download the file" in link.text:
                download_url = link.get('href')
                break

        if not download_url:
            print("Could not find download URL")
            return None, None, None, None

        return download_url, filename, shared_id, shared_id_cst

    except Exception as e:
        print(f"Error during extraction: {str(e)}")
        return None, None, None, None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_1fichier_url.py <url>")
        sys.exit(1)
    url = sys.argv[1]

    shared_id, shared_id_cst, user_agent = get_1fichier_cookies(url)
    if not shared_id or not shared_id_cst or not user_agent:
        print("Failed to get cookies or User-Agent")
        sys.exit(1)

    download_url, filename, shared_id, shared_id_cst = extract_1fichier_url(url, shared_id, shared_id_cst, user_agent)
    if download_url and filename and shared_id and shared_id_cst:
        print(f"DOWNLOAD_URL={download_url}")
        print(f"FILENAME={filename}")
        print(f"SHARED_ID={shared_id}")
        print(f"SHARED_ID_CST={shared_id_cst}")
        print(f"USER_AGENT={user_agent}")
    else:
        print("Extraction failed")
        sys.exit(1)

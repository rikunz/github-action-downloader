import requests
from bs4 import BeautifulSoup
import sys

def extract_1fichier_url(url):
    try:
        # Initial GET request
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to access URL: Status {response.status_code}")
            return None, None

        # Parse HTML to extract adz and filename
        soup = BeautifulSoup(response.content, 'html.parser')
        adz_input = soup.find_all('input')
        if not adz_input:
            print("Could not find adz input")
            return None, None
        adz = str(adz_input[0]).replace('<input name="adz" type="hidden" value="', '').replace('"/>', '')

        filename_elements = soup.find_all('td', class_='normal')
        if len(filename_elements) < 2:
            print("Could not find filename")
            return None, None
        filename = str(filename_elements[1]).replace('<td class="normal">', '').replace('</td>', '')

        # POST request to get download page
        data = {"adz": adz, "did": 0, "dlinline": "on"}
        post_response = requests.post(url, data=data)
        if post_response.status_code != 200:
            print(f"POST request failed: Status {post_response.status_code}")
            return None, None

        # Parse POST response to find download link
        soup = BeautifulSoup(post_response.content, 'html.parser')
        links = soup.find_all('a')
        target_text = "Click here to download the file"
        download_url = None
        for link in links:
            if target_text in str(link):
                download_url = str(link).replace('<a class="ok btn-general btn-orange" href="', '').replace('" style="float:none;margin:auto;font-weight:bold;padding: 10px;margin: 10px;font-size:+1.6em;border:2px solid red">Click here to download the file</a>', '')
                break

        if not download_url:
            print("Could not find download URL")
            return None, None

        return download_url, filename
    except Exception as e:
        print(f"Error during extraction: {str(e)}")
        return None, None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_1fichier_url.py <url>")
        sys.exit(1)
    url = sys.argv[1]
    download_url, filename = extract_1fichier_url(url)
    if download_url and filename:
        print(f"DOWNLOAD_URL={download_url}")
        print(f"FILENAME={filename}")
    else:
        print("Extraction failed")
        sys.exit(1)
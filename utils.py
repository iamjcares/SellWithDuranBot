import csv
import gzip
import io
import json
import os
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait


def load_config():
    """
    Load the configuration file.

    Returns:
        dict: The configuration file as a dictionary.
    """
    with open('config.json') as config_file:
        config = json.load(config_file)
    return config


def load_sitemap(url, output_path):
    """
    Download and extract the sitemap.
    
    Args: url (str): The URL of the sitemap.
         output_path (str): The path to save the sitemap file.
    
    Returns:
        bool: True if the sitemap was downloaded and extracted successfully, False otherwise.
    """
    print('Downloading sitemap...')
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print(f"An error occurred while downloading the sitemap: {err}")
        return False
    
    try:
        compressed_file = io.BytesIO(response.content)
        decompressed_file = gzip.GzipFile(fileobj=compressed_file)
        
        with open(output_path, 'wb') as outfile:
            outfile.write(decompressed_file.read())
    except Exception as err:
        print(f"An error occurred while decompressing the sitemap file: {err}")
        return False
    
    return True


def parse_sitemap(sitemap_path):
    """
    Parse the sitemap file and extract the URLs and last modification dates.
    
    Args:
        sitemap_path (str): The path to the sitemap file.
        
    Returns:
        list: A list of tuples containing the URLs and last modification dates.
    """
    
    try:
        tree = ET.parse(sitemap_path)
    except ET.ParseError as err:
        print(f"An error occurred while parsing the sitemap: {err}")
        return []

    root = tree.getroot()

    # Namespace dictionary to access the "loc" and "lastmod" tags
    namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    urls = [(url.find('ns:loc', namespaces).text, url.find('ns:lastmod', namespaces).text) for url in root.findall('.//ns:url', namespaces)]

    return urls

def filter_urls_by_date(urls, date):
    """
    Filter the URLs by last modification date.

    Args:
        urls (list): A list of tuples containing the URLs and last modification dates.
        date (date): The date to filter by.

    Returns:
        list: A list of URLs that match the date.
    """
    return [url for url, lastmod in urls if lastmod == date]

def save_urls_to_file(file_path, urls):
    """
    Save the URLs to a CSV file.

    Args:
        file_path (string): The path to the CSV file.
        urls (_type_): URLs to save.
    """
    if not len(urls):
        print("No URLs to save.")
        return
    try:
        with open(file_path, 'a', newline='') as f:
            writer = csv.writer(f)
            for url in urls:
                writer.writerow([url])
    except Exception as err:
        print(f"An error occurred while writing to the CSV file: {err}")
        
def remove_url_from_file(file_path, url):
    """
    Remove the URL from the CSV file.

    Args:
        file_path (string): The path to the CSV file.
        url (string): The URL to remove.
    """
    try:
        with open(file_path, 'r', newline='') as f:
            reader = csv.reader(f)
            processed_urls = [row[0] for row in reader]
    except FileNotFoundError:
        # If the file doesn't exist yet, consider all URLs as unprocessed
        processed_urls = []

    processed_urls.remove(url)
    
    try:
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            for url in processed_urls:
                writer.writerow([url])
    except Exception as err:
        print(f"An error occurred while writing to the CSV file: {err}")
        


def filter_processed_urls(urls, file_path):
    """
    Filter the URLs by the ones that haven't been processed yet.

    Args:
        urls (list): A list of URLs to filter.
        file_path (string): The path to the CSV file containing the processed URLs.

    Returns:
        list: A list of URLs that haven't been processed yet.
    """
    try:
        with open(file_path, 'r', newline='') as f:
            reader = csv.reader(f)
            processed_urls = {row[0] for row in reader}
    except FileNotFoundError:
        # If the file doesn't exist yet, consider all URLs as unprocessed
        processed_urls = set()

    return [url for url in urls if url not in processed_urls]


def create_target_url(url, cutoff=3):
    """
    Create the target URL from the original URL.

    Args:
        url (string): The original URL.
        cutoff (int, optional): The number of parts to remove from the URL. Defaults to 3.

    Returns:
        string: The target URL.
    """
    try:
        parts = url.split('-')
        parts = parts[:-cutoff]
        target_url = f"https://www.sellwithduran.com/property/{parts[1]}/{'-'.join(parts[2:])}/"
        return target_url
    except Exception as err:
        print(f"An error occurred while creating target URLs: {err}")
        return False
    

def create_target_urls(urls, cutoff=3):
    """
    Create the target URLs from the original URLs.

    Args:
        urls (list): A list of original URLs.
        cutoff (int, optional): The number of parts to remove from the URL. Defaults to 3.

    Returns:
        list: A list of target URLs.
    """
    target_urls = [ create_target_url(url, cutoff) for url in urls ]
    return target_urls
    

def page_has_loaded(driver):
    return driver.find_element(By.ID, '__layout')

def extract_data(url, to_extract):
    config = load_config()
    try:
        if config['os'] == 'mac':
            driver = webdriver.Chrome(config['chromedriver_mac'])
        elif config['os'] == 'windows':
            driver = webdriver.Chrome(config['chromedriver_windows'])
        else:
            driver = webdriver.Chrome(config['chromedriver_linux'])
        
        # driver = webdriver.Chrome()

        driver.get(url)
        # driver.implicitly_wait(30)
        WebDriverWait(driver, timeout=10).until(page_has_loaded)

        extracted_data = {}
        
        for field, class_name in to_extract.items():
            try:
                element = driver.find_element(By.CLASS_NAME, class_name)
                extracted_data[field] = element.text
            except NoSuchElementException:
                print(f"Element {field} not found on page {url}")
                extracted_data[field] = ''

        driver.quit()
        return extracted_data
    except Exception as err:
        print(f"An error occurred while extracting data: {err}")
        return []
    


def extract_params_from_url(url):
    """
    Extract the domain, MLS ID, and address from the URL.

    Args:
        url (string): The URL to extract from.

    Returns:
        tuple: A tuple containing the domain, MLS ID, and address.
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path_parts = parsed_url.path.strip('/').split('/')
        mlsid = path_parts[1]
        address = path_parts[2].replace('-', ' ')
        return domain, mlsid, address
    except Exception as err:
        print(f"An error occurred while extracting information from {url}: {err}")
        return None, None, None


def get_json_data(api_url ,url, key):
    """
    Get the JSON data from the API.

    Args:
        api_url (string): API URL to use.
        url (string): URL to extract data from.
        key (string): API key to use.

    Returns:
        dict: The JSON data.
    """
    domain, mlsid, address = extract_params_from_url(url)
    if not domain or not mlsid or not address:
        return False
    
    try:
        response = requests.get(
            api_url,
            headers={'Authorization': f'Bearer {key}'},
            params={
                'mlsid': mlsid, 'address': address, 'domain': domain,
            }
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print(f"An error occurred while downloading the property details: {err}")
        return False

    try:
        response = response.json()
        listing = response['listing']
        if not listing:
            print(f"Listing not found for URL {url}")
            return False
        return listing
    except Exception as err:
        print(f"An error occurred while parsing the property: {err}")
        return False


def parse_data(data, toExtract):
    """
    Parse the data and extract the needed fields.

    Args:
        data (dict): The data to parse.
        toExtract (dict): The fields to extract.

    Returns:
        dict: The extracted fields with data.
    """
    response = {}
    
    for field, value in toExtract.items():
        if value in data:
            if field == 'photourl':
                response[field] = data[value][0] if len(data[value]) else ''
            elif field == 'status':
                statuses = {
                    'comingSoon': 'Coming Soon',
                    'active': 'Available',
                    'openHouse': 'Available',
                    'justListed': 'Available',
                    'priceReduced': 'Price reduced',
                    'sold': 'Sold',
                }
                response[field] = statuses[data[value]] if data[value] in statuses else 'Available'
            else:
                response[field] = data[value]
        else:
            print(f"Field {field} not found in the response.")
            response[field] = ''
            
    return response

def post_data(url, data):
    """
    Post the data to the webform.

    Args:
        url (string): Webform URL to post to.
        data (dict): Data to post.

    Returns:
        bool: True if the data was posted successfully, False otherwise.
    """
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print(f"Data posted successfully: {response.text}")
        return True
    else:
        print(f"An error occurred while posting the data: {response.status_code}: {response.text}")

def process_url(url, config, max_cutoff = 6):
    """
    Process the URL - extract the data, parse it, and post it to the webform.

    Args:
        url (string): URL to process.
        config (dict): Configuration dictionary.
        max_cutoff (int, optional): The maximum number of parts to remove from the URL. Defaults to 6.

    Returns:
        bool: True if the URL was processed successfully, False otherwise.
    """
    current_cutoff = 3
    extracted = None
    
    while (current_cutoff <= max_cutoff) and (not extracted):
        print(f"Trying cutoff {current_cutoff} for {url}...")
        new_url = create_target_url(url, current_cutoff)
        if new_url == False:
            print("Failed to create target URL. Exiting.")
            save_urls_to_file(config['unprocessed_urls'], [url])
            return False
        extracted = get_json_data(config['api_url'], new_url, config['vendor_token'])
        current_cutoff += 1
        
    if not extracted:
        print("Failed to extract data. Exiting.")
        save_urls_to_file(config['unprocessed_urls'], [url])
        return False
        
    needed = parse_data(extracted, config['api_extraction'])
    
    processed = post_data(config['webform_url'], needed)
    
    if not processed:
        print("Failed to post data. Exiting.")
        save_urls_to_file(config['unsaved_urls'], [url])
        return False
    print('Processed URL: ', url)

    save_urls_to_file(config['processed_urls'], [url])
    
    return True



def cleanup(filepath):
    """
    Delete the sitemap file.

    Args:
        filepath (string): The path to the sitemap file.
    """
    print('Deleting sitemap file...')
    os.remove(filepath)


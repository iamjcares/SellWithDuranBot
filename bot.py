import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from utils import *


def process_sitemap(date = None, filter_by_date = True):
    config = load_config()
    
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
        
    if not load_sitemap(config['sitemap_url'], config['sitemap_file']):
        print('Unable to download and extract sitemap. Exiting...')
        return

    urls = parse_sitemap(config['sitemap_file'])
    if not urls:
        print("Failed to parse sitemap. Exiting...")
        return
        
    print(f"Found {len(urls)} URLs in the sitemap.")
    
    if filter_by_date:
        if(type(date) == str):    
            date = [date]
        filtered_urls = filter_urls_by_dates(urls, date)
    else:
        filtered_urls = [url for url, lastmod in urls]

    print(f"Found {len(filtered_urls)} URLs for today.")

    filtered_urls = filter_processed_urls(filtered_urls, config['processed_urls'])
    filtered_urls = filter_processed_urls(filtered_urls, config['unprocessed_urls'])
    # filtered_urls = filter_processed_urls(filtered_urls, config['unsaved_urls'])
    
    filtered_urls = filtered_urls[:config['max_scrap']]

    print(f"Found {len(filtered_urls)} URLs that haven't been processed yet.")

    start_time = time.time()
    
    # create a thread pool of 10 threads
    with ThreadPoolExecutor() as executor:
        executor.map(process_url, filtered_urls, [config]*len(filtered_urls))

    duration = time.time() - start_time
    print(f"Downloaded {len(filtered_urls)} in {duration} seconds")

    # delete the sitemap file
    cleanup(config['sitemap_file'])
    


def main():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    process_sitemap(yesterday)
    
def processMultiDates(days):
    dates = []
    for i in range(days):
        dates.append((datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'))
    process_sitemap(dates)
    

if __name__ == "__main__":
    # main()
    processMultiDates(10)
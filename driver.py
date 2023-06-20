from utils import *

config = load_config()


url = 'https://www.sellwithduran.com/property/1-H6255197-253-Merrick-Avenue-Hempstead-NY-11554'

url = create_target_url(url, 3)

print(url)

url = 'https://www.sellwithduran.com/property/3483489/18-Greenbrush-Court'

extracted = get_json_data(config['api_url'], url, config['vendor_token'])

# print(extracted)
if not extracted:
    print("Failed to extract data. Exiting.")
    exit(1)
    

needed = parse_data(extracted, config['api_extraction'])

print(needed)

# send = post_data(config['webform_url'], needed)

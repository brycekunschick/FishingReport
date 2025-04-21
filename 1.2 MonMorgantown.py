import requests
import re
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup

# Source 1: Lake Water Level (USGS)

# Read URLs from the csv list, create function to get them
urls_df = pd.read_csv('1.0 URLs.csv')

def get_url_by_index(index):
    url = urls_df.loc[urls_df['index'] == index, 'url'].values[0]
    return url

# Date Parameters for URL
date1 = pd.Timestamp.now()
date2 = date1 - pd.Timedelta(days=2)

dates = pd.Series([date1, date2]).astype(str)
dates = dates.str.slice(0,23)
dates = dates.str.replace(' ', 'T')

# USGS link for last 48h
url_usgs = get_url_by_index(2)
url_usgs = url_usgs.replace('date1', dates[0]).replace('date2', dates[1])

# Get URL content
response_usgs = requests.get(url_usgs)

# Load text if request was successful
if response_usgs.status_code == 200:
    text_content = response_usgs.text
    print("Request successful")
else:
    print(f"Request failed. Status code: {response_usgs.status_code}")

# Trim string down to just the data
data_start = "agency_cd"
start_index = text_content.find(data_start)

text_data = text_content[start_index:]
text_data = StringIO(text_data)

usgs_data = pd.read_csv(text_data, delimiter='\t')
usgs_data = usgs_data[usgs_data['agency_cd'] != '5s']

# Column adjustments
usgs_data = usgs_data[['datetime', '160485_00065']]
usgs_data = usgs_data.rename(columns={'160485_00065': 'surface_level'})
usgs_data['surface_level'] = usgs_data['surface_level'].astype(float)

# Create variable for 24h water level change
 
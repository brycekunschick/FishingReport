import requests
import re
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup



# Source 1: Creek Water Level - 0.7 miles from outflow (USGS)

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
url_usgs = get_url_by_index(3)
url_usgs = url_usgs.replace('date1', dates[0]).replace('date2', dates[1])

print(url_usgs)
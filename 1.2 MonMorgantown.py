import requests
import re
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
import ollama
from ollama import chat
from ollama import ChatResponse


# Source 1: River Water Level at Hildebrand Lock/Dam (USGS)

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




# Source 2: Weather Data (NOAA)

# Weather data URL (no parameters needed)
url_noaa = get_url_by_index(1)

# Get URL content
response_noaa = requests.get(url_noaa)

# Load HTML data if request was successful
if response_noaa.status_code == 200:
    html_content = response_noaa.text
    print("Request successful")
else:
    print("Request failed. Status code: {response.status_code}")

# Parse with bs4
html_parsed = BeautifulSoup(html_content, 'html.parser')
table = html_parsed.find('table', class_='obs-history')
table_data = []

tbody = table.find('tbody')

for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            row_data = [cell.text for cell in cells]
            table_data.append(row_data)

# Save to df and format
noaa_data = pd.DataFrame(table_data)
noaa_data = noaa_data.iloc[:, [0, 1, 2, 6, 13]]
noaa_data.columns = ['Day', 'Time', 'Wind', 'Temp', 'Pressure']

noaa_data['Day'] = noaa_data['Day'].str.pad(width=2, side='left', fillchar='0')

# Fix date values
today = pd.Timestamp.now()
today_year = today.strftime('%Y')
today_month = today.strftime('%m')
today_day = noaa_data.iloc[0]['Day']
today_time = noaa_data.iloc[0]['Time']
date_string = f"{today_year}-{today_month}-{today_day} {today_time}:00"
today_datetime = pd.to_datetime(date_string)

# Create a new datetime column, fill in values by hour
noaa_data['Date'] = pd.NaT
noaa_data.loc[0, 'Date'] = today_datetime

date_subtract = today_datetime

for i in range(1, len(noaa_data)):
     date_subtract = date_subtract - pd.Timedelta(hours=1)
     noaa_data.loc[i, 'Date'] = date_subtract

# Clean up the values for wind
noaa_data['Wind'] = noaa_data['Wind'].astype(str)

def wind_fix(wind_value):
    """Function to fix formatting of wind values"""
    if isinstance(wind_value, str):
        if "Calm" in wind_value:
            return "0"
        elif "G" in wind_value:  # Remove gust info
            return ''.join(filter(str.isdigit, wind_value.split("G")[0].strip()))
        else:  # Keep only numeric chars
            return ''.join(filter(str.isdigit, wind_value))
    return wind_value

noaa_data['Wind'] = noaa_data['Wind'].apply(wind_fix)

# Final column adjustments
noaa_data = noaa_data.drop(columns=['Day', 'Time'])
noaa_data['Wind'] = noaa_data['Wind'].astype(int)
noaa_data['Temp'] = noaa_data['Temp'].astype(float)
noaa_data['Pressure'] = noaa_data['Pressure'].astype(float)



# 3. Prepare variables for LLM

# 24h water level change from min or max (whichever is greater)
usgs_data_24h = usgs_data[len(usgs_data)-96:]
chng_from_max = usgs_data_24h.iloc[-1]['surface_level'] - usgs_data_24h['surface_level'].max()
chng_from_min = usgs_data_24h.iloc[-1]['surface_level'] - usgs_data_24h['surface_level'].min()

if chng_from_max*-1 > chng_from_min:
    surface_level_24h = chng_from_max
else:
    surface_level_24h = chng_from_min

# Current wind speeds
wind_speed = noaa_data.iloc[0]['Wind']

# Current barometric pressure
bar_pressure = noaa_data.iloc[0]['Pressure']

# 24h change in temperature
temp_24h = noaa_data.iloc[0]['Temp'] - noaa_data.iloc[23]['Temp']
temp_24h = round(temp_24h)


# 4. Generate fishing report with data input to LLM

ollama.pull(model='gemma3:4b')

prompt = f"""
Here is live data related to fishing near Morgantown, WV:

Water Level Change (last 48 hours): {surface_level_24h:.2f} feet. Favorable if increasing.
Current Wind Speed: {wind_speed} mph. Favorable if low.
Current Barometric Pressure: {bar_pressure:.2f} inHg. Favorable if below 30.40
Temperature Change (last 24 hours): {temp_24h} degrees F. Favorable if stable or rising.

Based on the data:
1. List each variable and indicate if it is favorable or unfavorable for fishing
2. Write a 3-5 sentence fishing report about the conditions and fishing outlook
"""

response: ChatResponse = chat(model='gemma3:4b', messages=[
  {
    'role': 'user',
    'content': prompt,
  },
])

fishing_report = response['message']['content']
print("\n--- Fishing Report ---")
print(fishing_report)
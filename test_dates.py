import requests
import re
import json

URL = "https://www.ishares.com/us/products/239689/ishares-msci-turkey-etf"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
}

print("Fetching URL...")
res = requests.get(URL, headers=HEADERS, timeout=15)
print("Status Code:", res.status_code)

if res.ok:
    # Try to find dates in the HTML
    # Usually BlackRock embeds component data in JSON format inside the page or has a dropdown.
    # Look for "asOfDate" or something similar in the JS variables or HTML options.
    
    # Method 1: Look for an array of dates like "availableDates": ["20260624", "20260623"]
    # We can use regex to find all dates in YYYYMMDD format that start with 202
    dates = set(re.findall(r'202[456]\d{4}', res.text))
    # Filter only those that look like valid YYYYMMDD strings (e.g. 20260624)
    valid_dates = []
    for d in dates:
        if len(d) == 8:
            try:
                # Valid month/day check
                m = int(d[4:6])
                day = int(d[6:8])
                if 1 <= m <= 12 and 1 <= day <= 31:
                    valid_dates.append(d)
            except:
                pass
                
    valid_dates.sort(reverse=True)
    print("Found potential YYYYMMDD dates:")
    print(valid_dates[:20]) # Print first 20

    # Specifically look for a JSON blob that might contain exactly the dates for holdings
    # Often it's in a JS object window.__INITIAL_STATE__ or similar

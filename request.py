import requests
import time
from bs4 import BeautifulSoup
import json
import re
headers = {
    "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
}
cache={}
def request_with_retry(url,headers=headers,max_retries=3,timeout=15):
    retry_status_codes = { 408, 429, 500, 502, 503, 504 }
    for attempt in range(max_retries+1):
        try: 
            response=requests.get(url,headers=headers,timeout=timeout)
            if response.status_code==200:
                return response
            if response.status_code in retry_status_codes:
                if attempt < max_retries:
                    retry_after = response.headers.get("Retry-After")

                    if retry_after:
                        try:
                            wait_time = float(retry_after)
                        except ValueError:
                            wait_time = 2 ** attempt
                    else:
                        wait_time = 2 ** attempt

                    print(
                        f"HTTP {response.status_code} "
                        f"→ retry {attempt + 1}/{max_retries} "
                        f"sau {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)
                    continue

                print(f"HTTP {response.status_code}: đã retry hết số lần cho phép")
                return None

            print(f"HTTP {response.status_code}: request thất bại")
            return None
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                wait_time = (2 ** attempt)
                print( f"Timeout " f"→ retry {attempt + 1}/{max_retries} " f"sau {wait_time:.1f}s" )
                time.sleep(wait_time) 
                continue
            return None
        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                wait_time = (2 ** attempt)
                print( f"Connection error " f"→ retry {attempt + 1}/{max_retries} " f"sau {wait_time:.1f}s" )
                time.sleep(wait_time) 
                continue
            return None       
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None
    return None
     
def get_url_apparels(productId,productName, headers=headers):
    if productId in cache:
        response=cache[productId]
    else:
        response=request_with_retry(f'https://snkrdunk.com/search?keywords={productId}',headers=headers)
        
    if response is None:
        return None

    cache[productId] = response
    soup=BeautifulSoup(response.text,'html.parser')
    div_items=soup.select('div[class*="scrollContainer"] a[href*="/apparels/"]')
    for div in div_items:
        name_element=div.select_one('span[class*="productName"]')
        name=name_element.get_text(strip=True)
        if(productName==name):
            url=div.get('href')
            return url
    return "not found"

    
def get_data_apparels(url,headers=headers):
    if not url:
        return None

    id=url.split('/')[-1]
    response=request_with_retry(f'https://snkrdunk.com/v1/apparels/{id}/sizes',headers=headers)

    if response is None:
        return None

    data=response.json()
    results={}
    size_prices=data.get('sizePrices',[])
    for item in size_prices:
        size=item.get('size',{}).get('localizedName')
        price=item.get('minListingPrice')
        results[size]=price
    return results
    

def get_data_products(id,headers=headers):
    response=request_with_retry(f'https://snkrdunk.com/products/{id}',headers=headers)

    if response is None:
        return None

    pattern = r'\\"listings\\":(\[.*?\]),\\"sneakerName\\"'
    match = re.search(pattern, response.text)
    if match:
        listings_str = match.group(1).replace('\\"', '"')
        listings = json.loads(listings_str)
        results={}
        for item in listings:
            size=item.get("variant", {}).get("sizeName")
            price=item.get('minNewListingPrice')
            results[size]=price
        return results

    return None
get_data_apparels('https://snkrdunk.com/apparels/887726')
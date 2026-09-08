import requests
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
def get_url_apparels(productId,productName, headers=headers):
    if productId in cache:
        response=cache[productId]
    else:
        response=requests.get(f'https://snkrdunk.com/search?keywords={productId}',headers=headers)
    if(response.status_code==200):
        cache[productId]=response
        soup=BeautifulSoup(response.text,'html.parser')
        div_items=soup.select('div[class*="scrollContainer"] a[href*="/apparels/"]')
        for div in div_items:
            name_element=div.select_one('span[class*="productName"]')
            name=name_element.get_text(strip=True)
            if(productName==name):
                url=div.get('href')
                return url
        return "not found"
    else:
        return(response.status_code)
def get_data_apparels(url,headers=headers):
    id=url.split('/')[-1]
    response=requests.get(f'https://snkrdunk.com/v1/apparels/{id}/sizes',headers=headers)
    results={}
    if(response.status_code==200):
        data=response.json()
        size_prices=data.get('sizePrices',[])
        for item in size_prices:
            size=item.get('size',{}).get('localizedName')
            price=item.get('minListingPrice')
            results[size]=price
        return results
    

def get_data_products(id,headers=headers):
    response=requests.get(f'https://snkrdunk.com/products/{id}',headers=headers)
    results={}
    if(response.status_code==200):
        pattern = r'\\"listings\\":(\[.*?\]),\\"sneakerName\\"'
        match = re.search(pattern, response.text)
        if match:
            listings_str = match.group(1).replace('\\"', '"')
            listings = json.loads(listings_str)
            for item in listings:
                size=item.get("variant", {}).get("sizeName")
                price=item.get('minNewListingPrice')
                results[size]=price
        return results
get_data_apparels('https://snkrdunk.com/apparels/887726')
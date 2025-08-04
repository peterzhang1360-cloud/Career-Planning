import requests
from bs4 import BeautifulSoup

def scrape_links():
  url = 'https://www.auckland.ac.nz/en/study/study-options/find-a-study-option.html'
  response = requests.get(url, timeout=10)
  response.raise_for_status()
  soup = BeautifulSoup(response.text, 'html.parser')
  links = soup.find_all('a', href=True) 
  for link in links:
    href = link['href']
    text = link.get_text(strip=True)
    print(f'{text}: {href}')

    sub_href = href
    sub_href = 'https://www.auckland.ac.nz' + sub_href
    sub_response = requests.get(sub_href, timeout=10)
    sub_response.raise_for_status()
    sub_soup = BeautifulSoup(sub_response.text, 'html.parser')
    sub_links = sub_soup.find_all('a', href=True, class_='listing-item__link')      
    for sub_link in sub_links:
        sub_href = sub_link['href']
        sub_text = sub_link.get_text(strip=True)
        print(f'{sub_text}: {sub_href}')

scrape_links()
import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_class_name(title):
    title = title.lower()
    if 'पहिली' in title or '1st' in title or 'first' in title: return 'class_1'
    if 'दुसरी' in title or '2nd' in title or 'second' in title: return 'class_2'
    if 'तिसरी' in title or '3rd' in title or 'third' in title: return 'class_3'
    if 'चौथी' in title or '4th' in title or 'fourth' in title: return 'class_4'
    if 'पाचवी' in title or '5th' in title or 'fifth' in title: return 'class_5'
    if 'सहावी' in title or '6th' in title or 'sixth' in title: return 'class_6'
    if 'सातवी' in title or '7th' in title or 'seventh' in title: return 'class_7'
    if 'आठवी' in title or '8th' in title or 'eighth' in title: return 'class_8'
    if 'नववी' in title or '9th' in title or 'ninth' in title: return 'class_9'
    if 'दहावी' in title or '10th' in title or 'tenth' in title: return 'class_10'
    if 'अकरावी' in title or '11th' in title or 'eleventh' in title: return 'class_11'
    if 'बारावी' in title or '12th' in title or 'twelfth' in title: return 'class_12'
    
    return 'unknown_class'

def get_subject_name(title):
    title = title.lower()
    if 'गणित' in title or 'math' in title: return 'mathematics'
    if 'विज्ञान' in title or 'science' in title or 'पर्यावरण' in title or 'evs' in title: return 'science'
    if 'इतिहास' in title or 'history' in title: return 'history'
    if 'भूगोल' in title or 'geography' in title: return 'geography'
    if 'नागरिकशास्त्र' in title or 'civics' in title: return 'civics'
    if 'मराठी' in title or 'marathi' in title or 'बालभारती' in title: return 'marathi'
    if 'इंग्रजी' in title or 'english' in title or 'my english' in title: return 'english'
    if 'हिंदी' in title or 'hindi' in title: return 'hindi'
    return 'general'

def download_book(book_id, title, base_dir, download_limit=None):
    class_name = get_class_name(title)
    subject_name = get_subject_name(title)
    
    # Fallback parsing
    if class_name == 'unknown_class' and len(book_id) == 9:
        try:
            cls = int(book_id[1:3])
            class_name = f'class_{cls}'
        except:
            pass

    target_folder = os.path.join(base_dir, class_name, subject_name)
    os.makedirs(target_folder, exist_ok=True)
    
    file_path = os.path.join(target_folder, f"{book_id}.pdf")
    pdf_url = f"https://ebooks.ebalbharati.in/pdfs/{book_id}.pdf"
    
    if os.path.exists(file_path):
        print(f"Skipping {book_id}.pdf - Already downloaded.")
        return True
        
    safe_title = title.encode('ascii', 'ignore').decode('ascii')
    print(f"Downloading {safe_title} ({book_id}.pdf) to {class_name}/{subject_name}...")
    try:
        response = requests.get(pdf_url, stream=True, timeout=30, verify=False)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk: f.write(chunk)
            print("Download successful.")
            return True
        else:
            print(f"Failed to download. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading {pdf_url}: {str(e)}")
    return False

def scrape_balbharati(base_dir, max_downloads=None):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--log-level=3')
    
    print("Installing/Finding ChromeDriver...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    print("Opening books.ebalbharati.in...")
    driver.get("https://books.ebalbharati.in/")
    time.sleep(5)  
    
    downloaded_count = 0
    seen_ids = set()
    
    try:
        for class_num in range(1, 13):
            if max_downloads and downloaded_count >= max_downloads:
                break
                
            class_id = 200 + class_num
            try:
                lbl = driver.find_element(By.CSS_SELECTOR, f"label[for='chk_{class_id}']")
                driver.execute_script("arguments[0].scrollIntoView();", lbl)
                lbl.click()
                print(f"\n--- Selected Class {class_num} ---")
                time.sleep(4) 
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                book_divs = soup.find_all('div', class_='bookDetails1')
                print(f"Found {len(book_divs)} books for this selection.")
                
                for div in book_divs:
                    if max_downloads and downloaded_count >= max_downloads:
                        break
                        
                    title_div = div.find('div', class_='divbooknm')
                    img = div.find('img')
                    
                    if not title_div or not img:
                        continue
                        
                    title = title_div.get('title', '').strip()
                    img_src = img.get('src', '')
                    book_id = img_src.split('/')[-1].replace('.jpg', '')
                    
                    if book_id in seen_ids or not book_id.isdigit():
                        continue
                        
                    seen_ids.add(book_id)
                    success = download_book(book_id, title, base_dir)
                    if success:
                        downloaded_count += 1
                        
                lbl.click()
                time.sleep(2)
                
            except Exception as e:
                print(f"Error navigating class {class_num}: {e}")
                
    finally:
        driver.quit()
        print(f"\nFinished scraping. Total downloaded: {downloaded_count}")

if __name__ == "__main__":
    knowledge_dir = r"C:\Users\vijay\Downloads\uniguru_ai-main\uniguru_ai-main\backend\knowledge\balbharti"
    os.makedirs(knowledge_dir, exist_ok=True)
    
    # We pass max_downloads=5 to test functionality quickly. 
    # To download everything, remove this parameter or set it to None.
    scrape_balbharati(knowledge_dir, max_downloads=5)

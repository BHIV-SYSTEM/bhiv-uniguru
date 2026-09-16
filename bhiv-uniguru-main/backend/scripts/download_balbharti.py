import os
import requests
import re
from bs4 import BeautifulSoup

def download_balbharati_sample():
    base_url = "https://books.ebalbharati.in/"
    target_dir = r"C:\Users\vijay\Downloads\uniguru_ai-main\uniguru_ai-main\backend\knowledge\balbharti"
    
    # We will download a small sample of known PDFs to avoid taking hours and filling the disk.
    # A full scraper would require POST requests with ASP.NET __VIEWSTATE parameters to navigate the pagination/filters.
    sample_books = [
        {"class": "class_1", "subject": "mathematics", "id": "101050001"},
        {"class": "class_1", "subject": "english", "id": "103050001"},
        {"class": "class_5", "subject": "marathi", "id": "501000541"},
        {"class": "class_5", "subject": "history", "id": "501000542"}
    ]
    
    print(f"Target Directory: {target_dir}")
    
    for book in sample_books:
        folder_path = os.path.join(target_dir, book["class"], book["subject"])
        os.makedirs(folder_path, exist_ok=True)
        
        pdf_url = f"https://ebooks.ebalbharati.in/pdfs/{book['id']}.pdf"
        file_path = os.path.join(folder_path, f"{book['id']}.pdf")
        
        if os.path.exists(file_path):
            print(f"Already exists: {file_path}")
            continue
            
        print(f"Downloading {pdf_url} to {file_path}...")
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(pdf_url, stream=True, timeout=30, verify=False)
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
                print(f"Successfully downloaded {book['id']}.pdf")
            else:
                print(f"Failed to download. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error downloading {pdf_url}: {str(e)}")

if __name__ == "__main__":
    download_balbharati_sample()

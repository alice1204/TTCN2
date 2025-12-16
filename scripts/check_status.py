import requests

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
TARGET_PAGE = "/commodities"
BASE_URL = "https://tradingeconomics.com"

headers = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.google.com/'
}

try:
    session = requests.Session()
    print("Đang kết nối thử...")
    response = session.get(f"{BASE_URL}{TARGET_PAGE}", headers=headers)
    
    print(f"Status Code: {response.status_code}") # Nếu là 403 hoặc 503 là bị chặn
    print("-" * 20)
    print("Tiêu đề trang web nhận được:")
    # In ra 500 ký tự đầu tiên để xem nó là trang gì
    print(response.text[:500]) 
    
except Exception as e:
    print(f"Lỗi: {e}")
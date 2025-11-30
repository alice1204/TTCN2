import requests
import re

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
TARGET_PAGE = "/commodities"
BASE_URL = "https://tradingeconomics.com"

headers = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Referer': 'https://www.google.com/'
}

try:
    session = requests.Session()
    print(">> Đang tải HTML...")
    response = session.get(f"{BASE_URL}{TARGET_PAGE}", headers=headers)
    html = response.text
    
    # 1. Kiểm tra xem từ khóa có tồn tại không
    if "TEdecryptk" in html:
        print("✅ TÌM THẤY 'TEdecryptk' trong HTML!")
        
        # 2. In ra 100 ký tự xung quanh nó để xem cấu trúc
        start_index = html.find("TEdecryptk")
        # Lấy đoạn text từ trước đó 20 ký tự đến sau đó 100 ký tự
        snippet = html[start_index-20 : start_index+100]
        
        print("-" * 30)
        print("CẤU TRÚC TÌM THẤY:")
        print(f"...{snippet}...")
        print("-" * 30)
        
        # 3. Test thử Regex hiện tại xem khớp không
        curr_regex = r"TEdecryptk\s*=\s*['\"]([^'\"]+)['\"]"
        match = re.search(curr_regex, html)
        if match:
            print(f"✅ Regex hiện tại hoạt động tốt: {match.group(1)[:10]}...")
        else:
            print("❌ Regex hiện tại KHÔNG bắt được (Do thừa thiếu khoảng trắng hoặc dấu câu).")
            
    else:
        print("❌ KHÔNG tìm thấy 'TEdecryptk' trong HTML.")
        print("👉 Có thể trang web đã chuyển sang render bằng JS hoặc Server trả về bản Mobile/Static.")
        
        # Lưu ra file để bạn mở bằng Notepad kiểm tra kỹ hơn
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("👉 Đã lưu file 'debug_page.html'. Hãy mở nó và Ctrl+F tìm 'TEdecryptk'.")

except Exception as e:
    print(f"Lỗi: {e}")
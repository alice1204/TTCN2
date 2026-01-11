import socketio
import base64
import zlib
import json
import nacl.secret
import nacl.utils
import requests
import re
import csv
import os
from datetime import datetime

# ==========================================
# CẤU HÌNH USER
# ==========================================
# File lưu trữ
FILE_PRICE = "data/raw/data_price_realtime.csv"
FILE_CHANGE = "data/raw/data_change_realtime.csv"

# Danh sách 5 yếu tố
SYMBOL_MAP = {
    "XAUUSD:CUR": "Gold",
    "XAGUSD:CUR": "Silver",
    "CO1:COM":    "Brent",
    "W 1:COM":    "Wheat",
    "USDCHF:CUR": "USD index"
}

# Thứ tự cột trong file CSV
COLUMNS_ORDER = ["Datetime", "Gold", "Silver", "Brent", "Wheat", "USD index"]

# BỘ NHỚ ĐỆM (CACHE) - Lưu trữ trạng thái mới nhất của thị trường
# Khởi tạo giá trị ban đầu là rỗng ""
latest_prices = {name: "" for name in SYMBOL_MAP.values()}
latest_changes = {name: "" for name in SYMBOL_MAP.values()}

# Cấu hình Web
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
TARGET_PAGE = "/commodities"
BASE_URL = "https://tradingeconomics.com"

secret_box = None
NONCE = None

# ==========================================
# 1. XỬ LÝ FILE CSV & LOGIC FILL-FORWARD
# ==========================================
def init_csv_files():
    """Tạo file và viết header nếu chưa có"""
    for filename in [FILE_PRICE, FILE_CHANGE]:
        if not os.path.exists(filename):
            try:
                with open(filename, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=COLUMNS_ORDER)
                    writer.writeheader()
                print(f"✅ Đã tạo file mới: {filename}")
            except Exception as e:
                print(f"❌ Lỗi tạo file {filename}: {e}")

def update_and_save(symbol, price, change_percent):
    global latest_prices, latest_changes
    
    # 1. Xác định tên cột (Ví dụ: Gold)
    col_name = SYMBOL_MAP.get(symbol)
    if not col_name: return

    # 2. Cập nhật vào Bộ nhớ đệm (Cache)
    latest_prices[col_name] = price
    latest_changes[col_name] = change_percent
    
    # 3. Lấy thời gian hiện tại
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 4. Chuẩn bị dòng dữ liệu để ghi (Lấy toàn bộ từ Cache ra)
    # Lưu ý: Các mã KHÔNG nhảy giá sẽ lấy lại giá trị cũ trong Cache
    row_price = {"Datetime": now_str}
    row_price.update(latest_prices)
    
    row_change = {"Datetime": now_str}
    row_change.update(latest_changes)

    # 5. Ghi ngay lập tức vào file
    try:
        # Ghi file Giá
        with open(FILE_PRICE, mode='a', newline='', encoding='utf-8') as f_p:
            writer = csv.DictWriter(f_p, fieldnames=COLUMNS_ORDER)
            writer.writerow(row_price)
            
        # Ghi file % Thay đổi
        with open(FILE_CHANGE, mode='a', newline='', encoding='utf-8') as f_c:
            writer = csv.DictWriter(f_c, fieldnames=COLUMNS_ORDER)
            writer.writerow(row_change)
            
        # In log ra màn hình
        # Màu xanh nếu tăng, đỏ nếu giảm
        color = "\033[92m" if change_percent >= 0 else "\033[91m"
        reset = "\033[0m"
        print(f"{now_str} | Cập nhật: {col_name:<10} | {color}{price:>10} ({change_percent}%){reset} | (Các mã khác giữ nguyên)")
        
    except Exception as e:
        print(f"❌ Lỗi ghi file: {e}")

# ==========================================
# 2. AUTH & CRYPTO
# ==========================================
def get_auth_data():
    print("[1/4] 🕵️  Đang lấy Auth Token...")
    
    # DANH SÁCH URL CẦN THỬ
    # Ưu tiên trang chi tiết (như Gold) vì thường chứa mã Auth cho biểu đồ
    target_urls = [
        'https://tradingeconomics.com/commodity/gold',
        'https://tradingeconomics.com/commodity/brent-crude-oil',
        'https://tradingeconomics.com/'  # Trang chủ
    ]

    session = requests.Session()
    
    # Header giả lập kỹ càng hơn
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://tradingeconomics.com/',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

    found_data = {}

    for url in target_urls:
        print(f"   Trying URL: {url} ...")
        try:
            response = session.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"   ⚠️ Lỗi HTTP {response.status_code} tại {url}")
                continue
                
            html = response.text
            
            # Regex tìm kiếm (Hỗ trợ nhiều biến thể khoảng trắng)
            patterns = {
                'key':   r"AUTH_KEY\s*=\s*['\"]([^'\"]+)['\"]",
                'nonce': r"AUTH_NONCE\s*=\s*['\"]([^'\"]+)['\"]",
                'token': r"AUTH_TOKEN\s*=\s*['\"]([^'\"]+)['\"]"
            }

            # Quét tìm 3 chìa khóa
            missing_key = False
            for name, pat in patterns.items():
                match = re.search(pat, html)
                if match:
                    found_data[name] = match.group(1)
                else:
                    missing_key = True
            
            # Nếu tìm đủ 3 chìa khóa thì dừng ngay, không cần thử URL khác
            if not missing_key and len(found_data) == 3:
                print(f"✅ Đã tìm thấy Key tại: {url}")
                print(f"   Auth Key: {found_data['key'][:10]}...")
                return found_data['token'], found_data['key'], found_data['nonce'], session.cookies.get_dict()
        
        except Exception as e:
            print(f"   ⚠️ Lỗi kết nối tới {url}: {e}")
            continue

    # Nếu chạy hết danh sách mà vẫn không tìm thấy
    print("❌ THẤT BẠI: Không tìm thấy Auth Token ở bất kỳ trang nào.")
    print("   👉 Khả năng cao trang web đã đổi hoàn toàn sang cơ chế Auth mới (TEChartsToken).")
    
    # Lưu trang cuối cùng để debug nếu cần
    if 'html' in locals():
        with open("debug_fail_page.html", "w", encoding="utf-8") as f:
            f.write(html)
            
    return None, None, None, None

def setup_crypto(key_b64, nonce_b64):
    global secret_box, NONCE
    try:
        secret_box = nacl.secret.SecretBox(base64.b64decode(key_b64))
        NONCE = base64.b64decode(nonce_b64)
        print(f"[2/4] 🔐 Đã nạp Key giải mã.")
        return True
    except: return False

def smart_decompress(data_bytes):
    try: return zlib.decompress(data_bytes).decode('utf-8')
    except: pass
    try: return zlib.decompress(data_bytes, wbits=-15).decode('utf-8')
    except: pass
    try: return zlib.decompress(data_bytes, wbits=16 + zlib.MAX_WBITS).decode('utf-8')
    except: pass
    return None

def decrypt_payload(data):
    if not secret_box: return None
    try:
        ciphertext = bytes(data) if isinstance(data, list) else data
        decrypted = secret_box.decrypt(ciphertext, NONCE)
        json_str = smart_decompress(decrypted)
        return json.loads(json_str) if json_str else None
    except: return None

# ==========================================
# 3. KẾT NỐI SOCKET
# ==========================================
sio = socketio.Client(logger=False, engineio_logger=False)

@sio.event
def connect():
    print("[3/4] 🚀 Socket đã kết nối!")
    # Đăng ký các mã
    sio.emit('subscribe', {'s': list(SYMBOL_MAP.keys())})
    sio.emit('subscribe', {'s': ['commodities', 'market']})
    
    print(f"[4/4] ⚡ Chế độ FILL-FORWARD đang chạy...")
    print(f"      File: {FILE_PRICE} & {FILE_CHANGE}")
    print("-" * 65)

@sio.on('*')
def catch_all(event, data):
    if event not in ['tick', 'market', 'commodities']: return

    result = decrypt_payload(data)
    if result:
        items = result if isinstance(result, list) else [result]
        
        for item in items:
            symbol = item.get('s')
            price = item.get('p')
            change = item.get('pch')
            
            # Chỉ xử lý khi đúng mã và có dữ liệu giá
            if symbol in SYMBOL_MAP and price is not None and change is not None:
                update_and_save(symbol, price, change)

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    init_csv_files()
    token, key, nonce, cookies = get_auth_data()
    
    if token and setup_crypto(key, nonce):
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        try:
            sio.connect(
                f'https://live.tradingeconomics.com?key=rain&url={TARGET_PAGE}',
                auth={'token': token, 'url': TARGET_PAGE},
                headers={'User-Agent': USER_AGENT, 'Cookie': cookie_str, 'Origin': BASE_URL},
                transports=['websocket']
            )
            sio.wait()
        except KeyboardInterrupt:
            print(f"\n👋 Bye!")
        except Exception as e:
            print(f"\n❌ Lỗi: {e}")
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
FILE_PRICE = "data/data_price_realtime.csv"
FILE_CHANGE = "data/data_change_realtime.csv"

# Danh sách 6 yếu tố bạn yêu cầu (Đã thêm Milk)
SYMBOL_MAP = {
    "XAUUSD:CUR": "Gold",
    "XAGUSD:CUR": "Silver",
    "CO1:COM":    "Brent",
    "W 1:COM":    "Wheat",
    "DA:COM":    "Milk",        # Class III Milk Futures
    "USDCHF:CUR": "USD index"    # USD/CHF thường được dùng đại diện hoặc dùng DXY:CUR
}

# Thứ tự cột trong file CSV
COLUMNS_ORDER = ["Datetime", "Gold", "Silver", "Brent", "Wheat", "Milk", "USD index"]

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
# 2. AUTH & CRYPTO (Phần này giữ nguyên)
# ==========================================
def get_auth_data():
    headers = {'User-Agent': USER_AGENT}
    try:
        session = requests.Session()
        print(f"\n[1/4] 🕵️  Đang lấy Auth Token...")
        response = session.get(f"{BASE_URL}{TARGET_PAGE}", headers=headers)
        
        token = re.search(r"token\s*:\s*['\"](eyJ[^'\"]+)['\"]", response.text).group(1)
        key_b64 = re.search(r"TEdecryptk\s*=\s*['\"]([^'\"]+)['\"]", response.text).group(1)
        nonce_b64 = re.search(r"TEdecryptn\s*=\s*['\"]([^'\"]+)['\"]", response.text).group(1)
        
        return token, key_b64, nonce_b64, session.cookies.get_dict()
    except Exception as e:
        print(f"❌ Lỗi Auth: {e}")
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
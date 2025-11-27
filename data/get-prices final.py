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
# CẤU HÌNH (Đã bỏ Live Cattle)
# ==========================================
FILE_PRICE = "data/data_price.csv"
FILE_CHANGE = "data/data_change.csv"

# Mapping Symbol
SYMBOL_MAP = {
    "XAUUSD:CUR": "Gold",
    "XAGUSD:CUR": "Silver",
    "CO1:COM":    "Brent",
    "W 1:COM":   "Wheat",
    "DA:COM":    "Milk",
    "USDCHF:CUR": "USD index"
}

# Các yếu tố bắt buộc
REQUIRED_COLUMNS = ["Gold", "Silver", "Brent", "Wheat", "Milk", "USD index"]
CSV_HEADERS = ["Datetime"] + REQUIRED_COLUMNS

# BỘ ĐỆM (BUFFER)
# Cấu trúc: {'Gold': {'p': 2000, 'pch': 0.5}, ...}
batch_buffer = {} 

# Cấu hình Web
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
TARGET_PAGE = "/commodities"
BASE_URL = "https://tradingeconomics.com"

secret_box = None
NONCE = None

# ==========================================
# 1. XỬ LÝ 2 FILE CSV SONG SONG
# ==========================================
def init_csv_files():
    """Khởi tạo cả 2 file nếu chưa tồn tại"""
    for filename in [FILE_PRICE, FILE_CHANGE]:
        if not os.path.exists(filename):
            try:
                with open(filename, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
                    writer.writeheader()
                print(f"✅ Đã tạo file: {filename}")
            except Exception as e:
                print(f"❌ Lỗi tạo file {filename}: {e}")

def process_batch(symbol, price, change_percent):
    global batch_buffer
    
    col_name = SYMBOL_MAP.get(symbol)
    if not col_name: return

    # Lưu cả 2 giá trị vào bộ đệm
    batch_buffer[col_name] = {
        'p': price,
        'pch': change_percent
    }
    
    print(f"   -> Đã nhận: {col_name:<12} (Price: {price} | Chg: {change_percent}%) | Tiến độ: {len(batch_buffer)}/6")

    # KIỂM TRA ĐỦ 6 MÓN CHƯA?
    current_keys = set(batch_buffer.keys())
    required_set = set(REQUIRED_COLUMNS)

    if required_set.issubset(current_keys):
        save_dual_csv()

def save_dual_csv():
    global batch_buffer
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Chuẩn bị 2 dòng dữ liệu riêng biệt
    row_price = {"Datetime": now_str}
    row_change = {"Datetime": now_str}
    
    for name in REQUIRED_COLUMNS:
        data = batch_buffer[name]
        row_price[name] = data['p']
        row_change[name] = data['pch']

    try:
        # 1. Ghi file GIÁ
        with open(FILE_PRICE, mode='a', newline='', encoding='utf-8') as f_p:
            writer = csv.DictWriter(f_p, fieldnames=CSV_HEADERS)
            writer.writerow(row_price)
            
        # 2. Ghi file % THAY ĐỔI
        with open(FILE_CHANGE, mode='a', newline='', encoding='utf-8') as f_c:
            writer = csv.DictWriter(f_c, fieldnames=CSV_HEADERS)
            writer.writerow(row_change)
        
        print(f"\n✅ [ĐỒNG BỘ] {now_str} | Đủ các yếu tố -> Đã ghi vào cả 2 file!")
        print("-" * 65)
        
        # Reset bộ đệm
        batch_buffer.clear()
        
    except Exception as e:
        print(f"❌ Lỗi ghi file: {e}")

# ==========================================
# 2. AUTH & CRYPTO (Giữ nguyên)
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
    sio.emit('subscribe', {'s': list(SYMBOL_MAP.keys())})
    sio.emit('subscribe', {'s': ['commodities', 'market']})
    
    print(f"[4/4] ⏳ Đang chờ GOM ĐỦ 5 mã: {', '.join(REQUIRED_COLUMNS)}")
    print(f"      Output: {FILE_PRICE} & {FILE_CHANGE}")
    print("-" * 65)

@sio.on('*')
def catch_all(event, data):
    if event not in ['tick', 'market', 'commodities']: return

    result = decrypt_payload(data)
    if result:
        items = result if isinstance(result, list) else [result]
        
        for item in items:
            symbol = item.get('s')
            price = item.get('p')      # Lấy giá
            change = item.get('pch')   # Lấy % thay đổi
            
            # Điều kiện: Đúng Symbol + Có giá + Có % thay đổi
            if symbol in SYMBOL_MAP and price is not None and change is not None:
                process_batch(symbol, price, change)

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    init_csv_files() # Khởi tạo 2 file
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
            print(f"\n👋 Đã dừng! Dữ liệu nằm trong {FILE_PRICE} và {FILE_CHANGE}")
        except Exception as e:
            print(f"\n❌ Lỗi: {e}")
import socketio
import base64
import zlib
import json
import nacl.secret
import nacl.utils
import requests
import re
from datetime import datetime

# --- CẤU HÌNH HỆ THỐNG ---
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
TARGET_PAGE = "/commodities"
BASE_URL = "https://tradingeconomics.com"

# Biến toàn cục lưu khóa giải mã
secret_box = None
NONCE = None

# ==========================================
# PHẦN 1: TỰ ĐỘNG LẤY CHÌA KHÓA (AUTO AUTH)
# ==========================================
def get_auth_data():
    headers = {'User-Agent': USER_AGENT}
    try:
        session = requests.Session()
        print(f"\n[1/4] 🕵️  Đang xâm nhập vào {TARGET_PAGE} để lấy chìa khóa...")
        response = session.get(f"{BASE_URL}{TARGET_PAGE}", headers=headers)
        html = response.text
        
        # Sử dụng Regex để "đào" dữ liệu từ Source Code HTML
        token_match = re.search(r"token\s*:\s*['\"](eyJ[^'\"]+)['\"]", html)
        key_match = re.search(r"TEdecryptk\s*=\s*['\"]([^'\"]+)['\"]", html)
        nonce_match = re.search(r"TEdecryptn\s*=\s*['\"]([^'\"]+)['\"]", html)

        if not (token_match and key_match and nonce_match):
            print("❌ Không tìm thấy Token/Key. Có thể trang web đã đổi cấu trúc.")
            return None, None, None, None
        
        token = token_match.group(1)
        key_b64 = key_match.group(1)
        nonce_b64 = nonce_match.group(1)
        
        print("✅ Đã lấy được Token & Key mới nhất.")
        return token, key_b64, nonce_b64, session.cookies.get_dict()
    except Exception as e:
        print(f"❌ Lỗi kết nối lấy Auth: {e}")
        return None, None, None, None

def setup_crypto(key_b64, nonce_b64):
    global secret_box, NONCE
    try:
        key = base64.b64decode(key_b64)
        NONCE = base64.b64decode(nonce_b64)
        secret_box = nacl.secret.SecretBox(key)
        print(f"[2/4] 🔐 Đã nạp thuật toán giải mã (Sodium/NaCl).")
        return True
    except Exception as e:
        print(f"❌ Lỗi setup crypto: {e}")
        return False

# ==========================================
# PHẦN 2: GIẢI MÃ & BUNG NÉN (CORE LOGIC)
# ==========================================
def smart_decompress(data_bytes):
    """Thử mọi phương pháp giải nén để tránh lỗi 'invalid stored block lengths'"""
    # Cách 1: Chuẩn Zlib (Có Header) - Khả năng cao nhất
    try: return zlib.decompress(data_bytes).decode('utf-8')
    except: pass

    # Cách 2: Raw Deflate (Không Header - wbits=-15) - Code cũ dùng cái này
    try: return zlib.decompress(data_bytes, wbits=-15).decode('utf-8')
    except: pass

    # Cách 3: Gzip (wbits=31)
    try: return zlib.decompress(data_bytes, wbits=16 + zlib.MAX_WBITS).decode('utf-8')
    except: pass

    return None

def decrypt_payload(data):
    if not secret_box: return None
    try:
        # Chuẩn hóa input: Chuyển List Int thành Bytes nếu cần
        ciphertext = bytes(data) if isinstance(data, list) else data
        
        # 1. Giải mã bằng Key + Nonce
        decrypted_bytes = secret_box.decrypt(ciphertext, NONCE)
        
        # 2. Bung nén thông minh
        json_str = smart_decompress(decrypted_bytes)
        
        if json_str:
            return json.loads(json_str)
        return None
    except Exception:
        # Bỏ qua các gói tin rác hoặc không giải mã được
        return None

# ==========================================
# PHẦN 3: KẾT NỐI WEBSOCKET
# ==========================================
sio = socketio.Client(logger=False, engineio_logger=False)

@sio.event
def connect():
    print("[3/4] 🚀 ĐÃ KẾT NỐI SOCKET! Đang đăng ký kênh...")
    # Đăng ký nhận dữ liệu
    # 'commodities': Kênh hàng hóa tổng hợp
    # 'market': Kênh thị trường chung
    # Các mã cụ thể: XAUUSD (Vàng), CL1 (Dầu), BTCUSD (Bitcoin)
    sio.emit('subscribe', {'s': ['commodities', 'market']})
    sio.emit('subscribe', {'s': ['XAUUSD:CUR', 'CL1:COM', 'BTCUSD:CUR', 'XAGUSD:CUR']})
    print("[4/4] 📡 Đang chờ dữ liệu Realtime... (Ctrl+C để dừng)\n")
    print(f"{'THỜI GIAN':<10} | {'MÃ (SYMBOL)':<15} | {'GIÁ (PRICE)':<12} | {'THAY ĐỔI':<10}")
    print("-" * 55)

@sio.on('*') # Bắt tất cả sự kiện
def catch_all(event, data):
    # Chỉ xử lý các sự kiện chứa dữ liệu giá
    if event not in ['tick', 'market', 'commodities']: return

    result = decrypt_payload(data)
    
    if result:
        # Server có thể trả về 1 object hoặc 1 list các object
        if isinstance(result, list):
            for item in result: process_item(item)
        else:
            process_item(result)

def process_item(item):
    symbol = item.get('s')
    price = item.get('p')
    change = item.get('pch', 0) # Phần trăm thay đổi
    
    if symbol and price:
        # Tô màu: Xanh lá nếu tăng, Đỏ nếu giảm
        color = "\033[92m" if change >= 0 else "\033[91m" # Green/Red
        reset = "\033[0m"
        
        now = datetime.now().strftime("%H:%M:%S")
        
        # In ra màn hình console đẹp
        print(f"{now:<10} | {symbol:<15} | {color}{price:>10.4f}{reset} | {color}{change:>7}%{reset}")

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    # Bước 1: Lấy thông tin xác thực
    token, key, nonce, cookies = get_auth_data()
    
    if token and setup_crypto(key, nonce):
        # Tạo chuỗi Cookie chuẩn
        cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        
        try:
            # Bước 2: Kết nối Socket với đầy đủ Headers giả lập
            sio.connect(
                f'https://live.tradingeconomics.com?key=rain&url={TARGET_PAGE}',
                auth={'token': token, 'url': TARGET_PAGE},
                headers={
                    'User-Agent': USER_AGENT,
                    'Cookie': cookie_string,
                    'Origin': BASE_URL,
                    'Referer': f"{BASE_URL}/"
                },
                transports=['websocket'] # Ép dùng WebSocket cho nhanh
            )
            sio.wait()
        except KeyboardInterrupt:
            print("\n👋 Đã dừng chương trình.")
        except Exception as e:
            print(f"\n❌ Lỗi Runtime: {e}")
    else:
        print("\n❌ Không thể khởi chạy do thiếu Token/Key.")
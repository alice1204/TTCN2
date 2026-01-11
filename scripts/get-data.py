import yfinance as yf
import pandas as pd
import time
import os
from datetime import datetime
import schedule

# ==========================================
# CẤU HÌNH
# ==========================================
SYMBOL_MAP = {
    "GC=F": "Gold",       
    "SI=F": "Silver",     
    "BZ=F": "Brent",    
    "ZW=F": "Wheat",     
    "DX-Y.NYB": "USD index" 
}

FILE_PRICE = "data/raw/data_price_yfinance.csv"
COLUMNS_ORDER = ["Datetime", "Gold", "Silver", "Brent", "Wheat", "USD index"]

def init_csv_files():
    """Tạo file CSV và ghi header nếu file chưa tồn tại"""
    if not os.path.exists(FILE_PRICE):
        os.makedirs(os.path.dirname(FILE_PRICE), exist_ok=True)
        # Tạo DataFrame rỗng chỉ có header
        df = pd.DataFrame(columns=COLUMNS_ORDER)
        df.to_csv(FILE_PRICE, index=False)
        print(f"📁 Đã khởi tạo file mới: {FILE_PRICE}")

def fetch_data():
    """Hàm lấy dữ liệu từ Yahoo Finance (Tối ưu tốc độ)"""
    now_str = datetime.now().strftime('%H:%M:%S')
    print(f"\n⏰ {now_str} - Đang lấy dữ liệu...", end="") # end="" để không xuống dòng
    
    current_prices = {}
    try:
        # Tải object Tickers
        tickers = yf.Tickers(" ".join(SYMBOL_MAP.keys()))
        
        for yf_symbol, my_name in SYMBOL_MAP.items():
            ticker = tickers.tickers[yf_symbol]
            
            # --- TỐI ƯU HÓA: Dùng fast_info thay vì info ---
            # fast_info lấy dữ liệu nhanh hơn và ít bị lỗi rate-limit hơn
            try:
                # Ưu tiên lấy last_price (giá khớp lệnh gần nhất)
                price = ticker.fast_info.last_price
            except:
                # Nếu lỗi thì quay về cách cũ (chậm hơn chút nhưng an toàn)
                price = ticker.info.get('regularMarketPrice') or ticker.info.get('currentPrice') or ticker.info.get('ask')
            if my_name == "Wheat" and price:
                price = price / 100  # Chuyển từ Cents (600) -> USD (6.0) cho dễ nhìn
            if price:
                current_prices[my_name] = round(price, 4)
            else:
                current_prices[my_name] = None
                print(f"\n⚠️ Mất tín hiệu: {my_name}")

        # Chỉ lưu nếu lấy được giá Vàng (quan trọng nhất)
        if current_prices.get('Gold'):
            save_to_csv(current_prices)
        else:
            print("\n❌ Dữ liệu Vàng bị thiếu, bỏ qua.")

    except Exception as e:
        print(f"\n❌ Lỗi kết nối: {e}")

def save_to_csv(prices):
    """Lưu vào file CSV"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    row_price = {'Datetime': now_str}
    for col in COLUMNS_ORDER[1:]:
        row_price[col] = prices.get(col, "")
    
    # Ghi file (mode='a' là append - ghi nối tiếp)
    df_p = pd.DataFrame([row_price])
    # header=False vì file đã được tạo header từ hàm init_csv_files
    df_p.to_csv(FILE_PRICE, mode='a', header=False, index=False)
    
    # In kết quả trên 1 dòng cho gọn
    print(f"✅ Đã lưu: Gold={prices.get('Gold')} | Silver={prices.get('Silver')} | Brent={prices.get('Brent')} | Wheat={prices.get('Wheat')} | USD index={prices.get('USD index')}")

# ==========================================
# MAIN LOOP
# ==========================================
if __name__ == "__main__":
    init_csv_files() # <--- Đã có hàm này để code không lỗi
    
    fetch_data() # Chạy lần đầu ngay lập tức
    
    schedule.every(60).seconds.do(fetch_data)
    
    print("🚀 Hệ thống đang chạy... (Ctrl+C để dừng)")
    while True:
        schedule.run_pending()
        time.sleep(1)
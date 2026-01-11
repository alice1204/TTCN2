import yfinance as yf
import pandas as pd
import os

# ==========================================
# 1. CẤU HÌNH
# ==========================================
START_DATE = "2024-10-01"
END_DATE   = "2026-10-01" # Code sẽ tự dừng ở ngày hôm nay nếu chưa đến 2026
INTERVAL   = "1h"         # Khung thời gian 1 giờ

# Mapping tên cho dễ đọc
SYMBOL_MAP = {
    "GC=F": "Gold",       
    "SI=F": "Silver",     
    "BZ=F": "Brent",      
    "ZW=F": "Wheat",      
    "DX-Y.NYB": "USD index"
}

OUTPUT_FILE = "data/raw/data_history_2y_H1.csv"

def download_history():
    print(f"⏳ Đang tải dữ liệu từ {START_DATE} đến {END_DATE} (Khung H1)...")
    
    # Tạo thư mục nếu chưa có
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    try:
        # Tải toàn bộ dữ liệu cùng lúc
        tickers_list = list(SYMBOL_MAP.keys())
        raw_data = yf.download(tickers_list, start=START_DATE, end=END_DATE, interval=INTERVAL)

        # yfinance trả về MultiIndex (VD: ('Close', 'GC=F')), cần làm phẳng
        # Chúng ta chỉ quan tâm đến cột 'Close' (Giá đóng cửa)
        df_close = raw_data['Close'].copy()
        
        # Đổi tên cột từ mã (GC=F) sang tên dễ đọc (Gold)
        df_close.rename(columns=SYMBOL_MAP, inplace=True)
        
        # Sắp xếp lại thứ tự cột cho đẹp
        desired_order = ["Gold", "Silver", "Brent", "Wheat", "USD index"]
        # Chỉ lấy các cột tồn tại trong data tải về (phòng trường hợp lỗi 1 mã)
        cols = [c for c in desired_order if c in df_close.columns]
        df_final = df_close[cols]

        # ==========================================
        # 2. XỬ LÝ SƠ BỘ (LÀM SẠCH NHẸ)
        # ==========================================
        
        # A. Xử lý Lúa mì (Wheat): Chia 100 để đổi từ Cents -> USD
        if "Wheat" in df_final.columns:
            print("   🛠️  Đang chuyển đổi đơn vị Lúa mì (Cents -> USD)...")
            df_final["Wheat"] = df_final["Wheat"] / 100

        # B. Xử lý thiếu dữ liệu (Forward Fill)
        # Vì tải 1h nên ban đêm hay bị ngắt quãng, ta lấp đầy bằng giá giờ trước đó
        print("   🧹 Đang lấp đầy dữ liệu trống (Forward Fill)...")
        df_final.ffill(inplace=True)
        
        # Xóa các dòng đầu tiên nếu vẫn còn NaN (do chưa có dữ liệu quá khứ để fill)
        df_final.dropna(inplace=True)

        # C. Reset Index để đưa cột Date/Time ra ngoài làm cột chính
        df_final.reset_index(inplace=True)
        
        # Đổi tên cột thời gian cho thống nhất với file realtime
        # yfinance thường đặt tên là 'Datetime' hoặc 'Date', ta đổi hết về 'Datetime'
        df_final.rename(columns={'Date': 'Datetime', 'index': 'Datetime'}, inplace=True)

        # ==========================================
        # 3. LƯU FILE
        # ==========================================
        df_final.to_csv(OUTPUT_FILE, index=False)
        
        print(f"\n✅ THÀNH CÔNG! Đã lưu file tại: {OUTPUT_FILE}")
        print(f"   - Tổng số dòng: {len(df_final)}")
        print(f"   - Thời gian bắt đầu: {df_final['Datetime'].min()}")
        print(f"   - Thời gian kết thúc: {df_final['Datetime'].max()}")
        print("\n👇 5 dòng dữ liệu đầu tiên:")
        print(df_final.head())

    except Exception as e:
        print(f"❌ Lỗi tải dữ liệu: {e}")

if __name__ == "__main__":
    download_history()
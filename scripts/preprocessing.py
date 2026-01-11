import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator, EMAIndicator
from sklearn.preprocessing import MinMaxScaler
import joblib
import os

# ==========================================
# CẤU HÌNH
# ==========================================
INPUT_FILE = "data/raw/data_history_2y_H1.csv"
OUTPUT_FILE = "data/processed/train_data_ready.csv"
SCALER_FILE = "model/scaler.pkl"

def process_data():
    print("🚀 Đang bắt đầu chế biến dữ liệu cho AI (Dùng thư viện 'ta')...")
    
    # 1. Đọc dữ liệu thô
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Lỗi: Không tìm thấy file {INPUT_FILE}. Hãy chạy file tải lịch sử trước!")
        return
        
    df = pd.read_csv(INPUT_FILE)
    df['Datetime'] = pd.to_datetime(df['Datetime'])
    df.set_index('Datetime', inplace=True)
    
    print(f"   - Dữ liệu gốc: {df.shape}")

    # ==========================================
    # 2. FEATURE ENGINEERING (Tạo đặc trưng)
    # ==========================================
    print("   🛠️  Đang tính toán các chỉ báo kỹ thuật (RSI, MACD, MA)...")
    
    target_col = 'Gold'
    
    # 2.1. RSI (14)
    # fillna=True để tự động lấp các giá trị NaN đầu tiên
    rsi = RSIIndicator(close=df[target_col], window=14, fillna=True)
    df['RSI'] = rsi.rsi()
    
    # 2.2. MACD
    macd = MACD(close=df[target_col], window_slow=26, window_fast=12, window_sign=9, fillna=True)
    df['MACD'] = macd.macd()
    df['MACD_SIGNAL'] = macd.macd_signal()
    
    # 2.3. SMA (50) & EMA (20)
    sma = SMAIndicator(close=df[target_col], window=50, fillna=True)
    df['SMA_50'] = sma.sma_indicator()
    
    ema = EMAIndicator(close=df[target_col], window=20, fillna=True)
    df['EMA_20'] = ema.ema_indicator()
    
    # 2.4. Returns (Tỷ lệ thay đổi giá)
    df['Returns'] = df[target_col].pct_change()

    # 3. Loại bỏ dòng NaN (thường chỉ còn dòng đầu tiên do pct_change)
    df.dropna(inplace=True)
    print(f"   - Dữ liệu sau khi thêm đặc trưng: {df.shape}")

    # ==========================================
    # 3. CHUẨN HÓA (SCALING) [0, 1]
    # ==========================================
    print("   ⚖️  Đang chuẩn hóa dữ liệu về khoảng [0, 1]...")
    
    feature_cols = df.columns
    scaler = MinMaxScaler(feature_range=(0, 1))
    
    # Học và biến đổi
    scaled_data = scaler.fit_transform(df)
    
    # Chuyển lại thành DataFrame
    df_scaled = pd.DataFrame(scaled_data, columns=feature_cols, index=df.index)

    # ==========================================
    # 4. LƯU TRỮ
    # ==========================================
    
    # A. Lưu file train
    if not os.path.exists("data/processed"):
        os.makedirs("data/processed")
    df_scaled.to_csv(OUTPUT_FILE)
    print(f"✅ Đã lưu dữ liệu train tại: {OUTPUT_FILE}")
    
    # B. Lưu Scaler
    if not os.path.exists("model"):
        os.makedirs("model")
    joblib.dump(scaler, SCALER_FILE)
    print(f"✅ Đã lưu file Scaler tại: {SCALER_FILE}")
    
    print("\n👇 5 dòng dữ liệu 'ngon' để AI ăn:")
    print(df_scaled.head())

if __name__ == "__main__":
    process_data()
# 📈 Gold Price Prediction Project

Dự án nghiên cứu và dự đoán giá Vàng sử dụng các mô hình Machine Learning (Linear Regression, XGBoost) và Deep Learning (LSTM). Dự án so sánh hiệu suất giữa việc chỉ sử dụng dữ liệu giá Vàng (Univariate) và dữ liệu đa biến (Multivariate: Dầu, Bạc, USD Index...).

## 📂 Cấu trúc thư mục
- `data/`: Chứa dữ liệu thô và dữ liệu đã làm sạch.
- `notebooks/`: Các file Jupyter Notebook dùng để chạy mô hình và phân tích.
- `models/`: Các file mô hình đã được huấn luyện.
- `results/`: Kết quả biểu đồ và bảng so sánh độ chính xác.
- `scipts/`: Các file script để lấy data từ TradingEconomics

## 🛠 Yêu cầu cài đặt

Dự án yêu cầu **Python 3.10** hoặc **3.11** (Lưu ý: Python 3.12+ có thể gặp lỗi với TensorFlow).

### 1. Tải source code
```bash
git clone [https://github.com/alice1204/TTCN2.git](https://github.com/alice1204/TTCN2.git)
cd TTCN2
```

### 2. Thiết lập môi trường ảo .venv
```bash
py -3.11 -m venv .venv
.\.venv\Scripts\Activate
```

### 3. Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### 4. HƯỚNG DẪN SỬ DỤNG
Bước 1: Làm sạch dữ liệu: Chạy các file trong `notebooks/01_data_processing/` để xử lý dữ liệu thô.
Bước 2: Huấn luyện mô hình: Mở các file trong `notebooks/02_models/` và `notebooks/03_models (only Gold)/` để train và xem kết quả dự báo.
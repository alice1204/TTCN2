# te_gold_OK.py → CHẠY NGON 100% – ĐÃ TEST HÔM NAY 26/11/2025
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from datetime import datetime
import pandas as pd
import time

print("Đang khởi động Edge (lần đầu đợi 30-60 giây để tải driver)...")
service = Service(EdgeChromiumDriverManager().install())
options = Options()
options.add_argument("--headless")           # Ẩn cửa sổ Edge
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])

driver = webdriver.Edge(service=service, options=options)
driver.get("https://tradingeconomics.com/commodities")

print("Đang tải trang + kết nối realtime... đợi 25 giây")
for i in range(25,0,-1):
    print(f"   Còn {i:2} giây...", end="\r")
    time.sleep(1)
print("\nĐang chèn code bắt giá vàng...")

# Chèn code bắt vàng (dùng decryptMessage có sẵn của trang)
driver.execute_script("""
    window.gold_data = [];
    if (typeof socket !== 'undefined') {
        const orig = socket.on;
        socket.on = function(ch, cb) {
            if (ch === 'commodities') {
                const wrapper = function(raw) {
                    try {
                        const dec = decryptMessage(raw);
                        if (dec) dec.forEach(i => {
                            if (i.s && (i.s.includes('GOLD') || i.s.includes('XAU'))) {
                                window.gold_data.push(i);
                            }
                        });
                    } catch(e) {}
                    cb(raw);
                };
                return orig.call(this, ch, wrapper);
            }
            return orig.call(this, ch, cb);
        };
    }
""")

df = pd.DataFrame(columns=["time","symbol","price","change","change_pct"])
print("\nBẮT ĐẦU LẤY GIÁ VÀNG REALTIME! (Ctrl+C để dừng)\n")

while True:
    try:
        data = driver.execute_script("return window.gold_data.splice(0);")
        if data:
            for item in data:
                p = item.get("p")
                c = item.get("c",0)
                cp = item.get("cp",0)
                s = item.get("s","GOLD")
                print(f"{datetime.now():%H:%M:%S} | VÀNG = {p:,.2f} USD | ±{c} ({cp:+.2f}%)")
                df = pd.concat([df, pd.DataFrame([{"time":datetime.now(),"symbol":s,"price":p,"change":c,"change_pct":cp}])], ignore_index=True)
            if len(df)%100==0:
                df.to_csv(f"gold_{datetime.now().strftime('%Y%m%d')}.csv", index=False)
                print(f"→ ĐÃ LƯU {len(df)} điểm!")
        time.sleep(2)
    except KeyboardInterrupt:
        df.to_csv(f"GOLD_FINAL_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", index=False)
        print(f"\nĐÃ LƯU {len(df)} điểm vàng!")
        driver.quit()
        break
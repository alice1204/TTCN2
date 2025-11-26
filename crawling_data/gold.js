const axios = require("axios");
const fs = require("fs");

const API_KEY = "589b2a6fc5c9b55f94a9f6fc34c944fb";   // <-- đặt API key vào đây

// Nếu file CSV chưa tồn tại -> tạo phần header
if (!fs.existsSync("gold.csv")) {
    fs.writeFileSync("gold.csv", "time,price_usd\n", "utf8");
}

async function getGoldPrice() {
    try {
        const response = await axios.get(
            `https://api.metalpriceapi.com/v1/latest?api_key=${API_KEY}&base=USD&currencies=XAU`
        );

        if (!response.data || !response.data.rates) {
            console.log("⚠️ API lỗi:", response.data);
            return;
        }

        let raw = response.data.rates.XAU;
        let price = raw < 1 ? 1 / raw : raw;

        // Hiển thị trên màn hình
        console.log(`⏳ ${new Date().toLocaleTimeString()} — ${price.toFixed(2)} USD/oz`);

        // Ghi vào CSV
        const line = `${new Date().toISOString()},${price.toFixed(2)}\n`;
        fs.appendFileSync("gold.csv", line, "utf8");

    } catch (err) {
        console.error("⚠️ Lỗi khi lấy giá vàng:", err.message);
    }
}

// chạy ngay lập tức
getGoldPrice();

// chạy lại mỗi 5 giây
setInterval(getGoldPrice, 5000);

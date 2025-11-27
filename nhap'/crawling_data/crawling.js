const axios = require("axios");
const fs = require("fs");
const { Parser } = require("json2csv");

const CSV_FILE = "market_realtime_60s.csv";

// ======== API KEYS ========
const METAL_KEY = "feb8dcdc6d6219af7c8c7b340dfb4a5f"; 
const AV_KEY = "A9NLVFEGDHYUKJXN";    


// ========== 1. MetalPriceAPI ==========
async function getMetalsCrypto() {
    try {
        const url = `https://api.metalpriceapi.com/v1/latest?api_key=${METAL_KEY}&base=USD&symbols=XAU,XAG,BTC,ETH`;
        const res = await axios.get(url);

        const r = res.data.rates;

        return {
            gold: r.XAU ?? null,
            silver: r.XAG ?? null,
            btc: r.BTC ?? null,
            eth: r.ETH ?? null
        };
    } catch {
        return { gold: null, silver: null, btc: null, eth: null };
    }
}


// ========== 2. ONE REQUEST → AlphaVantage ==========
async function getAlphaVantageBundle() {
    try {
        const url = `https://www.alphavantage.co/query?function=COMMODITY_EXCHANGE_RATE&apikey=${AV_KEY}`;
        const res = await axios.get(url);

        const data = res.data['Realtime Commodity Prices'] || {};

        return {
            wti: data.WTI ?? null,
            brent: data.BRENT ?? null,
            gasoline: data.RBOB ?? null,
            usd_index: data.DXY ?? null
        };
    } catch {
        return { wti: null, brent: null, gasoline: null, usd_index: null };
    }
}


// ======== Save to CSV ========
function appendToCSV(row) {
    const exists = fs.existsSync(CSV_FILE);
    const fields = Object.keys(row);
    const parser = new Parser({ fields, header: !exists });
    const csv = parser.parse([row]);

    fs.appendFileSync(CSV_FILE, csv + "\n", "utf8");
}


// ======== MAIN every 60 seconds ========
async function crawl() {
    console.log("Fetching realtime data...");

    const metalsCrypto = await getMetalsCrypto();
    const alpha = await getAlphaVantageBundle();

    const row = {
        time: new Date().toISOString(),
        gold: metalsCrypto.gold,
        silver: metalsCrypto.silver,
        btc: metalsCrypto.btc,
        eth: metalsCrypto.eth,
        wti: alpha.wti,
        brent: alpha.brent,
        gasoline: alpha.gasoline,
        usd_index: alpha.usd_index
    };

    console.log(row);
    appendToCSV(row);
}

setInterval(crawl, 60000);
crawl();

console.log("Realtime crawling started (1 request / 60s)...");

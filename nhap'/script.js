
    console.log('/controls/io.ascx')
    TEdecryptk = 'j9ONifjoKzxt7kmfYTdKK/5vve0b9Y1UCj/n50jr8d8='
    TEdecryptn = 'Ipp9HNSfVBUntqFK7PrtofYaOPV312xy'
    var socket_url = 'https://live.tradingeconomics.com?key=rain';

    console.log("IO Connecting to " + socket_url)
    var TE_URL = window.location.pathname;
    socket_url += "&url=" + TE_URL;
    $.ajaxSetup({ cache: !0 });

    $.getScript('https://d3fy651gv2fhd3.cloudfront.net/js/io.min.js?v=20240223', function () {
        OnSocketIOLoad();
    });

    var socket = null;
    var MKTChannels = []
    var Subscribed = []

    function base64ToUint8Array(base64) {
        const binaryString = atob(base64);
        const length = binaryString.length;
        const bytes = new Uint8Array(length);
        for (let i = 0; i < length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes;
    }

    function decryptMessage(ciphertext) {
        const key = base64ToUint8Array(TEdecryptk);
        const nonce = base64ToUint8Array(TEdecryptn);
        const ciphertextUint8Array = new Uint8Array(ciphertext);
        let decryptedPlaintext = sodium.crypto_secretbox_open_easy(ciphertextUint8Array, nonce, key);
        decryptedPlaintext = pako.inflate(decryptedPlaintext, { to: 'string' });
        if (decryptedPlaintext !== undefined) {
            return (JSON.parse(decryptedPlaintext))

        }
    }

    function OnSocketIOLoad() {
        var MKT_TBL_SELEC = "#table-logic-handler-for-sockets";
        var TEChannels = ['calendar'];
        if (TE_URL == '/') TEChannels = ['calendar', 'market'];
        else if (TE_URL == "/calendar") TEChannels = ['calendar'];
        else if (TE_URL.indexOf("/shares") > -1) TEChannels = ['market', 'calendar'];
        else if (TE_URL.indexOf("/crypto/treemap") > -1 && window.location.href.toLowerCase().indexOf("freq=") < 0) TEChannels = ['crypto', 'calendar'];
        else if (TE_URL.indexOf("/stocks/treemap") > -1 && window.location.href.toLowerCase().indexOf("freq=") < 0) TEChannels = ['indexes', 'calendar'];
        else if (TE_URL.indexOf("/commodities/treemap") > -1 && window.location.href.toLowerCase().indexOf("freq=") < 0) TEChannels = ['commodities', 'calendar'];
        else if (TE_URL.indexOf("/treemap") > -1 || TE_URL.indexOf("/trademap") > -1 || TE_URL.indexOf("/geomap") > -1 || TE_URL.indexOf("/correlations") > -1) TEChannels = ['calendar'];
        else if (TE_URL.indexOf("calendar") > -1) TEChannels = ['calendar', 'market'];
        else if (TE_URL.indexOf("/dividends") > -1 || TE_URL.indexOf("/ipo") > -1 || TE_URL.indexOf("/stock-splits") > -1 || TE_URL.indexOf("/earnings") > -1) TEChannels = ['calendar', 'market'];
        else if (TE_URL.indexOf("stream") > -1) TEChannels = ['calendar', 'market', 'stream']; else if (TE_URL.indexOf("/currencies") > -1) TEChannels = ['currencies', 'calendar']; else if (TE_URL.indexOf("/stocks") > -1) TEChannels = ['indexes', 'calendar'];
        else if (TE_URL.indexOf("/bonds") > -1) TEChannels = ['bonds', 'calendar']; else if (TE_URL.indexOf("/commodities") > -1) TEChannels = ['commodities', 'calendar'];
        else if (TE_URL.indexOf("/crypto") > -1) TEChannels = ['crypto', 'calendar'];
        else if (TE_URL.indexOf("/forecast/government-bond-10y") > -1) TEChannels = ['bonds', 'calendar'];
        else if (TE_URL.indexOf("/forecast/commodity") > -1) TEChannels = ['commodities', 'calendar'];
        else if (TE_URL.indexOf("/currency") > -1 || TE_URL.indexOf("/stock-market") > -1 || TE_URL.indexOf("/commodity/") > -1 || TE_URL.indexOf("/government-bond-yield") > -1) TEChannels = ['market', 'calendar'];
        else if (TE_URL.split(':').length == 2) TEChannels = ['calendar', 'market'];
        console.log('IO EPOCH: 1764060255'); console.log('IO IP: 113.185.41.79'); console.log('IO URL: /commodity/crude-oil');console.log('IO TOKEN: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlcG9jaCI6MTc2NDA2MDI1NSwiaXAiOiIxMTMuMTg1LjQxLjc5IiwidXJsIjoiL2NvbW1vZGl0eS9jcnVkZS1vaWwifQ.xOfvOyTGuAU2HoMHWjwZIwnI46V7ZyeUqhEj2ut3YlE');
        socket = io.connect(socket_url, {
            withCredentials: true, // Needed for ELB Cookies Stickyness
            
            auth: { token: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlcG9jaCI6MTc2NDA2MDI1NSwiaXAiOiIxMTMuMTg1LjQxLjc5IiwidXJsIjoiL2NvbW1vZGl0eS9jcnVkZS1vaWwifQ.xOfvOyTGuAU2HoMHWjwZIwnI46V7ZyeUqhEj2ut3YlE', url: TE_URL }
        });
        socket.on('connect', function () {

            ioErrorCount = 0;
            IS_CONNECTED = !0;

            // Subscribe to the page symbol
            if (TE_URL.split(':').length == 2 && TESymbol != '') {
                var socketSymbol = TESymbol.toUpperCase()
                console.log('IO Subscribe', socketSymbol, 'No lag');
                socket.emit('subscribe', { s: [socketSymbol] })
                Subscribed.push(socketSymbol)
            }

            // Subscribe to channels
            if (TEChannels && TEChannels.length) {
                console.log('IO Subscribing to TEChannels', TEChannels);
                socket.emit('subscribe', { s: TEChannels })
            } else {
                console.log('IO No TEChannels to Subscribe');
            }

            // Subscribe to symbols
            if (TE_URL != '/' && TE_URL.indexOf("calendar") <= -1 && (TE_URL.split('/').length > 2 || TE_URL.indexOf(":ind") > -1)) {
                gatherMKTChannels();
                if (MKTChannels && MKTChannels.length) {
                    console.log('IO Subscribing to', MKTChannels.length, 'symbols:', MKTChannels);
                    if (MKTChannels.length <= 36) {
                        socket.emit('subscribe', { s: MKTChannels })
                    }
                    else {
                        console.log('IO Subscribing using Chunks');
                        var i, j, temparray, chunk = 36;
                        for (i = 0, j = MKTChannels.length; i < j; i += chunk) {
                            temparray = MKTChannels.slice(i, i + chunk);
                            console.log('IO Subscribing to', temparray.length, 'channels:', temparray);
                            socket.emit('subscribe', { s: temparray })
                        }
                    }

                } else {
                    console.log('IO No MKTChannels to Subscribe');
                }
            }

            socket.on('disconnect', function () { IS_CONNECTED = !1; console.log('Got disconnect!') }); socket.on("smooth-disconnect", function () { socket.disconnect() })
        });
        var isSnap = !0; for (var i = 0; i < TEChannels.length; i++) {
            channel = TEChannels[i]; if (channel == 'calendar' || channel == 'stream') continue;
            console.log('IO Snap ' + channel);
            socket.on(channel, function (a) {
                a = decryptMessage(a)
                if (a.length > 0) {
                    for (i = 0; i < a.length; i++) {
                        TE_UpdateTable(a[i], isSnap)
                        TE_UpdateMiniWidget(a[i])
                        TE_UpdateTreeMap(a[i])
                    }
                    isSnap = !1
                } else { console.log('IO Sent Empty Market Update') }
            })
        }
        var ioErrorCount = 0;
        socket.on("connect_error", (err) => {
            ioErrorCount++;
            console.log('IO Connect Error', ioErrorCount);
            console.log(err.message);
            if (TE_URL.indexOf("calendar") <= -1 && ioErrorCount % 10 == 0) {
                console.log('Disconnecting IO');
                socket.disconnect();
                if (ioErrorCount < 100) {
                    var sleepSecs = ioErrorCount * 5;
                    console.log('Connecting again in', sleepSecs, 'seconds');
                    setInterval(function () {
                        socket.connect()
                    }, sleepSecs * 1000)
                }
                else
                    console.log('Stay disconnected');
            }
        });
        socket.on('tick', function (t) {
            t = decryptMessage(t)
            TE_UpdateTable(t);
            if (TE_URL.split(':').length == 2) UpdateMarketTick(t);
        });
        function gatherMKTChannels() {
            // Temporary block to avoid too many symbols
            return

            var nMarkets = $("[data-subscribe]").length;
            console.log("IO data-subscribe tag present in ", nMarkets, "markets")
            if (nMarkets == null || typeof input !== "undefined") return
            else if (nMarkets > 600)
                console.log("IO Skipping [data-subscribe] because of too many symbols")
            else {
                console.log("IO Searching [data-subscribe]")
                var sCount = 0;
                $("[data-subscribe]").each(function (i, item) {
                    var socketSymbol = $(item).attr('data-subscribe')
                    if (!MKTChannels.includes(socketSymbol) && !Subscribed.includes(socketSymbol)) {
                        sCount++;
                        console.log('IO [data-subscribe]', sCount, socketSymbol)
                        MKTChannels.push(socketSymbol)
                    }
                    else
                        console.log('Already Subscribed. Skip', socketSymbol)
                })
            }
        }
        function TE_UpdateTable(d, isSnap) {
            var s = d.s;
            let element_price;
            $('tr[data-symbol="' + s + '"]').each((i, el) => {
                element_price = $(el).find("td#p");
            })
            if (element_price == undefined) {
                return
            }
            const p0 = parseFloat(element_price.text())
            var r = $('tr[data-symbol="' + s + '"]'); var p = r.find('td#p'); var dec = 4; if (typeof r.data('decimals') !== 'undefined' && r.data('decimals') !== "") dec = r.data("decimals"); if (p0 != d.p.toFixed(dec)) {
                p.text(d.p.toFixed(dec));
                fg … 
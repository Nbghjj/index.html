<!DOCTYPE html>
<html lang="am">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Ayat Bingo - Live Mini App</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { background-color: #120c24; color: #fff; font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 10px; user-select: none; }
        .container { max-width: 480px; margin: 0 auto; display: none; }
        .container.active-screen { display: block !important; }
        
        .card-banner { background: linear-gradient(135deg, #2c1b4d, #1f143a); padding: 20px; border-radius: 14px; text-align: center; border: 1px solid #3c2a6d; margin-bottom: 15px; }
        .card-banner h3 { color: #f39c12; margin: 0 0 5px 0; font-size: 22px; }
        .card-banner p { color: #a08cc4; font-size: 13px; margin: 0 0 10px 0; }
        
        .wallet-box, .room-box { background: #1f143a; padding: 15px; border-radius: 14px; border: 1px solid #3c2a6d; margin-bottom: 15px; }
        .wallet-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .wallet-actions { display: flex; gap: 10px; }
        .wallet-btn { flex: 1; padding: 12px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
        .deposit-btn { background: #2ecc71; color: #fff; }
        .withdraw-btn { background: #e74c3c; color: #fff; }
        
        .join-btn, .bingo-claim-btn { background: linear-gradient(135deg, #f39c12, #f1c40f); border: none; width: 100%; padding: 16px; border-radius: 8px; color: #000; font-weight: bold; cursor: pointer; font-size: 16px; }
        
        /* RESTRICTION / ERROR SCREEN */
        .blocked-screen { text-align: center; padding: 40px 20px; }
        .blocked-screen h2 { color: #e74c3c; margin-bottom: 10px; }
        .blocked-screen p { color: #a08cc4; font-size: 14px; line-height: 1.6; }
        .close-app-btn { background: #f39c12; border: none; padding: 12px 24px; font-weight: bold; border-radius: 8px; cursor: pointer; margin-top: 20px; color: #000; }
        
        .loader { border: 4px solid #2c1b4d; border-top: 4px solid #f39c12; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 50px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>

    <!-- LOADING SCREEN -->
    <div id="loading-screen" class="container active-screen">
        <div class="loader"></div>
        <p style="text-align: center; color: #a08cc4; font-size: 13px;">መረጃዎ እየተረጋገጠ ነው...</p>
    </div>

    <!-- BLOCKED SCREEN (CONTACT ያልላከ ሰው የሚያየው) -->
    <div id="blocked-screen" class="container">
        <div class="card-banner">
            <h3>AYAT BINGO</h3>
            <p>መተግበሪያው አልተከፈተም</p>
        </div>
        <div class="blocked-screen">
            <h2>⚠️ አልተመዘገቡም!</h2>
            <p>
                ይህንን Mini App ለመጠቀም እባክዎ መጀመሪያ ቦቱ ላይ የሚገኘውን <br>
                <b style="color: #f1c40f;">"📱 Share Contact"</b> የሚለውን ተጭነው ስልክ ቁጥርዎን ያጋሩ።
            </p>
            <button class="close-app-btn" onclick="if(window.Telegram) Telegram.WebApp.close();">ወደ ቦቱ ተመለስ</button>
        </div>
    </div>

    <!-- HOME SCREEN -->
    <div id="home-screen" class="container">
        <div class="card-banner">
            <h3>AYAT BINGO</h3>
            <p id="welcomeUserText">Admin: @Kiramk123</p>
            <span>24/7 LIVE TELEGRAM BINGO SYSTEM</span>
        </div>
        
        <div class="wallet-box">
            <div class="wallet-row">
                <span style="font-size: 14px; color: #a08cc4;">የኪስ ቦርሳ (Wallet):</span>
                <span style="font-size: 18px; font-weight: bold; color: #2ecc71;"><b id="home-wallet-val">0</b> Birr</span>
            </div>
            <div class="wallet-actions">
                <button class="wallet-btn deposit-btn" type="button">+ Deposit</button>
                <button class="wallet-btn withdraw-btn" type="button">- Withdraw</button>
            </div>
        </div>

        <div class="room-box">
            <h4>Ayat Bingo Room (20 Birr)</h4>
            <p style="font-size: 13px; color: #a08cc4;">Active Players: <span id="player-count">85</span> / 300</p>
            <button class="join-btn" type="button">JOIN ROOM →</button>
        </div>
    </div>

    <script>
        // ⚠️ ማስታወሻ: ይህንን URL በ Render/Hosting Server URLህ ተካው!
        const SERVER_BACKEND_URL = "https://YOUR-RENDER-APP-NAME.onrender.com";

        function switchScreen(screenId) {
            document.querySelectorAll('.container').forEach(s => s.classList.remove('active-screen'));
            const target = document.getElementById(screenId);
            if (target) target.classList.add('active-screen');
        }

        document.addEventListener("DOMContentLoaded", function() {
            let tg = window.Telegram ? window.Telegram.WebApp : null;
            let telegramUser = null;
            let telegramUsername = "Player";

            if (tg) {
                try {
                    tg.expand();
                    tg.ready();
                    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                        telegramUser = tg.initDataUnsafe.user.id.toString();
                        telegramUsername = tg.initDataUnsafe.user.first_name || "Player";
                    }
                } catch (e) {}
            }

            // Telegram ID ከሌለ ወይም በብራውዘር ከተከፈተ
            if (!telegramUser) {
                switchScreen('blocked-screen');
                return;
            }

            // BACKEND VERIFICATION (የስልክ ቁጥሩን መላኩን ማረጋገጥ)
            fetch(`${SERVER_BACKEND_URL}/api/check-registration`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: telegramUser })
            })
            .then(res => res.json())
            .then(data => {
                if (data.registered) {
                    // ከተመዘገበ ወደ ጨዋታው ማለፍ
                    document.getElementById('welcomeUserText').textContent = `ሰላም ${telegramUsername} | Admin: @Kiramk123`;
                    switchScreen('home-screen');
                } else {
                    // ካልተመዘገበ መከልከል
                    switchScreen('blocked-screen');
                }
            })
            .catch(err => {
                console.error("Verification Error:", err);
                // የኔትወርክ ስህተት ካለ ለጊዜው ወደ blocked ይልካል
                switchScreen('blocked-screen');
            });
        });
    </script>
</body>
</html>

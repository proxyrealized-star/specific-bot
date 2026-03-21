# ================= IMPORTS =================
import random
import hashlib
import sqlite3
import requests
from io import BytesIO
from datetime import datetime, timedelta
import os
import threading

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

# Flask imports for web panel
from flask import Flask, request, render_template_string, redirect, url_for, session

# ================= CONFIG =================
BOT_TOKEN = "8617750252:AAG5HR0Tyl1a0O7cc4lY_pRzpMD0zvXeSUA"
ADMIN_ID = 8554863978
BOT_USERNAME = "specificxx_bot"  # ⚠️ Apna bot username yahan daalo

API_URL = "https://paid-sell.vercel.app/api/proxy?type=insta&value=username_here"

# ================= 4 FORCE CHANNELS =================
FORCE_CHANNELS = [
    "@midnight_xaura",
    "@proxydominates",
    "https://t.me/+gnyODeNwEwNjZDJl",
    "@proxyintfiles"
]

# ================= REFERRAL CREDITS =================
REFERRAL_CREDITS = 3

# ================= FLASK SETUP =================
app = Flask(__name__)
app.secret_key = "bot_secret_key_123"
PORT = int(os.environ.get("PORT", 8080))

# ================= DATABASE =================
db = sqlite3.connect("users.db", check_same_thread=False)
cur = db.cursor()

# Create tables with credit system
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, joined_date TEXT, credits INTEGER DEFAULT 0, total_referrals INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS referrals (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER, referred_id INTEGER, referred_username TEXT, joined_date TEXT, credits_given INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS used_referrals (user_id INTEGER PRIMARY KEY, has_used INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS bot_stats (id INTEGER PRIMARY KEY, total_searches INTEGER DEFAULT 0, total_reports INTEGER DEFAULT 0)")
db.commit()

# Initialize stats
cur.execute("INSERT OR IGNORE INTO bot_stats (id, total_searches, total_reports) VALUES (1, 0, 0)")
db.commit()

def save_user(uid, username=None, referrer_id=None):
    cur.execute("SELECT id FROM users WHERE id = ?", (uid,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (id, username, joined_date, credits, total_referrals) VALUES (?, ?, ?, ?, ?)", 
                    (uid, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0, 0))
        db.commit()
        
        # Handle referral
        if referrer_id and referrer_id != uid:
            cur.execute("SELECT id FROM users WHERE id = ?", (referrer_id,))
            if cur.fetchone():
                cur.execute("SELECT has_used FROM used_referrals WHERE user_id = ?", (uid,))
                if not cur.fetchone():
                    cur.execute("UPDATE users SET credits = credits + ?, total_referrals = total_referrals + 1 WHERE id = ?", 
                              (REFERRAL_CREDITS, referrer_id))
                    cur.execute("INSERT INTO referrals (referrer_id, referred_id, referred_username, joined_date, credits_given) VALUES (?, ?, ?, ?, ?)",
                              (referrer_id, uid, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), REFERRAL_CREDITS))
                    cur.execute("INSERT INTO used_referrals (user_id, has_used) VALUES (?, 1)", (uid,))
                    db.commit()
    else:
        if username:
            cur.execute("UPDATE users SET username = ? WHERE id = ?", (username, uid))
            db.commit()

def get_credits(uid):
    cur.execute("SELECT credits FROM users WHERE id = ?", (uid,))
    result = cur.fetchone()
    return result[0] if result else 0

def deduct_credit(uid):
    credits = get_credits(uid)
    if credits > 0:
        cur.execute("UPDATE users SET credits = credits - 1 WHERE id = ?", (uid,))
        db.commit()
        return True
    return False

def add_credits(uid, amount):
    cur.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (amount, uid))
    db.commit()

def total_users():
    cur.execute("SELECT COUNT(*) FROM users")
    return cur.fetchone()[0]

def increment_searches():
    cur.execute("UPDATE bot_stats SET total_searches = total_searches + 1 WHERE id = 1")
    db.commit()

def increment_reports():
    cur.execute("UPDATE bot_stats SET total_reports = total_reports + 1 WHERE id = 1")
    db.commit()

def get_stats():
    cur.execute("SELECT total_searches, total_reports FROM bot_stats WHERE id = 1")
    return cur.fetchone()

def get_referral_link(user_id):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

# ================= FORCE JOIN =================
async def is_joined(bot, user_id):
    for ch in FORCE_CHANNELS:
        try:
            if ch.startswith("https://"):
                continue
            else:
                member = await bot.get_chat_member(ch, user_id)
                if member.status in ["left", "kicked"]:
                    return False
        except:
            return False
    return True

def join_kb():
    btns = []
    for ch in FORCE_CHANNELS:
        if ch.startswith("https://"):
            btns.append([InlineKeyboardButton(f"📢 Join Channel {FORCE_CHANNELS.index(ch)+1}", url=ch)])
        else:
            btns.append([InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch[1:]}")])
    btns.append([InlineKeyboardButton("✅ Check Again", callback_data="check")])
    return InlineKeyboardMarkup(btns)

# ================= UI =================
def menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Deep Analysis", callback_data="deep")],
        [InlineKeyboardButton("💰 My Credits", callback_data="credits")],
        [InlineKeyboardButton("🔗 Referral Link", callback_data="referral")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ])

def after_kb(username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Full Report", callback_data=f"report|{username}")],
        [InlineKeyboardButton("🔄 Analyze Again", callback_data="deep")],
        [InlineKeyboardButton("⬅️ Menu", callback_data="menu")]
    ])

# ================= API =================
def fetch_profile(username):
    url = API_URL.format(username)
    
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            print(f"HTTP Error: {r.status_code}")
            return None
        
        data = r.json()
        print(f"API Response for @{username}: {data}")
        
        if data.get("status") != "ok":
            print(f"API Error: {data.get('message', 'Unknown error')}")
            return None
        
        profile = data.get("profile", {})
        if not profile:
            print("No profile data found")
            return None
        
        return {
            "status": "ok",
            "collected_at": data.get("collected_at", ""),
            "developer": data.get("developer", "@E_commerceseller"),
            "profile": profile
        }
        
    except Exception as e:
        print(f"API Error: {e}")
        return None

def download_image(url):
    try:
        r = requests.get(url, timeout=15)
        bio = BytesIO(r.content)
        bio.name = "profile.jpg"
        return bio
    except:
        return None

# ================= ANALYSIS ENGINE =================
def calc_risk(profile_data):
    profile = profile_data.get("profile", {})
    username = profile.get("username", "user")
    bio = (profile.get("biography") or "").lower()
    private = profile.get("is_private", False)
    
    try:
        posts = int(profile.get("posts", 0))
    except:
        posts = 0

    seed = int(hashlib.sha256(username.encode()).hexdigest(), 16)
    rnd = random.Random(seed)

    pool = [
        "SCAM", "SPAM", "NUDITY",
        "HATE", "HARASSMENT",
        "BULLYING", "VIOLENCE",
        "TERRORISM"
    ]

    if any(x in bio for x in ["music", "rapper", "artist", "singer", "phonk", "promo"]):
        pool += ["DRUGS", "DRUGS"]

    if private and posts < 5:
        pool += ["SCAM", "SCAM", "SCAM"]

    include_self = private and rnd.choice([True, False])
    if include_self:
        pool.append("SELF")
        pool = [i for i in pool if i != "HATE"]

    if rnd.random() < 0.15:
        pool.append("WEAPONS")

    rnd.shuffle(pool)
    selected = list(dict.fromkeys(pool))[:rnd.randint(1, 3)]

    issues, intensity = [], 0
    for i in selected:
        count = rnd.randint(3, 4) if i == "WEAPONS" else rnd.randint(1, 4)
        intensity += count
        issues.append(f"{count}X {i}")

    risk = min(95, 40 + intensity * 6 + (10 if private else 0) + (15 if posts < 5 else 0))
    return risk, issues

# ================ FORMAT REPORT =================
def format_report(data, risk, issues):
    profile = data.get("profile", {})
    collected_at = data.get("collected_at", datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"))
    developer = data.get("developer", "@E_commerceseller")
    
    username = profile.get("username", "N/A")
    full_name = profile.get("full_name", "N/A")
    user_id = profile.get("id", "N/A")
    bio = profile.get("biography", "") or "No bio"
    followers = f"{profile.get('followers', 0):,}"
    following = f"{profile.get('following', 0):,}"
    posts = profile.get("posts", 0)
    private = "✅ YES" if profile.get("is_private", False) else "❌ NO"
    verified = "✅ YES" if profile.get("is_verified", False) else "❌ NO"
    business = "✅ YES" if profile.get("is_business_account", False) else "❌ NO"
    professional = "✅ YES" if profile.get("is_professional_account", False) else "❌ NO"
    external_url = profile.get("external_url", "None")
    
    report = f"""
╔══════════════════════════════════════╗
║     🔥 INSTAGRAM ANALYZER PRO 🔥     ║
║           BY @proxyfxc               ║
╚══════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 INSTAGRAM INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• USERNAME: @{username}
• FULL NAME: {full_name}
• USER ID: {user_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 BIO:
{bio}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 STATISTICS:
• 👥 FOLLOWERS: {followers}
• 🔄 FOLLOWING: {following}
• 📸 POSTS: {posts}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔒 PRIVATE: {private}
✅ VERIFIED: {verified}
💼 BUSINESS: {business}
🎯 PROFESSIONAL: {professional}
🔗 EXTERNAL URL: {external_url if external_url else 'None'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 DETECTED ISSUES"""
    
    for issue in issues:
        report += f"\n• {issue}"
    
    if risk >= 80:
        risk_emoji = "🔴 HIGH RISK"
    elif risk >= 50:
        risk_emoji = "🟡 MEDIUM RISK"
    else:
        risk_emoji = "🟢 LOW RISK"
    
    report += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ RISK ASSESSMENT
• SCORE: {risk}% {risk_emoji}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️ COLLECTED: {collected_at}
💻 DEVELOPER: {developer}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    return report

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username
    
    # Check for referral
    referrer_id = None
    if context.args and context.args[0].startswith("ref_"):
        try:
            referrer_id = int(context.args[0].split("_")[1])
        except:
            pass
    
    save_user(uid, username, referrer_id)

    if not await is_joined(context.bot, uid):
        await update.message.reply_text(
            "❌ Please join all channels first.",
            reply_markup=join_kb()
        )
        return

    credits = get_credits(uid)
    
    await update.message.reply_text(
        f"✨ Welcome to Insta Analyzer Pro ✨\n\n"
        f"📊 Your Status: {'✅ PREMIUM' if credits > 100 else '❌ FREE'}\n"
        f"💰 Credits: {credits}\n\n"
        f"Send any Instagram username to analyze!",
        reply_markup=menu_kb()
    )

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "check":
        if await is_joined(context.bot, uid):
            credits = get_credits(uid)
            await q.message.edit_text(f"✅ Access granted!\n\n💰 Credits: {credits}", reply_markup=menu_kb())
        else:
            await q.message.reply_text("❌ Please join all channels first", reply_markup=join_kb())

    elif q.data == "menu":
        credits = get_credits(uid)
        await q.message.edit_text(f"🏠 Main Menu\n\n💰 Credits: {credits}", reply_markup=menu_kb())

    elif q.data == "credits":
        credits = get_credits(uid)
        cur.execute("SELECT total_referrals FROM users WHERE id = ?", (uid,))
        referrals = cur.fetchone()[0] if cur.fetchone() else 0
        
        text = f"💰 YOUR CREDITS: {credits}\n"
        text += f"👥 TOTAL REFERRALS: {referrals}\n\n"
        text += f"🔰 Get more credits:\n"
        text += f"• Refer friends: +{REFERRAL_CREDITS} credits each\n"
        text += f"• Contact admin to buy credits"
        
        await q.message.edit_text(text, reply_markup=menu_kb())

    elif q.data == "referral":
        link = get_referral_link(uid)
        text = f"🔗 YOUR REFERRAL LINK:\n\n{link}\n\n"
        text += f"💰 You get {REFERRAL_CREDITS} credits for each friend who joins!"
        await q.message.edit_text(text, reply_markup=menu_kb())

    elif q.data == "deep":
        credits = get_credits(uid)
        if credits <= 0:
            await q.message.reply_text(
                "❌ You have 0 credits!\n\n"
                "Get more credits by:\n"
                "• Referring friends (+3 credits each)\n"
                "• Contact admin to buy credits",
                reply_markup=menu_kb()
            )
            return
            
        context.user_data["wait"] = True
        await q.message.reply_text("👤 Send Instagram username (with or without @):")

    elif q.data.startswith("report|"):
        username = q.data.split("|")[1]
        
        if not deduct_credit(uid):
            await q.message.reply_text("❌ Insufficient credits!", reply_markup=menu_kb())
            return
        
        await q.message.reply_text("🔄 Fetching full report...")
        increment_reports()
        
        data = fetch_profile(username)
        if not data:
            add_credits(uid, 1)  # Refund
            await q.message.reply_text("❌ Profile not found or API error")
            return
        
        risk, issues = calc_risk(data)
        report = format_report(data, risk, issues)
        credits_left = get_credits(uid)
        report += f"\n💰 Credits left: {credits_left}"
        
        await q.message.reply_text(report, reply_markup=after_kb(username))

    elif q.data == "help":
        await q.message.reply_text(
            "🔍 *How to use:*\n"
            "• Send any Instagram username\n"
            "• Get detailed analysis\n"
            "• Risk assessment included\n\n"
            "💰 *Credit System:*\n"
            "• Each analysis costs 1 credit\n"
            "• Get 3 credits per referral\n\n"
            "📊 *Commands:*\n"
            "• /start - Main menu\n"
            "• /credits - Check credits\n"
            "• /referral - Get referral link\n\n"
            "👑 *Admin:*\n"
            "• /users - Total users\n"
            "• /stats - Bot stats\n"
            "• /addcredits [user_id] [amount] - Add credits\n"
            "• /broadcast - Send message",
            parse_mode='Markdown'
        )

async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("wait"):
        return

    context.user_data["wait"] = False
    uid = update.effective_user.id
    username = update.message.text.replace("@", "").strip()
    
    if not username:
        await update.message.reply_text("❌ Please send a valid username")
        return
    
    credits = get_credits(uid)
    if credits <= 0:
        await update.message.reply_text(
            "❌ You have 0 credits!\n\n"
            "Get more credits by:\n"
            "• Referring friends (+3 credits each)\n"
            "• Contact admin to buy credits",
            reply_markup=menu_kb()
        )
        return
    
    status_msg = await update.message.reply_text("🔄 Analyzing Instagram profile...")
    increment_searches()
    
    if not deduct_credit(uid):
        await status_msg.edit_text("❌ Credit deduction failed")
        return
    
    data = fetch_profile(username)
    
    if not data:
        add_credits(uid, 1)  # Refund
        await status_msg.edit_text("❌ Profile not found or API error")
        return
    
    risk, issues = calc_risk(data)
    profile = data.get("profile", {})
    pic_url = profile.get("profile_pic_url_hd")
    
    credits_left = get_credits(uid)
    caption = f"🎯 ANALYSIS COMPLETE\n@{username}\nRisk: {risk}%\n💰 Credits left: {credits_left}"
    
    if pic_url:
        try:
            pic_data = download_image(pic_url)
            if pic_data:
                await update.message.reply_photo(
                    photo=pic_data,
                    caption=caption,
                    reply_markup=after_kb(username)
                )
                await status_msg.delete()
                return
        except Exception as e:
            print(f"Photo error: {e}")
    
    await status_msg.edit_text(caption, reply_markup=after_kb(username))

# ================= ADMIN COMMANDS =================
async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    await update.message.reply_text(f"👥 Total users: {total_users()}")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    searches, reports = get_stats()
    total = total_users()
    await update.message.reply_text(f"📊 STATS:\n👥 Users: {total}\n🔍 Searches: {searches}\n📄 Reports: {reports}")

async def addcredits_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addcredits [user_id] [amount]")
        return
    
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
        add_credits(user_id, amount)
        await update.message.reply_text(f"✅ Added {amount} credits to user {user_id}")
        
        try:
            await context.bot.send_message(user_id, f"💰 You received {amount} credits from admin!")
        except:
            pass
    except:
        await update.message.reply_text("❌ Invalid input")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast message")
        return

    msg = " ".join(context.args)
    cur.execute("SELECT id FROM users")
    sent = 0
    failed = 0

    for (uid,) in cur.fetchall():
        try:
            await context.bot.send_message(uid, msg)
            sent += 1
        except:
            failed += 1

    await update.message.reply_text(f"✅ Broadcast sent to {sent} users\n❌ Failed: {failed}")

# ================= FLASK ROUTES =================
@app.route('/')
def home():
    return "Bot is running! Admin panel at /admin"

@app.route('/admin')
def admin_login():
    return '''
    <html>
        <body style="background:#1a1a1a;color:#fff;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;">
            <div style="background:#2d2d2d;padding:30px;border-radius:10px;">
                <h2>Admin Login</h2>
                <form method="post" action="/admin/auth">
                    <input type="text" name="username" placeholder="Username" style="width:100%;padding:10px;margin:10px 0;" required>
                    <input type="password" name="password" placeholder="Password" style="width:100%;padding:10px;margin:10px 0;" required>
                    <button type="submit" style="background:#00a86b;color:#fff;padding:10px;width:100%;border:none;border-radius:5px;">Login</button>
                </form>
            </div>
        </body>
    </html>
    '''

@app.route('/admin/auth', methods=['POST'])
def admin_auth():
    if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
        session['admin'] = True
        return redirect(url_for('admin_dashboard'))
    return "Invalid credentials"

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    searches, reports = get_stats()
    total = total_users()
    
    users = cur.execute("SELECT id, username, credits, total_referrals FROM users ORDER BY joined_date DESC LIMIT 20").fetchall()
    
    html = f'''
    <html>
        <head>
            <title>Admin Dashboard</title>
            <style>
                body {{background:#1a1a1a;color:#fff;font-family:Arial;padding:20px;}}
                .stats {{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:30px;}}
                .stat-card {{background:#2d2d2d;padding:20px;border-radius:10px;text-align:center;}}
                table {{width:100%;background:#2d2d2d;border-radius:10px;overflow:hidden;}}
                th,td {{padding:12px;text-align:left;border-bottom:1px solid #3d3d3d;}}
                th {{background:#00a86b;}}
            </style>
        </head>
        <body>
            <h1>Admin Dashboard</h1>
            <div class="stats">
                <div class="stat-card"><h3>Total Users</h3><p>{total}</p></div>
                <div class="stat-card"><h3>Searches</h3><p>{searches}</p></div>
                <div class="stat-card"><h3>Reports</h3><p>{reports}</p></div>
            </div>
            <h2>Recent Users</h2>
            <table>
                <tr><th>ID</th><th>Username</th><th>Credits</th><th>Referrals</th></tr>
    '''
    for uid, uname, credits, refs in users:
        html += f'<tr><td>{uid}</td><td>@{uname or "N/A"}</td><td>{credits}</td><td>{refs}</td></tr>'
    
    html += '''
            </table>
            <p><a href="/admin/logout" style="color:#fff;">Logout</a></p>
        </body>
    </html>
    '''
    return html

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# ================= RUN =================
def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def main():
    # Start Flask in thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start bot
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("addcredits", addcredits_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username))

    print("✅ Bot started!")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📊 Force channels: {FORCE_CHANNELS}")
    print(f"💰 Referral credits: {REFERRAL_CREDITS}")
    print(f"🌐 Admin panel: http://localhost:{PORT}/admin")
    app.run_polling()

if __name__ == "__main__":
    main()

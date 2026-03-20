# ================= IMPORTS =================
import random
import hashlib
import sqlite3
import requests
from io import BytesIO
from datetime import datetime
import os
import threading
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

# Flask imports
from flask import Flask, request, render_template_string, redirect, url_for, session
import threading

# ================= CONFIG FROM ENV =================
# Get from environment variables (set these in Render)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8617750252:AAG5HR0Tyl1a0O7cc4lY_pRzpMD0zvXeSUA")  # Fallback for local
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8210445482"))  # Convert to int
PORT = int(os.environ.get("PORT", 8080))

API_URL = "https://tg-user-id-to-number-4erk.onrender.com/api/insta={}?api_key=PAID_INSTA_SELL187"

# ================= 4 FORCE CHANNELS =================
FORCE_CHANNELS = [
    "@midnight_xaura",        # 1
    "@proxydominates",        # 2
    "https://t.me/+gnyODeNwEwNjZDJl",  # 3 (private link)
    "@proxyintfiles"          # 4
]

# Admin panel credentials
ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "admin123")
SECRET_KEY = os.environ.get("SECRET_KEY", "bot_secret_key_123_change_in_production")

# Referral credits
REFERRAL_CREDITS = 3

# ================= FLASK APP =================
app = Flask(__name__)
app.secret_key = SECRET_KEY

# ================= DATABASE =================
db = sqlite3.connect("users.db", check_same_thread=False)
cur = db.cursor()

# Create tables with referral and premium system
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, joined_date TEXT, credits INTEGER DEFAULT 0, total_referrals INTEGER DEFAULT 0, is_premium INTEGER DEFAULT 0, premium_until TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS referrals (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER, referred_id INTEGER, referred_username TEXT, joined_date TEXT, credits_given INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS bot_stats (id INTEGER PRIMARY KEY, total_searches INTEGER, total_reports INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS used_referrals (user_id INTEGER PRIMARY KEY, has_used INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS usage_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, timestamp TEXT)")
db.commit()

# Initialize stats if not exists
cur.execute("INSERT OR IGNORE INTO bot_stats (id, total_searches, total_reports) VALUES (1, 0, 0)")
db.commit()

def save_user(uid, username=None, referrer_id=None):
    """Save user to database with referral handling"""
    # Check if user exists
    cur.execute("SELECT id FROM users WHERE id = ?", (uid,))
    if not cur.fetchone():
        # New user - insert
        cur.execute("INSERT INTO users (id, username, joined_date, credits, total_referrals, is_premium) VALUES (?, ?, ?, ?, ?, ?)", 
                    (uid, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0, 0, 0))
        db.commit()
        
        # Handle referral if provided
        if referrer_id and referrer_id != uid:
            # Check if referrer exists and referred user hasn't used referral before
            cur.execute("SELECT id FROM users WHERE id = ?", (referrer_id,))
            if cur.fetchone():
                cur.execute("SELECT has_used FROM used_referrals WHERE user_id = ?", (uid,))
                if not cur.fetchone():
                    # Give credits to referrer
                    cur.execute("UPDATE users SET credits = credits + ?, total_referrals = total_referrals + 1 WHERE id = ?", 
                              (REFERRAL_CREDITS, referrer_id))
                    # Log the referral
                    cur.execute("INSERT INTO referrals (referrer_id, referred_id, referred_username, joined_date, credits_given) VALUES (?, ?, ?, ?, ?)",
                              (referrer_id, uid, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), REFERRAL_CREDITS))
                    # Mark as used
                    cur.execute("INSERT INTO used_referrals (user_id, has_used) VALUES (?, 1)", (uid,))
                    db.commit()
    else:
        # User exists - just update username if needed
        if username:
            cur.execute("UPDATE users SET username = ? WHERE id = ?", (username, uid))
            db.commit()

def get_user_credits(uid):
    """Get user credits"""
    cur.execute("SELECT credits, is_premium FROM users WHERE id = ?", (uid,))
    result = cur.fetchone()
    if result:
        return result[0], result[1]  # credits, is_premium
    return 0, 0

def deduct_credit(uid):
    """Deduct one credit from user (if not premium)"""
    credits, is_premium = get_user_credits(uid)
    
    if is_premium == 1:
        return True  # Premium users don't need credits
    
    if credits > 0:
        cur.execute("UPDATE users SET credits = credits - 1 WHERE id = ?", (uid,))
        db.commit()
        return True
    return False

def add_credits(uid, amount):
    """Add credits to user"""
    cur.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (amount, uid))
    db.commit()

def make_premium(uid, days=30):
    """Make user premium"""
    premium_until = (datetime.now().replace(hour=23, minute=59, second=59) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("UPDATE users SET is_premium = 1, premium_until = ? WHERE id = ?", (premium_until, uid))
    db.commit()

def remove_premium(uid):
    """Remove premium status"""
    cur.execute("UPDATE users SET is_premium = 0, premium_until = NULL WHERE id = ?", (uid,))
    db.commit()

def check_premium(uid):
    """Check if user is premium and if premium expired"""
    cur.execute("SELECT is_premium, premium_until FROM users WHERE id = ?", (uid,))
    result = cur.fetchone()
    if result and result[0] == 1:
        if result[1]:
            premium_until = datetime.strptime(result[1], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > premium_until:
                # Premium expired
                remove_premium(uid)
                return False
        return True
    return False

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

def log_usage(user_id, action):
    """Log user actions"""
    cur.execute("INSERT INTO usage_log (user_id, action, timestamp) VALUES (?, ?, ?)",
                (user_id, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()

def get_referral_link(user_id):
    """Generate referral link"""
    return f"https://t.me/{(BOT_TOKEN.split(':')[0])}?start=ref_{user_id}"

def get_user_details(uid):
    """Get complete user details"""
    cur.execute("SELECT id, username, joined_date, credits, total_referrals, is_premium, premium_until FROM users WHERE id = ?", (uid,))
    return cur.fetchone()

def get_top_referrers(limit=10):
    """Get top referrers"""
    cur.execute("SELECT id, username, total_referrals, credits FROM users WHERE total_referrals > 0 ORDER BY total_referrals DESC LIMIT ?", (limit,))
    return cur.fetchall()

# ================= FORCE JOIN =================
async def is_joined(bot, user_id):
    for ch in FORCE_CHANNELS:
        try:
            # Handle channel links vs usernames
            if ch.startswith("https://"):
                # For private links, we can't check membership directly
                # So we'll just assume they need to join
                continue
            else:
                member = await bot.get_chat_member(ch, user_id)
                if member.status in ["left", "kicked"]:
                    return False
        except Exception as e:
            print(f"Error checking channel {ch}: {e}")
            return False
    return True

def join_kb():
    btns = []
    for ch in FORCE_CHANNELS:
        if ch.startswith("https://"):
            # Private link
            btns.append([InlineKeyboardButton(f"📢 Join Channel {FORCE_CHANNELS.index(ch)+1}", url=ch)])
        else:
            # Public channel
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
        print(f"API Response for @{username}: {data}")  # Debug print
        
        # Check if status is 'ok' (API returns 'ok' not 'success')
        if data.get("status") != "ok":
            print(f"API Error: {data.get('message', 'Unknown error')}")
            return None
        
        # Extract profile data
        profile = data.get("profile", {})
        if not profile:
            print("No profile data found")
            return None
        
        # Return combined data
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
    """Download image from URL"""
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
    
    # Parse posts count
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
    """API response ko stylish box format mein karo"""
    
    profile = data.get("profile", {})
    collected_at = data.get("collected_at", datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"))
    developer = data.get("developer", "@E_commerceseller")
    
    username = profile.get("username", "N/A")
    full_name = profile.get("full_name", "N/A")
    user_id = profile.get("id", "N/A")
    bio = profile.get("biography", "") or "No bio"
    followers = f"{profile.get('followers', 0):,}"  # Add commas
    following = f"{profile.get('following', 0):,}"
    posts = profile.get("posts", 0)
    private = "✅ YES" if profile.get("is_private", False) else "❌ NO"
    verified = "✅ YES" if profile.get("is_verified", False) else "❌ NO"
    business = "✅ YES" if profile.get("is_business_account", False) else "❌ NO"
    professional = "✅ YES" if profile.get("is_professional_account", False) else "❌ NO"
    external_url = profile.get("external_url", "None")
    
    # Build the stylish report
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
    
    # Determine risk level emoji
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
    
    # Check for referral in start command
    referrer_id = None
    if context.args and context.args[0].startswith("ref_"):
        try:
            referrer_id = int(context.args[0].split("_")[1])
        except:
            pass
    
    # Save user with referral
    save_user(uid, username, referrer_id)

    if not await is_joined(context.bot, uid):
        await update.message.reply_text(
            "❌ Please join all channels first.",
            reply_markup=join_kb()
        )
        return

    credits, is_premium = get_user_credits(uid)
    premium_status = "✅ PREMIUM" if is_premium == 1 else "❌ FREE"
    
    await update.message.reply_text(
        f"✨ Welcome to Insta Analyzer Pro ✨\n\n"
        f"📊 Your Status: {premium_status}\n"
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
            credits, is_premium = get_user_credits(uid)
            premium_status = "✅ PREMIUM" if is_premium == 1 else "❌ FREE"
            await q.message.edit_text(
                f"✅ Access granted!\n\n📊 Status: {premium_status}\n💰 Credits: {credits}",
                reply_markup=menu_kb()
            )
        else:
            await q.message.reply_text("❌ Please join all channels first", reply_markup=join_kb())

    elif q.data == "menu":
        credits, is_premium = get_user_credits(uid)
        premium_status = "✅ PREMIUM" if is_premium == 1 else "❌ FREE"
        await q.message.edit_text(
            f"🏠 Main Menu\n\n📊 Status: {premium_status}\n💰 Credits: {credits}",
            reply_markup=menu_kb()
        )

    elif q.data == "credits":
        credits, is_premium = get_user_credits(uid)
        referrals = get_user_details(uid)[4] if get_user_details(uid) else 0
        
        text = f"💰 YOUR CREDITS: {credits}\n"
        text += f"👥 TOTAL REFERRALS: {referrals}\n"
        text += f"🎖️ PREMIUM: {'YES' if is_premium == 1 else 'NO'}\n\n"
        text += f"🔰 Get more credits:\n"
        text += f"• Refer friends: +{REFERRAL_CREDITS} credits each\n"
        text += f"• Contact admin for premium"
        
        await q.message.edit_text(text, reply_markup=menu_kb())

    elif q.data == "referral":
        link = get_referral_link(uid)
        text = f"🔗 YOUR REFERRAL LINK:\n\n{link}\n\n"
        text += f"💰 You get {REFERRAL_CREDITS} credits for each friend who joins!"
        await q.message.edit_text(text, reply_markup=menu_kb())

    elif q.data == "deep":
        # Check credits/premium before proceeding
        credits, is_premium = get_user_credits(uid)
        if credits <= 0 and is_premium == 0:
            await q.message.reply_text(
                "❌ You have 0 credits!\n\n"
                "Get more credits by:\n"
                "• Referring friends (+3 credits each)\n"
                "• Contact admin for premium",
                reply_markup=menu_kb()
            )
            return
            
        context.user_data["wait"] = True
        await q.message.reply_text("👤 Send Instagram username (with or without @):")

    elif q.data.startswith("report|"):
        username = q.data.split("|")[1]
        
        # Deduct credit (premium users don't get deducted)
        credits, is_premium = get_user_credits(uid)
        if is_premium == 0:
            if not deduct_credit(uid):
                await q.message.reply_text("❌ Insufficient credits!", reply_markup=menu_kb())
                return
        
        await q.message.reply_text("🔄 Fetching full report...")
        increment_reports()
        log_usage(uid, f"full_report_{username}")
        
        data = fetch_profile(username)
        if not data:
            await q.message.reply_text("❌ Profile not found or API error")
            return
        
        risk, issues = calc_risk(data)
        report = format_report(data, risk, issues)
        
        await q.message.reply_text(report, reply_markup=after_kb(username))

    elif q.data == "help":
        await q.message.reply_text(
            "🔍 *How to use:*\n"
            "• Send any Instagram username\n"
            "• Get detailed analysis\n"
            "• Risk assessment included\n\n"
            "💰 *Credit System:*\n"
            "• Each analysis costs 1 credit\n"
            "• Get 3 credits per referral\n"
            "• Premium users get unlimited\n\n"
            "📊 *Commands:*\n"
            "• /start - Main menu\n"
            "• /credits - Check credits\n"
            "• /referral - Get referral link\n\n"
            "👑 *Admin only:*\n"
            "• /users - Total users\n"
            "• /stats - Bot stats\n"
            "• /premium @user - Make premium\n"
            "• /broadcast - Send message",
            parse_mode='Markdown'
        )

async def handle_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("wait"):
        return

    context.user_data["wait"] = False
    uid = update.effective_user.id
    username_input = update.message.text.replace("@", "").strip()
    
    if not username_input:
        await update.message.reply_text("❌ Please send a valid username")
        return
    
    # Check credits/premium
    credits, is_premium = get_user_credits(uid)
    if credits <= 0 and is_premium == 0:
        await update.message.reply_text(
            "❌ You have 0 credits!\n\n"
            "Get more credits by:\n"
            "• Referring friends (+3 credits each)\n"
            "• Contact admin for premium",
            reply_markup=menu_kb()
        )
        return
    
    status_msg = await update.message.reply_text("🔄 Analyzing Instagram profile...")
    increment_searches()
    log_usage(uid, f"search_{username_input}")
    
    # Deduct credit (premium users don't get deducted)
    if is_premium == 0:
        deduct_credit(uid)
    
    # Fetch profile data
    data = fetch_profile(username_input)
    
    if not data:
        await status_msg.edit_text("❌ Profile not found or API error")
        return
    
    # Calculate risk
    risk, issues = calc_risk(data)
    
    # Get profile pic URL
    profile = data.get("profile", {})
    pic_url = profile.get("profile_pic_url_hd")
    
    # Get updated credits
    credits, is_premium = get_user_credits(uid)
    caption = f"🎯 ANALYSIS COMPLETE\n@{username_input}\nRisk: {risk}%\n💰 Credits left: {credits if is_premium==0 else '∞'}"
    
    # Try to send with profile pic
    if pic_url:
        try:
            pic_data = download_image(pic_url)
            if pic_data:
                await update.message.reply_photo(
                    photo=pic_data,
                    caption=caption,
                    reply_markup=after_kb(username_input)
                )
                await status_msg.delete()
                return
        except Exception as e:
            print(f"Photo error: {e}")
    
    # Send text-only response
    await status_msg.edit_text(caption, reply_markup=after_kb(username_input))

# ================= ADMIN COMMANDS =================
async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    total = total_users()
    premium = cur.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1").fetchone()[0]
    await update.message.reply_text(f"📊 STATISTICS:\n\n👥 Total users: {total}\n⭐ Premium users: {premium}")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    searches, reports = get_stats()
    total = total_users()
    premium = cur.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1").fetchone()[0]
    referrals = cur.execute("SELECT COUNT(*) FROM referrals").fetchone()[0]
    
    await update.message.reply_text(
        f"📊 BOT STATISTICS:\n\n"
        f"👥 Total Users: {total}\n"
        f"⭐ Premium Users: {premium}\n"
        f"🔍 Total Searches: {searches}\n"
        f"📄 Total Reports: {reports}\n"
        f"🔗 Total Referrals: {referrals}"
    )

async def premium_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /premium @username [days]")
        return
    
    username = context.args[0].replace("@", "")
    days = 30  # default
    if len(context.args) > 1:
        try:
            days = int(context.args[1])
        except:
            pass
    
    # Find user by username
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = cur.fetchone()
    
    if result:
        make_premium(result[0], days)
        await update.message.reply_text(f"✅ Made @{username} premium for {days} days!")
        
        # Notify user
        try:
            await context.bot.send_message(
                result[0],
                f"🎉 Congratulations! You are now a PREMIUM user for {days} days!\n"
                f"✨ You now have unlimited access to all features!"
            )
        except:
            pass
    else:
        await update.message.reply_text("❌ User not found")

async def remove_premium_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /removepremium @username")
        return
    
    username = context.args[0].replace("@", "")
    
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = cur.fetchone()
    
    if result:
        remove_premium(result[0])
        await update.message.reply_text(f"✅ Removed premium from @{username}")
        
        # Notify user
        try:
            await context.bot.send_message(
                result[0],
                "Your premium subscription has expired. Use /start to check your current status."
            )
        except:
            pass
    else:
        await update.message.reply_text("❌ User not found")

async def add_credits_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addcredits @username amount")
        return
    
    username = context.args[0].replace("@", "")
    try:
        amount = int(context.args[1])
    except:
        await update.message.reply_text("❌ Invalid amount")
        return
    
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = cur.fetchone()
    
    if result:
        add_credits(result[0], amount)
        await update.message.reply_text(f"✅ Added {amount} credits to @{username}")
        
        # Notify user
        try:
            await context.bot.send_message(
                result[0],
                f"💰 You received {amount} credits!"
            )
        except:
            pass
    else:
        await update.message.reply_text("❌ User not found")

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

async def top_referrers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    top = get_top_referrers(10)
    text = "🏆 TOP REFERRERS:\n\n"
    
    for i, (uid, username, referrals, credits) in enumerate(top, 1):
        text += f"{i}. @{username or uid}\n   👥 {referrals} referrals | 💰 {credits} credits\n"
    
    await update.message.reply_text(text)

# ================= FLASK ROUTES =================
@app.route('/')
def home():
    return "Bot is running! Admin panel at /admin"

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid credentials"
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Login</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial; background: #1a1a1a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; }
                .login-form { background: #2d2d2d; padding: 30px; border-radius: 10px; width: 300px; }
                input { width: 100%; padding: 10px; margin: 10px 0; border: none; border-radius: 5px; }
                button { background: #00a86b; color: white; padding: 10px; border: none; border-radius: 5px; width: 100%; cursor: pointer; }
            </style>
        </head>
        <body>
            <div class="login-form">
                <h2>Admin Login</h2>
                <form method="post">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Login</button>
                </form>
            </div>
        </body>
        </html>
    ''')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    searches, reports = get_stats()
    total = total_users()
    premium = cur.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1").fetchone()[0]
    referrals = cur.execute("SELECT COUNT(*) FROM referrals").fetchone()[0]
    
    # Get recent users
    recent = cur.execute("SELECT id, username, joined_date, credits, is_premium FROM users ORDER BY joined_date DESC LIMIT 10").fetchall()
    
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial; background: #1a1a1a; color: #fff; margin: 0; padding: 20px; }
                .container { max-width: 1200px; margin: 0 auto; }
                .header { display: flex; justify-content: space-between; align-items: center; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
                .stat-card { background: #2d2d2d; padding: 20px; border-radius: 10px; text-align: center; }
                .stat-card h3 { margin: 0; color: #00a86b; }
                .stat-card p { font-size: 24px; margin: 10px 0; }
                table { width: 100%; background: #2d2d2d; border-radius: 10px; overflow: hidden; }
                th, td { padding: 12px; text-align: left; border-bottom: 1px solid #3d3d3d; }
                th { background: #00a86b; }
                .premium { color: gold; }
                .logout { background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Admin Dashboard</h1>
                    <a href="/admin/logout" class="logout">Logout</a>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Total Users</h3>
                        <p>{{ total }}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Premium Users</h3>
                        <p>{{ premium }}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Searches</h3>
                        <p>{{ searches }}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Reports</h3>
                        <p>{{ reports }}</p>
                    </div>
                    <div class="stat-card">
                        <h3>Referrals</h3>
                        <p>{{ referrals }}</p>
                    </div>
                </div>
                
                <h2>Recent Users</h2>
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Joined</th>
                        <th>Credits</th>
                        <th>Status</th>
                    </tr>
                    {% for user in recent %}
                    <tr>
                        <td>{{ user[0] }}</td>
                        <td>@{{ user[1] or 'N/A' }}</td>
                        <td>{{ user[2] }}</td>
                        <td>{{ user[3] }}</td>
                        <td class="{% if user[4] == 1 %}premium{% endif %}">
                            {% if user[4] == 1 %}PREMIUM{% else %}FREE{% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </body>
        </html>
    ''', total=total, premium=premium, searches=searches, reports=reports, referrals=referrals, recent=recent)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# ================= RUN BOT AND FLASK =================
def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def run_bot():
    app_bot = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("users", users_cmd))
    app_bot.add_handler(CommandHandler("stats", stats_cmd))
    app_bot.add_handler(CommandHandler("premium", premium_cmd))
    app_bot.add_handler(CommandHandler("removepremium", remove_premium_cmd))
    app_bot.add_handler(CommandHandler("addcredits", add_credits_cmd))
    app_bot.add_handler(CommandHandler("broadcast", broadcast))
    app_bot.add_handler(CommandHandler("topreferrers", top_referrers_cmd))
    app_bot.add_handler(CallbackQueryHandler(callbacks))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username))

    print("✅ Bot started! Press Ctrl+C to stop")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📊 Force channels: {FORCE_CHANNELS}")
    print(f"💰 Referral credits: {REFERRAL_CREDITS}")
    print(f"🌐 Admin panel: http://localhost:{PORT}/admin")
    app_bot.run_polling()

if __name__ == "__main__":
    # Run Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Run bot in main thread
    run_bot()

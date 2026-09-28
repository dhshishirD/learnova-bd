# -*- coding: utf-8 -*-
"""
Learnova BD - Telegram Multi-Group Automation & 30-Day Master Quiz Scheduler
Author: Learnova BD Automation
Description:
    Fully automated 24/7 Quiz Engine supporting:
    - 3 Daily Scheduled Sessions (☀️ 1:30 PM, 🌆 7:00 PM, 🌙 10:00 PM BST)
    - 3 Groups: Science (-1004432271474), Humanities (-1004394313271), Business (-1003919112457)
    - Main Discussion Group (-1001913753365)
    - 240 questions per group (720 total) mapped across 30 days starting 2026-09-28
    - Zero-miss state tracking & GitHub Actions / Cloud Cron support.
"""

import os
import sys
import json
import time
import random
import logging
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta, date

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# BOT CONFIGURATION
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8815514289:AAFqvAP8vwX_em6AYruKGRxCupggjI_Nf5I")
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Exact Telegram Chat IDs
CHATS = {
    "main_discussion": -1001913753365,
    "science": -1004432271474,
    "humanities": -1004394313271,
    "business": -1003919112457
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "quiz_schedule_state.json")
START_DATE = date(2026, 9, 28)

SESSION_MAP = {
    1: {"name": "সেশন ১ — কোর সাবজেক্টস (Core Subjects)", "time_str": "দুপুর ১:৩০", "subjects": [0, 1, 2]},
    2: {"name": "সেশন ২ — লাইফ সায়েন্স, জেনারেল ও ICT", "time_str": "সন্ধ্যা ৭:০০", "subjects": [3, 4, 5]},
    3: {"name": "সেশন ৩ — ল্যাঙ্গুয়েজ ও এলিট এডমিশন চ্যালেঞ্জ", "time_str": "রাত ১০:০০", "subjects": [6, 7]}
}

MOTIVATIONAL_POSTS = [
    {
        "tag": "🌙 আল-কুরআনের বাণী ও অনুপ্রেরণা",
        "text": "“মানুষ তাই পায়, যার জন্য সে চেষ্টা করে।” (সূরা আন-নাজম: ৩৯)",
        "tip": "💡 প্রতিটি পড়া যেন মুখস্থ নয়, কনসেপ্ট ক্লিয়ার করে হয়। আজকের পড়ার রুটিন কমপ্লিট করো!",
        "portal_cta": "🔥 ১০ মিনিট স্কুল যেকোনো কোর্সে স্পেশাল ফি-তে ভর্তি হতে: https://learnova-bd.vercel.app"
    },
    {
        "tag": "💼 সহিহ হাদিস ও কর্মপ্রেরণা",
        "text": "“নিশ্চয় আল্লাহ ভালোবাসেন যখন তোমাদের কেউ কোনো কাজ করে, সে যেন তা নিখুঁত ও নিষ্ঠার সাথে করে।” (বাইহাকী: ৪৯৩১)",
        "tip": "💡 ডেইলি কুইজ প্র্যাকটিস তোমার দুর্বলতাগুলো দূর করে বোর্ড ও এডমিশন পরীক্ষায় এগিয়ে রাখবে!",
        "portal_cta": "🎯 HSC 28 ও 27 এর সকল কোর্সের ভেরিফাইড অফার লিংক: https://learnova-bd.vercel.app"
    },
    {
        "tag": "⚡ ডেইলি স্টাডি হ্যাক",
        "text": "“The secret of getting ahead is getting started.” — Mark Twain",
        "tip": "💡 পোমোডোরো টেকনিক (২৫ মিনিট ফুল ফোকাস পড়া + ৫ মিনিট ব্রেক) দিয়ে আজকে ৩টি সেশন কমপ্লিট করো!",
        "portal_cta": "🌐 ১০ মিনিট স্কুল কোর্স ডিসকাউন্ট পোর্টাল: https://learnova-bd.vercel.app"
    }
]


def get_dhaka_now():
    """Returns current datetime in Bangladesh Standard Time (UTC+6)"""
    return datetime.now(timezone.utc) + timedelta(hours=6)


def get_current_day():
    """Calculates active day number from 2026-09-28 (1 to 30)"""
    dhaka_today = get_dhaka_now().date()
    delta = (dhaka_today - START_DATE).days + 1
    if delta < 1:
        return 1
    if delta > 30:
        return 30
    return delta


def load_master_banks():
    """Loads all 3 Master Quiz Banks from JSON"""
    banks = {"science": [], "humanities": [], "business": []}
    
    file_map = {
        "science": ["HSC_Science_Month1_240_Quiz_Master_Bank.json", os.path.join("HSC_Quiz_Banks_Month1", "Science", "HSC_Science_Month1_240_Quiz_Master_Bank.json")],
        "humanities": ["HSC_Humanities_Month1_240_Quiz_Master_Bank.json", os.path.join("HSC_Quiz_Banks_Month1", "Humanities", "HSC_Humanities_Month1_240_Quiz_Master_Bank.json")],
        "business": ["HSC_Business_Studies_Month1_240_Quiz_Master_Bank.json", os.path.join("HSC_Quiz_Banks_Month1", "Business_Studies", "HSC_Business_Studies_Month1_240_Quiz_Master_Bank.json")]
    }

    for group, paths in file_map.items():
        loaded = False
        for p in paths:
            full_p = os.path.join(BASE_DIR, p)
            if os.path.exists(full_p):
                try:
                    with open(full_p, "r", encoding="utf-8") as f:
                        banks[group] = json.load(f)
                    logger.info(f"Loaded {len(banks[group])} quizzes for {group} from {p}")
                    loaded = True
                    break
                except Exception as e:
                    logger.error(f"Error loading {full_p}: {e}")
        if not loaded:
            logger.warning(f"Could not load bank for {group}, using empty list.")
    return banks


MASTER_BANKS = load_master_banks()


def load_state():
    """Loads posted sessions state"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state):
    """Saves posted sessions state"""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def send_telegram_request(method, payload):
    """Sends a POST request to Telegram Bot API with error handling"""
    url = f"{API_BASE}/{method}"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            res_body = resp.read().decode('utf-8')
            return json.loads(res_body)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8', errors='ignore')
        logger.error(f"Telegram HTTPError ({method}): {e.code} - {err_msg}")
        return None
    except Exception as e:
        logger.error(f"Telegram Request Exception ({method}): {e}")
        return None


def clean_options(opts, correct_str):
    """
    Cleans options so each is <= 100 chars as required by Telegram.
    Returns cleaned options list and the correct 0-based index.
    """
    cleaned = []
    correct_idx = 0
    for i, opt in enumerate(opts):
        c_opt = opt.strip()
        if len(c_opt) > 98:
            c_opt = c_opt[:95] + "..."
        cleaned.append(c_opt)
        if opt.strip().startswith(correct_str[:3]) or opt.strip() == correct_str.strip():
            correct_idx = i
    return cleaned, correct_idx


def clean_explanation(exp):
    """Telegram explanation must not exceed 200 characters"""
    e = exp.strip()
    if len(e) > 196:
        e = e[:193] + "..."
    return e


def send_quiz_poll(chat_id, quiz_item, day_number):
    """Sends a native Telegram Quiz Poll"""
    q_text = f"[{quiz_item['subject']} | দিন {day_number}/৩০]\n{quiz_item['question']}"
    if len(q_text) > 295:
        q_text = q_text[:292] + "..."

    opts, correct_idx = clean_options(quiz_item["options"], quiz_item["correct"])
    exp = clean_explanation(quiz_item["explanation"])

    payload = {
        "chat_id": chat_id,
        "question": q_text,
        "options": opts,
        "is_anonymous": False,
        "type": "quiz",
        "correct_option_id": correct_idx,
        "explanation": exp,
        "explanation_parse_mode": "HTML"
    }

    res = send_telegram_request("sendPoll", payload)
    if res and res.get("ok"):
        logger.info(f"Quiz Q{quiz_item['id']} successfully sent to {chat_id}")
        return True
    return False


def post_session_quizzes(session_num, day_number=None, force=False):
    """
    Dispatches all quizzes for a given session and day across all groups.
    Updates state so it never double-posts unless force=True.
    """
    if day_number is None:
        day_number = get_current_day()

    dhaka_now = get_dhaka_now()
    date_key = dhaka_now.strftime("%Y-%m-%d")
    state_key = f"{date_key}_day{day_number}_session{session_num}"

    state = load_state()
    if state.get(state_key) and not force:
        logger.info(f"Session {session_num} for Day {day_number} ({date_key}) already completed. Skipping.")
        return True

    sess_info = SESSION_MAP.get(session_num)
    if not sess_info:
        logger.error(f"Invalid session number: {session_num}")
        return False

    logger.info(f"🚀 Triggering Day {day_number} | {sess_info['name']} ({sess_info['time_str']}) across all channels...")

    # 1. Post Session Announcement in Main Discussion Group
    announcement_text = (
        f"🔔 <b>HSC 2026/2027 ডেইলি লাইভ কুইজ এরিনা</b> 🎯\n\n"
        f"🗓️ <b>আজকের দিন:</b> দিন {day_number} / ৩০ ({dhaka_now.strftime('%d %B %Y')})\n"
        f"⏰ <b>সেশন:</b> {sess_info['name']}\n\n"
        f"গ্রুপভিত্তিক লাইভ পোল শুরু হয়েছে! প্রত্যেকে নিজের গ্রুপে অংশগ্রহণ করো:\n"
        f"🔬 <a href='https://t.me/tenminuteschoolC'>বিজ্ঞান বিভাগ গ্রুপ</a>\n"
        f"📚 <a href='https://t.me/tenminuteschoolC'>মানবিক বিভাগ গ্রুপ</a>\n"
        f"💼 <a href='https://t.me/tenminuteschoolC'>ব্যবসায় শিক্ষা গ্রুপ</a>\n\n"
        f"🌐 <b>ওয়েবসাইটে সরাসরি সবগুলো কুইজ প্র্যাকটিস করতে:</b>\n"
        f"👉 <a href='https://learnova-bd.vercel.app'>learnova-bd.vercel.app</a>"
    )
    send_telegram_request("sendMessage", {
        "chat_id": CHATS["main_discussion"],
        "text": announcement_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    })

    # 2. Post Group-wise Quizzes
    subject_indices = sess_info["subjects"]
    for group_key in ["science", "humanities", "business"]:
        bank = MASTER_BANKS.get(group_key, [])
        chat_id = CHATS.get(group_key)
        if not bank or not chat_id:
            logger.warning(f"No bank or chat ID for {group_key}")
            continue

        for sub_idx in subject_indices:
            q_idx = sub_idx * 30 + (day_number - 1)
            if q_idx < len(bank):
                quiz = bank[q_idx]
                send_quiz_poll(chat_id, quiz, day_number)
                time.sleep(2)

    # 3. Post a Random Mixed Quiz to Main Discussion
    mixed_bank = MASTER_BANKS.get("science", []) + MASTER_BANKS.get("humanities", []) + MASTER_BANKS.get("business", [])
    if mixed_bank:
        spotlight_quiz = random.choice(mixed_bank)
        send_quiz_poll(CHATS["main_discussion"], spotlight_quiz, day_number)

    # Mark as posted
    state[state_key] = {
        "timestamp": dhaka_now.isoformat(),
        "day": day_number,
        "session": session_num
    }
    save_state(state)
    logger.info(f"✅ Successfully completed Day {day_number} Session {session_num}!")
    return True


def auto_detect_and_run_session(day_number=None, force=False):
    """Automatically detects what session is due right now in BST and executes it"""
    dhaka_now = get_dhaka_now()
    hour = dhaka_now.hour
    minute = dhaka_now.minute
    time_float = hour + minute / 60.0

    if day_number is None:
        day_number = get_current_day()

    logger.info(f"Current Bangladesh Time: {dhaka_now.strftime('%Y-%m-%d %I:%M %p')} (Day {day_number})")

    # Determine session based on time
    # Session 1: 13:30 (1:30 PM) to 18:59
    # Session 2: 19:00 (7:00 PM) to 21:59
    # Session 3: 22:00 (10:00 PM) to 23:59
    # Early morning (< 13:30) can catch up previous day or await 13:30
    if 13.5 <= time_float < 19.0:
        session_to_run = 1
    elif 19.0 <= time_float < 22.0:
        session_to_run = 2
    elif time_float >= 22.0:
        session_to_run = 3
    else:
        # Before 1:30 PM
        session_to_run = 1

    return post_session_quizzes(session_to_run, day_number, force=force)


def run_continuous_daemon():
    """Runs a resilient local 24/7 background scheduler"""
    logger.info("Learnova Quiz Scheduler Daemon is running locally...")
    last_check_minute = -1

    while True:
        try:
            dhaka_now = get_dhaka_now()
            minute = dhaka_now.minute
            hour = dhaka_now.hour

            if minute != last_check_minute:
                last_check_minute = minute
                day = get_current_day()

                # Session 1: 13:30
                if hour == 13 and minute >= 30:
                    post_session_quizzes(1, day)
                # Session 2: 19:00
                elif hour == 19 and minute >= 0:
                    post_session_quizzes(2, day)
                # Session 3: 22:00
                elif hour == 22 and minute >= 0:
                    post_session_quizzes(3, day)

            time.sleep(20)
        except Exception as e:
            logger.error(f"Scheduler daemon error: {e}")
            time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Learnova 30-Day Master Quiz Scheduler")
    parser.add_argument("--session", choices=["1", "2", "3", "auto"], default="auto", help="Session to post (1, 2, 3, or auto)")
    parser.add_argument("--day", type=int, default=None, help="Specific day number (1-30)")
    parser.add_argument("--force", action="store_true", help="Force post even if already marked posted")
    parser.add_argument("--daemon", action="store_true", help="Run as continuous local background daemon")
    args = parser.parse_args()

    if args.daemon:
        run_continuous_daemon()
    elif args.session == "auto":
        auto_detect_and_run_session(day_number=args.day, force=args.force)
    else:
        post_session_quizzes(int(args.session), day_number=args.day, force=args.force)

import os
import requests
import threading
from bs4 import BeautifulSoup
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ---------- CONFIGURATION ----------
TOKEN = "8207041062:AAHWN5Bf2Yih5kld7n_8jAwAfonAzffRd2s"

# ---------- KEEP ALIVE ----------
server = Flask(__name__)
@server.route('/')
def home(): return "Bot is running 24/7!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

def keep_alive():
    threading.Thread(target=run_server).start()

# ---------- SCRAPING FUNCTIONS ----------

def get_board_result(url, roll, board_name):
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": url
        }
        
        # Mymensingh needs cookie initialization
        if board_name == "Mymensingh":
            session.get("https://www.mymensingheducationboard.gov.bd/resultmbh25/", headers=headers)
        
        payload = {"roll": roll, "regno": ""}
        if board_name == "Chattogram":
            payload = {"roll": roll, "button2": "Submit"}
            headers["Referer"] = "https://hscresult.bise-ctg.gov.bd/h_x_y_ctg25/individual/index.php"

        res = session.post(url, data=payload, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")

        # Data collection dictionary
        extracted_data = {}
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) == 4:
                extracted_data[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)
                extracted_data[cols[2].get_text(strip=True)] = cols[3].get_text(strip=True)
            elif len(cols) == 2:
                extracted_data[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)

        name = extracted_data.get("Name")
        if not name: return None

        # সাবজেক্ট লিস্ট প্রসেসিং
        subjects_list = []
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) == 2:
                c1, c2 = cols[0].get_text(strip=True), cols[1].get_text(strip=True)
                # ফিল্টার আউট মেনু আইটেমস
                if c1 and c2 and c1 not in ["Name", "Father's Name", "Mother's Name", "Result", "Institute", "Roll No", "GPA", "Group", "Reg. NO", "Board", "Session", "Type", "Subject", "Obtain Marks"]:
                    subjects_list.append(f"{c1} → {c2}")

        return {
            "name": name,
            "father": extracted_data.get("Father's Name", "N/A"),
            "mother": extracted_data.get("Mother's Name", "N/A"),
            "reg": extracted_data.get("Reg. NO") or extracted_data.get("Registration No") or "N/A",
            "group": extracted_data.get("Group", "N/A"),
            "result": extracted_data.get("Result", "N/A"),
            "gpa": extracted_data.get("GPA", ""),
            "inst": extracted_data.get("Institute", "N/A"),
            "board": board_name.upper(),
            "subjects": "\n".join(subjects_list) if subjects_list else "Details on website"
        }
    except: return None

# ---------- BOT LOGIC ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Mymensingh', 'Jessore'], ['Chattogram']]
    await update.message.reply_text(
        "👋 স্বাগতম! কোন বোর্ডের রেজাল্ট দেখতে চান?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_data = context.user_data

    if text in ['Mymensingh', 'Jessore', 'Chattogram']:
        user_data['board'] = text
        await update.message.reply_text(f"✅ আপনি {text} সিলেক্ট করেছেন। এবার Roll দিন:", reply_markup=ReplyKeyboardRemove())
        return

    if text.isdigit():
        board = user_data.get('board')
        if not board:
            await update.message.reply_text("⚠️ আগে বোর্ড সিলেক্ট করুন! /start চাপুন।")
            return

        wait_msg = await update.message.reply_text(f"⏳ {board} বোর্ডের রেজাল্ট আনা হচ্ছে...")
        
        url_map = {
            'Mymensingh': "https://www.mymensingheducationboard.gov.bd/resultmbh25/result.php",
            'Jessore': "https://www.jessoreboard.gov.bd/resultjbh25/result.php",
            'Chattogram': "https://hscresult.bise-ctg.gov.bd/h_x_y_ctg25/individual/result_mark_details.php"
        }
        
        res = get_board_result(url_map[board], text, board)

        if not res:
            await wait_msg.edit_text("❌ রেজাল্ট পাওয়া যায়নি! রোল নম্বরটি চেক করুন।")
        else:
            msg = (
                f"🧑‍🎓 STUDENT INFORMATION\n━━━━━━━━━━━━━━\n\n"
                f"👤 Name: {res['name']}\n"
                f"👨 Father: {res['father']}\n"
                f"👩 Mother: {res['mother']}\n\n"
                f"━━━━━━━━━━━━━━\n"
                f"📘 HSC RESULT 2025\n"
                f"━━━━━━━━━━━━━━\n\n"
                f"🆔 Roll No: {text}\n"
                f"📄 Registration No: {res['reg']}\n\n"
                f"🏫 Board: {res['board']}\n"
                f"📚 Group: {res['group']}\n\n"
                f"📊 Result: {res['result']}\n"
                f"{('⭐ GPA: ' + res['gpa']) if res['gpa'].strip() else ''}\n\n"
                f"🏫 Institute: {res['inst']}\n\n"
                f"📊 SUBJECTS\n━━━━━━━━━━━━━━\n{res['subjects']}"
            )
            await wait_msg.edit_text(msg)
        
        await update.message.reply_text("আবার দেখতে চাইলে বোর্ড সিলেক্ট করুন:", 
            reply_markup=ReplyKeyboardMarkup([['Mymensingh', 'Jessore'], ['Chattogram']], resize_keyboard=True))

if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 Bot Fix Updated!")
    app.run_polling()

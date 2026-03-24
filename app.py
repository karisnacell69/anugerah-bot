import asyncio
import threading
import uuid
import os
import requests

from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request, jsonify

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler
)

# ================= CONFIG =================
TOKEN = "8636518862:AAGZDQJMzlxQklGi4DfCXWN7N2WKr4IDMqU"
ADMIN_ID = 6806611251
WA_NUMBER = "6283195664588"

DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
WEBHOOK_URL = f"https://{DOMAIN}/webhook"
PORT = int(os.environ.get("PORT", 5000))

COMBINED_IMG = "combined_payment.jpg"

# ================= DATA =================
HARGA = {"17": 70000, "18": 75000, "19": 80000, "20": 85000}
ORDERS = {}

UMUR, JUMLAH, NAMA, ALAMAT = range(4)

# ================= WA FUNCTION =================
def kirim_wa(text):
    link = f"https://wa.me/{WA_NUMBER}?text={requests.utils.quote(text)}"
    print("📲 WA LINK:", link)
    return link

# ================= BUAT GAMBAR =================
def buat_gambar():
    logo = Image.open("logo.jpg").convert("RGB")
    qris = Image.open("qris.jpg").convert("RGB")

    logo = logo.resize((300, 300))
    qris = qris.resize((800, 500))

    canvas = Image.new("RGB", (800, 900), (240, 248, 255))
    draw = ImageDraw.Draw(canvas)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22
        )
    except:
        font = ImageFont.load_default()

    draw.text((400, 30), "ANUGERAH FARM - QRIS", fill="black", anchor="mm")

    canvas.paste(logo, (250, 80))
    canvas.paste(qris, (0, 400))

    canvas.save(COMBINED_IMG)

# ================= BOT =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🐔 17 Minggu", callback_data="17")],
        [InlineKeyboardButton("🐔 18 Minggu", callback_data="18")],
        [InlineKeyboardButton("🐔 19 Minggu", callback_data="19")],
        [InlineKeyboardButton("🐔 20 Minggu", callback_data="20")],
    ]

    await update.message.reply_text(
        "🐔 ANUGERAH FARM\n\nPilih umur ayam:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return UMUR

async def pilih_umur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    umur = q.data
    context.user_data["umur"] = umur
    context.user_data["harga"] = HARGA[umur]

    await q.message.reply_text("Masukkan jumlah:")
    return JUMLAH

async def jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jml = int(update.message.text)
    context.user_data["jumlah"] = jml

    total = jml * context.user_data["harga"]
    context.user_data["total"] = total

    await update.message.reply_text("Masukkan nama:")
    return NAMA

async def nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nama"] = update.message.text
    await update.message.reply_text("Masukkan alamat:")
    return ALAMAT

async def alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    order_id = str(uuid.uuid4())[:8]

    ORDERS[order_id] = {"data": data, "status": "PENDING"}

    pesan_wa = f"""
ORDER BARU MASUK

ID: {order_id}
Nama: {data['nama']}
Umur: {data['umur']} minggu
Jumlah: {data['jumlah']}
Alamat: {data['alamat']}
Total: Rp{data['total']}
"""

    wa_link = kirim_wa(pesan_wa)

    with open(COMBINED_IMG, "rb") as img:
        await update.message.reply_photo(
            photo=img,
            caption=f"Order ID: {order_id}\nTotal: Rp{data['total']}\n\nKlik WA:\n{wa_link}"
        )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=pesan_wa
    )

    return ConversationHandler.END

# ================= ADMIN =================
async def bukti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return

    oid = list(ORDERS.keys())[-1]

    keyboard = [[
        InlineKeyboardButton("✅ Lunas", callback_data=f"ok_{oid}"),
        InlineKeyboardButton("❌ Tolak", callback_data=f"no_{oid}")
    ]]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        reply_markup=InlineKeyboardMarkup(keyboard),
        caption=f"Bukti {oid}"
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    action, oid = q.data.split("_")
    ORDERS[oid]["status"] = "LUNAS" if action == "ok" else "DITOLAK"

    await q.edit_message_caption(caption=f"{oid} {ORDERS[oid]['status']}")

# ================= BOT SETUP =================
bot_app = None
loop = None

def start_loop():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def setup_bot():
    global bot_app
    bot_app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            UMUR: [CallbackQueryHandler(pilih_umur)],
            JUMLAH: [MessageHandler(filters.TEXT & ~filters.COMMAND, jumlah)],
            NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, nama)],
            ALAMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, alamat)],
        },
        fallbacks=[]
    )

    bot_app.add_handler(conv)
    bot_app.add_handler(MessageHandler(filters.PHOTO, bukti))
    bot_app.add_handler(CallbackQueryHandler(admin, pattern="^(ok|no)_"))

    await bot_app.initialize()
    await bot_app.start()

    await bot_app.bot.delete_webhook(drop_pending_updates=True)
    await bot_app.bot.set_webhook(WEBHOOK_URL)

    print("Webhook:", WEBHOOK_URL)

# ================= FLASK =================
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    update = Update.de_json(data, bot_app.bot)

    asyncio.run_coroutine_threadsafe(
        bot_app.process_update(update), loop
    )

    return "ok"

@app.route("/")
def home():
    return "BOT AKTIF"

@app.route("/api/orders")
def orders():
    return jsonify(ORDERS)

# ================= START =================
if __name__ == "__main__":
    buat_gambar()

    t = threading.Thread(target=start_loop, daemon=True)
    t.start()

    import time
    time.sleep(1)

    asyncio.run_coroutine_threadsafe(setup_bot(), loop)

    print("🚀 BOT LEVEL SULTAN AKTIF")
    app.run(host="0.0.0.0", port=PORT)

import requests
import uuid
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler
)

# ================= CONFIG =================
TOKEN = "8724925416:AAExcJfEJwQZG1n62WmzL602ZN7Iyp6nmyU"
ADMIN_ID = 6806611251

# 🔗 WEB KAMU
URL_WEB = "https://ayametelur909.great-site.net/api/order"

# ================= HARGA =================
HARGA = {
    "17": 70000,
    "18": 75000,
    "19": 80000,
    "20": 85000
}

# ================= DATABASE SEMENTARA =================
ORDERS = {}

# ================= STATE =================
UMUR, JUMLAH, NAMA, ALAMAT = range(4)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🐔 17 Minggu", callback_data="17")],
        [InlineKeyboardButton("🐔 18 Minggu", callback_data="18")],
        [InlineKeyboardButton("🔥 19 Minggu", callback_data="19")],
        [InlineKeyboardButton("🔥 20 Minggu", callback_data="20")]
    ]

    await update.message.reply_text(
        "🐔 *PILIH UMUR AYAM*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return UMUR

# ================= PILIH UMUR =================
async def pilih_umur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    umur = query.data
    context.user_data["umur"] = umur
    context.user_data["harga"] = HARGA[umur]

    await query.message.reply_text(
        f"✅ Pilih: {umur} minggu\n💰 Harga: Rp{HARGA[umur]}\n\nMasukkan jumlah:"
    )
    return JUMLAH

# ================= JUMLAH =================
async def jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jumlah = int(update.message.text)
    context.user_data["jumlah"] = jumlah

    total = jumlah * context.user_data["harga"]
    context.user_data["total"] = total

    await update.message.reply_text(
        f"""📊 *RINCIAN ORDER*

🐔 Umur: {context.user_data['umur']} minggu
📦 Jumlah: {jumlah}
💰 Harga: Rp{context.user_data['harga']}
━━━━━━━━━━━━━━
💵 Total: Rp{total}

📝 Masukkan nama:""",
        parse_mode="Markdown"
    )
    return NAMA

# ================= NAMA =================
async def nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nama"] = update.message.text
    await update.message.reply_text("📍 Masukkan alamat:")
    return ALAMAT

# ================= ALAMAT + ORDER + KIRIM WEB =================
async def alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["alamat"] = update.message.text
    data = context.user_data

    # ===== BUAT ORDER ID =====
    order_id = str(uuid.uuid4())[:8]

    ORDERS[order_id] = {
        "data": data,
        "status": "PENDING"
    }

    # ===== KIRIM KE WEB (ANTI ERROR) =====
    try:
        requests.post(
            URL_WEB,
            data={
                "order_id": order_id,
                "nama": data["nama"],
                "jumlah": data["jumlah"],
                "total": data["total"],
                "umur": data["umur"],
                "alamat": data["alamat"]
            },
            timeout=5
        )
        status_web = "✅ Server Web Terhubung"
    except Exception as e:
        print("Web Error:", e)
        status_web = "⚠️ Server Web Offline"

    pesan = f"""
🆔 Order ID: {order_id}

🐔 Umur: {data['umur']} minggu
📦 Jumlah: {data['jumlah']}
💰 Total: Rp{data['total']}

⏳ Status: PENDING
"""

    # ===== USER =====
    await update.message.reply_text(
        f"""💳 *PEMBAYARAN QRIS*

{pesan}

📸 Kirim bukti transfer di sini ya

{status_web}
""",
        parse_mode="Markdown"
    )

    # ===== ADMIN =====
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text="📥 ORDER BARU\n" + pesan,
        parse_mode="Markdown"
    )

    return ConversationHandler.END

# ================= BUKTI TRANSFER =================
async def bukti_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return

    if not ORDERS:
        return

    last_order_id = list(ORDERS.keys())[-1]
    file_id = update.message.photo[-1].file_id

    keyboard = [
        [
            InlineKeyboardButton("✅ Lunas", callback_data=f"approve_{last_order_id}"),
            InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{last_order_id}")
        ]
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=f"📸 Bukti Transfer\nOrder ID: {last_order_id}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("✅ Bukti terkirim, menunggu konfirmasi admin")

# ================= APPROVE ADMIN =================
async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    action, order_id = data.split("_")

    if order_id not in ORDERS:
        return

    if action == "approve":
        ORDERS[order_id]["status"] = "LUNAS"
        text = f"✅ Order {order_id} LUNAS"
    else:
        ORDERS[order_id]["status"] = "DITOLAK"
        text = f"❌ Order {order_id} DITOLAK"

    await query.edit_message_caption(caption=text)

# ================= CANCEL =================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Order dibatalkan")
    return ConversationHandler.END

# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        UMUR: [CallbackQueryHandler(pilih_umur)],
        JUMLAH: [MessageHandler(filters.TEXT & ~filters.COMMAND, jumlah)],
        NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, nama)],
        ALAMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, alamat)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.PHOTO, bukti_transfer))
app.add_handler(CallbackQueryHandler(handle_admin, pattern="^(approve|reject)_"))

print("🚀 BOT SULTAN FULL SYSTEM AKTIF")
app.run_polling()
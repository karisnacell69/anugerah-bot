import os
import logging
import requests
import uuid
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ================= CONFIG =================
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8636518862:AAGZDQJMzlxQklGi4DfCXWN7N2WKr4IDMqU")
ADMIN_ID = 6806611251

# 🔗 WEB
URL_WEB = "https://ayametelur909.great-site.net/api/order"

# ================= GAMBAR =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "logo.jpg")
QRIS_PATH = os.path.join(BASE_DIR, "qris.jpg")

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
        [InlineKeyboardButton("🐔 17 Minggu - Rp70.000", callback_data="17")],
        [InlineKeyboardButton("🐔 18 Minggu - Rp75.000", callback_data="18")],
        [InlineKeyboardButton("🔥 19 Minggu - Rp80.000", callback_data="19")],
        [InlineKeyboardButton("🔥 20 Minggu - Rp85.000", callback_data="20")]
    ]

    caption = (
        "🐔 *SELAMAT DATANG DI TOKO AYAM SULTAN!*\n\n"
        "Pilih umur ayam yang kamu inginkan:"
    )

    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as foto:
            await update.message.reply_photo(
                photo=foto,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(
            caption,
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
        f"✅ Pilihan: *{umur} minggu*\n"
        f"💰 Harga satuan: *Rp{HARGA[umur]:,}*\n\n"
        "📦 Masukkan jumlah yang dipesan:",
        parse_mode="Markdown"
    )
    return JUMLAH

# ================= JUMLAH =================
async def jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jml = int(update.message.text)
        if jml <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Masukkan angka yang valid (contoh: 10)")
        return JUMLAH

    context.user_data["jumlah"] = jml
    total = jml * context.user_data["harga"]
    context.user_data["total"] = total

    await update.message.reply_text(
        f"📊 *RINCIAN ORDER*\n\n"
        f"🐔 Umur: {context.user_data['umur']} minggu\n"
        f"📦 Jumlah: {jml} ekor\n"
        f"💰 Harga satuan: Rp{context.user_data['harga']:,}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💵 *Total: Rp{total:,}*\n\n"
        f"📝 Masukkan nama pemesan:",
        parse_mode="Markdown"
    )
    return NAMA

# ================= NAMA =================
async def nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nama"] = update.message.text
    await update.message.reply_text(
        "📍 Masukkan alamat pengiriman lengkap:"
    )
    return ALAMAT

# ================= ALAMAT + ORDER + KIRIM WEB =================
async def alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["alamat"] = update.message.text
    data = context.user_data

    order_id = str(uuid.uuid4())[:8].upper()

    ORDERS[order_id] = {
        "data": dict(data),
        "status": "PENDING"
    }

    # ===== KIRIM KE WEB =====
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
        status_web = "✅ Order tersimpan di server"
    except Exception as e:
        logger.warning("Web Error: %s", e)
        status_web = "⚠️ Server web offline (order tetap tercatat)"

    pesan_order = (
        f"🆔 *Order ID: {order_id}*\n\n"
        f"👤 Nama: {data['nama']}\n"
        f"🐔 Umur: {data['umur']} minggu\n"
        f"📦 Jumlah: {data['jumlah']} ekor\n"
        f"📍 Alamat: {data['alamat']}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💵 *Total: Rp{data['total']:,}*\n"
        f"⏳ Status: PENDING\n"
    )

    caption_qris = (
        f"💳 *PEMBAYARAN QRIS*\n\n"
        f"{pesan_order}\n"
        f"📸 Scan QRIS di atas lalu kirim bukti transfer di sini\n\n"
        f"{status_web}"
    )

    # ===== KIRIM QRIS KE USER =====
    if os.path.exists(QRIS_PATH):
        with open(QRIS_PATH, "rb") as qris:
            await update.message.reply_photo(
                photo=qris,
                caption=caption_qris,
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(caption_qris, parse_mode="Markdown")

    # ===== NOTIF KE ADMIN =====
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📥 *ORDER BARU MASUK!*\n\n{pesan_order}",
        parse_mode="Markdown"
    )

    return ConversationHandler.END

# ================= BUKTI TRANSFER =================
async def bukti_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return

    user_orders = [
        oid for oid, o in ORDERS.items()
        if o["status"] == "PENDING"
    ]

    if not user_orders:
        await update.message.reply_text("⚠️ Tidak ada order aktif yang ditemukan.")
        return

    last_order_id = user_orders[-1]
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
        caption=(
            f"📸 *Bukti Transfer Masuk*\n"
            f"🆔 Order ID: {last_order_id}\n"
            f"👤 Nama: {ORDERS[last_order_id]['data'].get('nama', '-')}\n"
            f"💵 Total: Rp{ORDERS[last_order_id]['data'].get('total', 0):,}"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "✅ Bukti transfer berhasil dikirim ke admin!\n"
        "Mohon tunggu konfirmasi dalam beberapa menit."
    )

# ================= ADMIN APPROVE / REJECT =================
async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_", 1)
    if len(parts) != 2:
        return

    action, order_id = parts

    if order_id not in ORDERS:
        await query.edit_message_caption(caption="⚠️ Order tidak ditemukan")
        return

    order = ORDERS[order_id]

    if action == "approve":
        order["status"] = "LUNAS"
        text = f"✅ *Order {order_id} - LUNAS*\n👤 {order['data'].get('nama', '-')}"
    else:
        order["status"] = "DITOLAK"
        text = f"❌ *Order {order_id} - DITOLAK*\n👤 {order['data'].get('nama', '-')}"

    await query.edit_message_caption(caption=text, parse_mode="Markdown")
    logger.info("Order %s updated to %s", order_id, order["status"])

# ================= CANCEL =================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Order dibatalkan.\nKetik /start untuk memulai lagi."
    )
    return ConversationHandler.END

# ================= STATUS =================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ORDERS:
        await update.message.reply_text("📭 Belum ada order.")
        return

    pesan = "📋 *DAFTAR ORDER:*\n\n"
    for oid, o in list(ORDERS.items())[-5:]:
        pesan += (
            f"🆔 {oid} | {o['data'].get('nama', '-')} | "
            f"Rp{o['data'].get('total', 0):,} | {o['status']}\n"
        )

    await update.message.reply_text(pesan, parse_mode="Markdown")

# ================= MAIN =================
def main():
    logger.info("🚀 BOT SULTAN FULL SYSTEM AKTIF")

    application = ApplicationBuilder().token(TOKEN).build()

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

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.PHOTO, bukti_transfer))
    application.add_handler(CallbackQueryHandler(handle_admin, pattern="^(approve|reject)_"))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

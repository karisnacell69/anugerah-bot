import requests
import uuid
import os
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# ================= CONFIG =================
TOKEN = "8636518862:AAGZDQJMzlxQklGi4DfCXWN7N2WKr4IDMqU"
ADMIN_ID = 6806611251

# 🔗 WEB ADMIN (panel lokal via proxy)
URL_WEB = "http://localhost:5000/api/order"

COMBINED_IMG = "combined_payment.jpg"

# ================= HARGA =================
HARGA = {"17": 70000, "18": 75000, "19": 80000, "20": 85000}

# ================= DATABASE SEMENTARA =================
ORDERS = {}

# ================= STATE =================
UMUR, JUMLAH, NAMA, ALAMAT = range(4)


# ================= BUAT GAMBAR GABUNGAN =================
def buat_combined_image():
    logo = Image.open("logo.jpg").convert("RGB")
    qris = Image.open("qris.jpg").convert("RGB")

    WIDTH = 800
    logo_size = int(WIDTH * 0.45)
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

    qris_ratio = qris.height / qris.width
    qris_h = int(WIDTH * qris_ratio)
    qris = qris.resize((WIDTH, qris_h), Image.LANCZOS)

    PAD = 16
    HEADER_H = 56
    total_h = HEADER_H + logo_size + PAD + qris_h + PAD

    canvas = Image.new("RGB", (WIDTH, total_h), (240, 248, 255))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, WIDTH, HEADER_H], fill=(30, 130, 210))

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22
        )
    except Exception:
        font = ImageFont.load_default()

    draw.text(
        (WIDTH // 2, HEADER_H // 2),
        "Anugerah Farm Store  —  Pembayaran QRIS",
        fill="white",
        font=font,
        anchor="mm",
    )

    logo_x = (WIDTH - logo_size) // 2
    canvas.paste(logo, (logo_x, HEADER_H))
    canvas.paste(qris, (0, HEADER_H + logo_size + PAD))

    canvas.save(COMBINED_IMG, quality=92)
    print(f"✅ Gambar gabungan dibuat: {canvas.size}")


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🐔 17 Minggu — Rp70.000/ekor", callback_data="17")],
        [InlineKeyboardButton("🐔 18 Minggu — Rp75.000/ekor", callback_data="18")],
        [InlineKeyboardButton("🔥 19 Minggu — Rp80.000/ekor", callback_data="19")],
        [InlineKeyboardButton("🔥 20 Minggu — Rp85.000/ekor", callback_data="20")],
    ]

    await update.message.reply_text(
        "🐔 *ANUGERAH FARM STORE*\n\nPilih umur ayam yang ingin dipesan:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
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
        f"✅ Umur: *{umur} minggu* | Harga: *Rp{HARGA[umur]:,}*\n\n📦 Masukkan jumlah ekor:",
        parse_mode="Markdown",
    )
    return JUMLAH


# ================= JUMLAH =================
async def jumlah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        jml = int(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ Masukkan angka saja, contoh: 10")
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
        f"💵 Total: *Rp{total:,}*\n\n"
        f"📝 Masukkan nama pemesan:",
        parse_mode="Markdown",
    )
    return NAMA


# ================= NAMA =================
async def nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nama"] = update.message.text
    await update.message.reply_text("📍 Masukkan alamat pengiriman:")
    return ALAMAT


# ================= ALAMAT + ORDER + KIRIM WEB =================
async def alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["alamat"] = update.message.text
    data = context.user_data

    order_id = str(uuid.uuid4())[:8].upper()

    ORDERS[order_id] = {
        "data": {
            "nama": data["nama"],
            "umur": data["umur"],
            "jumlah": data["jumlah"],
            "alamat": data["alamat"],
            "total": data["total"],
        },
        "status": "PENDING",
    }

    # Kirim ke web admin
    try:
        requests.post(
            URL_WEB,
            data={
                "order_id": order_id,
                "nama": data["nama"],
                "jumlah": data["jumlah"],
                "total": data["total"],
                "umur": data["umur"],
                "alamat": data["alamat"],
            },
            timeout=5,
        )
        status_web = "✅ Tercatat di admin panel"
    except Exception as e:
        print("Web Error:", e)
        status_web = "⚠️ Admin panel offline"

    ringkasan = (
        f"🆔 Order ID: `{order_id}`\n\n"
        f"👤 Nama: {data['nama']}\n"
        f"🐔 Umur: {data['umur']} minggu\n"
        f"📦 Jumlah: {data['jumlah']} ekor\n"
        f"📍 Alamat: {data['alamat']}\n"
        f"💵 Total: *Rp{data['total']:,}*\n"
        f"⏳ Status: PENDING\n"
        f"{status_web}"
    )

    # ===== KIRIM GAMBAR GABUNGAN KE USER =====
    with open(COMBINED_IMG, "rb") as img_file:
        await update.message.reply_photo(
            photo=img_file,
            caption=(
                f"💳 *PEMBAYARAN QRIS*\n\n"
                f"{ringkasan}\n\n"
                f"📸 Scan QR di atas lalu kirim *foto bukti transfer* di sini"
            ),
            parse_mode="Markdown",
        )

    # ===== KIRIM KE ADMIN =====
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📥 *ORDER BARU MASUK*\n\n{ringkasan}",
        parse_mode="Markdown",
    )

    return ConversationHandler.END


# ================= BUKTI TRANSFER =================
async def bukti_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return

    user_id = update.message.from_user.id
    user_name = update.message.from_user.full_name

    # Cari order terakhir milik user ini
    last_order_id = None
    for oid, order in reversed(list(ORDERS.items())):
        if order["status"] == "PENDING":
            last_order_id = oid
            break

    if not last_order_id:
        await update.message.reply_text("⚠️ Tidak ada order pending yang ditemukan.")
        return

    file_id = update.message.photo[-1].file_id

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Lunas", callback_data=f"approve_{last_order_id}_{user_id}"
            ),
            InlineKeyboardButton(
                "❌ Tolak", callback_data=f"reject_{last_order_id}_{user_id}"
            ),
        ]
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=(
            f"📸 *Bukti Transfer*\n🆔 Order ID: `{last_order_id}`\n👤 Dari: {user_name}"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

    await update.message.reply_text(
        "✅ Bukti transfer terkirim!\nMenunggu konfirmasi admin... 🕐"
    )


# ================= APPROVE/REJECT ADMIN =================
async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    action = parts[0]
    order_id = parts[1]
    user_id = int(parts[2]) if len(parts) > 2 else None

    if order_id not in ORDERS:
        await query.edit_message_caption(caption="⚠️ Order tidak ditemukan")
        return

    if action == "approve":
        ORDERS[order_id]["status"] = "LUNAS"
        caption = f"✅ Order `{order_id}` sudah *LUNAS*"
        user_msg = f"🎉 Pembayaran Order `{order_id}` *DIKONFIRMASI*!\nTerima kasih, pesanan segera diproses 🐔"
    else:
        ORDERS[order_id]["status"] = "DITOLAK"
        caption = f"❌ Order `{order_id}` *DITOLAK*"
        user_msg = f"❌ Pembayaran Order `{order_id}` *DITOLAK*.\nHubungi admin untuk info lebih lanjut."

    await query.edit_message_caption(caption=caption, parse_mode="Markdown")

    if user_id:
        try:
            await context.bot.send_message(
                chat_id=user_id, text=user_msg, parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Gagal kirim ke user: {e}")

    # Update web admin juga
    try:
        requests.get(
            f"http://localhost:5000/api/update/{order_id}/{ORDERS[order_id]['status']}",
            timeout=3,
        )
    except Exception:
        pass


# ================= CANCEL =================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Order dibatalkan. Ketik /start untuk mulai lagi."
    )
    return ConversationHandler.END


# ================= STATUS =================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ORDERS:
        await update.message.reply_text("📭 Belum ada order.")
        return
    lines = [f"🆔 `{oid}` — {o['status']}" for oid, o in list(ORDERS.items())[-5:]]
    await update.message.reply_text(
        "📋 *5 Order Terakhir:*\n\n" + "\n".join(lines), parse_mode="Markdown"
    )


# ================= MAIN =================
if __name__ == "__main__":
    buat_combined_image()

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
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.PHOTO, bukti_transfer))
    app.add_handler(CallbackQueryHandler(handle_admin, pattern=r"^(approve|reject)_"))

    print("🚀 BOT ANUGERAH FARM — AKTIF")
    app.run_polling()

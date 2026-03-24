import asyncio
import threading
import uuid
import os
import requests as req_lib

from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request, jsonify

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, ConversationHandler
)

# ===================== CONFIG =====================
TOKEN    = "8636518862:AAGZDQJMzlxQklGi4DfCXWN7N2WKr4IDMqU"
ADMIN_ID = 6806611251
DOMAIN   = os.environ.get("REPLIT_DEV_DOMAIN", "")
WEBHOOK_URL = f"https://{DOMAIN}/webhook"
COMBINED_IMG = "combined_payment.jpg"

# ===================== HARGA =====================
HARGA = {"17": 70000, "18": 75000, "19": 80000, "20": 85000}

# ===================== DATA SEMENTARA =====================
ORDERS = {}

# ===================== STATE =====================
UMUR, JUMLAH, NAMA, ALAMAT = range(4)

# ===================== GAMBAR GABUNGAN =====================
def buat_combined_image():
    logo = Image.open("logo.jpg").convert("RGB")
    qris = Image.open("qris.jpg").convert("RGB")
    WIDTH     = 800
    logo_size = int(WIDTH * 0.45)
    logo      = logo.resize((logo_size, logo_size), Image.LANCZOS)
    qris_h    = int(WIDTH * qris.height / qris.width)
    qris      = qris.resize((WIDTH, qris_h), Image.LANCZOS)
    PAD       = 16
    HEADER_H  = 56
    canvas    = Image.new("RGB", (WIDTH, HEADER_H + logo_size + PAD + qris_h + PAD), (240, 248, 255))
    draw      = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, WIDTH, HEADER_H], fill=(30, 130, 210))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
    draw.text((WIDTH // 2, HEADER_H // 2), "Anugerah Farm Store  —  Pembayaran QRIS",
              fill="white", font=font, anchor="mm")
    canvas.paste(logo, ((WIDTH - logo_size) // 2, HEADER_H))
    canvas.paste(qris, (0, HEADER_H + logo_size + PAD))
    canvas.save(COMBINED_IMG, quality=92)
    print(f"✅ Gambar gabungan dibuat: {canvas.size}")

# ===================== BOT HANDLERS =====================
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

async def pilih_umur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    umur = query.data
    context.user_data["umur"]  = umur
    context.user_data["harga"] = HARGA[umur]
    await query.message.reply_text(
        f"✅ Umur: *{umur} minggu* | Harga: *Rp{HARGA[umur]:,}*\n\n📦 Masukkan jumlah ekor:",
        parse_mode="Markdown",
    )
    return JUMLAH

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

async def nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nama"] = update.message.text
    await update.message.reply_text("📍 Masukkan alamat pengiriman:")
    return ALAMAT

async def alamat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["alamat"] = update.message.text
    data     = context.user_data
    order_id = str(uuid.uuid4())[:8].upper()

    ORDERS[order_id] = {
        "data": {
            "nama": data["nama"], "umur": data["umur"],
            "jumlah": data["jumlah"], "alamat": data["alamat"],
            "total": data["total"],
        },
        "status": "PENDING",
    }

    try:
        req_lib.post("http://localhost:5000/api/order", data={
            "order_id": order_id, "nama": data["nama"],
            "jumlah": data["jumlah"], "total": data["total"],
            "umur": data["umur"], "alamat": data["alamat"],
        }, timeout=5)
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

    with open(COMBINED_IMG, "rb") as img_file:
        await update.message.reply_photo(
            photo=img_file,
            caption=(
                f"💳 *PEMBAYARAN QRIS*\n\n{ringkasan}\n\n"
                f"📸 Scan QR di atas lalu kirim *foto bukti transfer* di sini"
            ),
            parse_mode="Markdown",
        )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📥 *ORDER BARU MASUK*\n\n{ringkasan}",
        parse_mode="Markdown",
    )
    return ConversationHandler.END

async def bukti_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return
    user_id   = update.message.from_user.id
    user_name = update.message.from_user.full_name
    last_order_id = None
    for oid, order in reversed(list(ORDERS.items())):
        if order["status"] == "PENDING":
            last_order_id = oid
            break
    if not last_order_id:
        await update.message.reply_text("⚠️ Tidak ada order pending yang ditemukan.")
        return
    file_id  = update.message.photo[-1].file_id
    keyboard = [[
        InlineKeyboardButton("✅ Lunas",  callback_data=f"approve_{last_order_id}_{user_id}"),
        InlineKeyboardButton("❌ Tolak",  callback_data=f"reject_{last_order_id}_{user_id}"),
    ]]
    await context.bot.send_photo(
        chat_id=ADMIN_ID, photo=file_id,
        caption=f"📸 *Bukti Transfer*\n🆔 Order ID: `{last_order_id}`\n👤 Dari: {user_name}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    await update.message.reply_text("✅ Bukti transfer terkirim!\nMenunggu konfirmasi admin... 🕐")

async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts    = query.data.split("_")
    action   = parts[0]
    order_id = parts[1]
    user_id  = int(parts[2]) if len(parts) > 2 else None
    if order_id not in ORDERS:
        await query.edit_message_caption(caption="⚠️ Order tidak ditemukan")
        return
    if action == "approve":
        ORDERS[order_id]["status"] = "LUNAS"
        caption  = f"✅ Order `{order_id}` sudah *LUNAS*"
        user_msg = f"🎉 Pembayaran Order `{order_id}` *DIKONFIRMASI*!\nTerima kasih, pesanan segera diproses 🐔"
    else:
        ORDERS[order_id]["status"] = "DITOLAK"
        caption  = f"❌ Order `{order_id}` *DITOLAK*"
        user_msg = f"❌ Pembayaran Order `{order_id}` *DITOLAK*.\nHubungi admin untuk info lebih lanjut."
    await query.edit_message_caption(caption=caption, parse_mode="Markdown")
    if user_id:
        try:
            await context.bot.send_message(chat_id=user_id, text=user_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Gagal kirim ke user: {e}")
    try:
        req_lib.get(f"http://localhost:5000/api/update/{order_id}/{ORDERS[order_id]['status']}", timeout=3)
    except Exception:
        pass

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Order dibatalkan. Ketik /start untuk mulai lagi.")
    return ConversationHandler.END

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ORDERS:
        await update.message.reply_text("📭 Belum ada order.")
        return
    lines = [f"🆔 `{oid}` — {o['status']}" for oid, o in list(ORDERS.items())[-5:]]
    await update.message.reply_text(
        "📋 *5 Order Terakhir:*\n\n" + "\n".join(lines), parse_mode="Markdown"
    )

# ===================== BOT APPLICATION (WEBHOOK MODE) =====================
bot_app  = None
bot_loop = None

def _start_bot_loop():
    global bot_loop
    bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(bot_loop)
    bot_loop.run_forever()

async def _setup_bot():
    global bot_app
    bot_app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            UMUR:   [CallbackQueryHandler(pilih_umur)],
            JUMLAH: [MessageHandler(filters.TEXT & ~filters.COMMAND, jumlah)],
            NAMA:   [MessageHandler(filters.TEXT & ~filters.COMMAND, nama)],
            ALAMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, alamat)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    bot_app.add_handler(conv)
    bot_app.add_handler(CommandHandler("status", status_cmd))
    bot_app.add_handler(MessageHandler(filters.PHOTO, bukti_transfer))
    bot_app.add_handler(CallbackQueryHandler(handle_admin, pattern=r"^(approve|reject)_"))

    await bot_app.initialize()
    await bot_app.start()

    # Register webhook with Telegram
    await bot_app.bot.delete_webhook(drop_pending_updates=True)
    result = await bot_app.bot.set_webhook(WEBHOOK_URL)
    if result:
        print(f"✅ Webhook aktif: {WEBHOOK_URL}")
    else:
        print(f"❌ Webhook GAGAL didaftarkan")

# ===================== FLASK APP =====================
flask_app = Flask(__name__)

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data or bot_app is None:
        return "Bad Request", 400
    update = Update.de_json(data, bot_app.bot)
    future = asyncio.run_coroutine_threadsafe(bot_app.process_update(update), bot_loop)
    try:
        future.result(timeout=10)
    except Exception as e:
        print(f"Webhook error: {e}")
    return "ok", 200

@flask_app.route("/api/order", methods=["POST"])
def add_order():
    data     = request.form.to_dict()
    order_id = data.get("order_id")
    ORDERS[order_id] = {"data": data, "status": "PENDING"}
    return jsonify({"status": "ok"})

@flask_app.route("/api/orders")
def get_orders():
    return jsonify(ORDERS)

@flask_app.route("/api/update/<order_id>/<status>")
def update_status(order_id, status):
    if order_id in ORDERS:
        ORDERS[order_id]["status"] = status.upper()
    return jsonify({"status": "updated"})

@flask_app.route("/webhook/info")
def webhook_info():
    return jsonify({"webhook_url": WEBHOOK_URL, "active": bot_app is not None})

@flask_app.route("/")
def index():
    return """<!DOCTYPE html>
<html>
<head>
    <title>Admin Panel - Anugerah Farm Store</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: sans-serif; background: #0f172a; color: #fff; padding: 16px; }
        h2 { text-align: center; padding: 16px 0; font-size: 20px; color: #38bdf8; }
        .webhook-box {
            background: #1e3a5f; border: 1px solid #38bdf8; border-radius: 8px;
            padding: 12px 14px; margin: 10px 0; font-size: 12px; word-break: break-all;
        }
        .webhook-box span { color: #7dd3fc; }
        .badge-ok { display:inline-block; background:#22c55e; color:#fff; padding:2px 8px; border-radius:10px; font-size:11px; }
        .card {
            background: #1e293b; padding: 14px; margin: 10px 0;
            border-radius: 10px; border-left: 4px solid #38bdf8;
        }
        .card p { margin: 4px 0; font-size: 14px; }
        .badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:bold; margin-top:6px; }
        .PENDING  { background:#f59e0b; color:#000; }
        .LUNAS    { background:#22c55e; color:#fff; }
        .DITOLAK  { background:#ef4444; color:#fff; }
        .actions { margin-top:10px; display:flex; gap:8px; }
        button { flex:1; padding:8px; border:none; border-radius:6px; cursor:pointer; font-size:13px; font-weight:bold; }
        .ok { background:#22c55e; color:#fff; }
        .no { background:#ef4444; color:#fff; }
        #empty { text-align:center; color:#64748b; margin-top:40px; }
    </style>
</head>
<body>
<h2>📊 Admin Panel — Anugerah Farm Store</h2>
<div class="webhook-box">
    🔗 Webhook: <span id="wh-url">memuat...</span> <span class="badge-ok">AKTIF</span>
</div>
<div id="orders"><p id="empty">⏳ Memuat data...</p></div>

<script>
fetch('/webhook/info').then(r=>r.json()).then(d=>{
    document.getElementById('wh-url').textContent = d.webhook_url;
});

async function loadOrders() {
    const res = await fetch('/admin/api/orders');
    const data = await res.json();
    const keys = Object.keys(data);
    const container = document.getElementById('orders');
    if (keys.length === 0) {
        container.innerHTML = '<p id="empty">📭 Belum ada order masuk.</p>';
        return;
    }
    container.innerHTML = keys.reverse().map(id => {
        const o = data[id];
        return `
        <div class="card">
            <p><b>🆔 Order ID:</b> ${id}</p>
            <p>👤 <b>Nama:</b> ${o.data.nama}</p>
            <p>🐔 <b>Umur:</b> ${o.data.umur} minggu</p>
            <p>📦 <b>Jumlah:</b> ${o.data.jumlah} ekor</p>
            <p>📍 <b>Alamat:</b> ${o.data.alamat}</p>
            <p>💰 <b>Total:</b> Rp${Number(o.data.total).toLocaleString('id-ID')}</p>
            <span class="badge ${o.status}">${o.status}</span>
            <div class="actions">
                <button class="ok" onclick="update('${id}','lunas')">✅ Lunas</button>
                <button class="no" onclick="update('${id}','ditolak')">❌ Tolak</button>
            </div>
        </div>`;
    }).join('');
}

async function update(id, status) {
    await fetch('/admin/api/update/' + id + '/' + status);
    loadOrders();
}

loadOrders();
setInterval(loadOrders, 3000);
</script>
</body>
</html>"""

# ===================== STARTUP =====================
if __name__ == "__main__":
    buat_combined_image()

    # Start background asyncio loop
    t = threading.Thread(target=_start_bot_loop, daemon=True)
    t.start()
    import time; time.sleep(0.5)

    # Initialize bot in background loop and register webhook
    future = asyncio.run_coroutine_threadsafe(_setup_bot(), bot_loop)
    future.result(timeout=30)

    print(f"🚀 SERVER + WEBHOOK AKTIF")
    print(f"🔗 Webhook URL: {WEBHOOK_URL}")
    flask_app.run(host="0.0.0.0", port=5000)

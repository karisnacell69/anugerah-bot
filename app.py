from flask import Flask, request, jsonify

app = Flask(__name__)

# ================= DATABASE SEMENTARA =================
ORDERS = {}

# ================= API TAMBAH ORDER =================
@app.route("/admin/api/order", methods=["POST"])
def add_order():
    data = request.form.to_dict()
    order_id = data.get("order_id")
    ORDERS[order_id] = {
        "data": data,
        "status": "PENDING"
    }
    return jsonify({"status": "ok"})

# ================= API GET SEMUA ORDER =================
@app.route("/admin/api/orders")
def get_orders():
    return jsonify(ORDERS)

# ================= UPDATE STATUS =================
@app.route("/admin/api/update/<order_id>/<status>")
def update_status(order_id, status):
    if order_id in ORDERS:
        ORDERS[order_id]["status"] = status.upper()
    return jsonify({"status": "updated"})

# ================= WEB ADMIN =================
@app.route("/admin")
@app.route("/admin/")
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
        .card {
            background: #1e293b;
            padding: 14px;
            margin: 10px 0;
            border-radius: 10px;
            border-left: 4px solid #38bdf8;
        }
        .card p { margin: 4px 0; font-size: 14px; }
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-top: 6px;
        }
        .PENDING  { background: #f59e0b; color: #000; }
        .LUNAS    { background: #22c55e; color: #fff; }
        .DITOLAK  { background: #ef4444; color: #fff; }
        .actions { margin-top: 10px; display: flex; gap: 8px; }
        button {
            flex: 1;
            padding: 8px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: bold;
        }
        .ok { background: #22c55e; color: #fff; }
        .no { background: #ef4444; color: #fff; }
        #empty { text-align: center; color: #64748b; margin-top: 40px; }
    </style>
</head>
<body>
<h2>📊 Admin Panel — Anugerah Farm Store</h2>
<div id="orders"><p id="empty">⏳ Memuat data...</p></div>

<script>
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
            <span class="badge ${o.status}">⏳ ${o.status}</span>
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

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

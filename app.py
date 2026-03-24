from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# ================= DATABASE SEMENTARA =================
ORDERS = {}

# ================= API TAMBAH ORDER =================
@app.route("/api/order", methods=["POST"])
def add_order():
    data = request.form.to_dict()

    order_id = data.get("order_id")

    ORDERS[order_id] = {
        "data": data,
        "status": "PENDING"
    }

    return jsonify({"status": "ok"})

# ================= API GET SEMUA ORDER =================
@app.route("/api/orders")
def get_orders():
    return jsonify(ORDERS)

# ================= UPDATE STATUS =================
@app.route("/api/update/<order_id>/<status>")
def update_status(order_id, status):
    if order_id in ORDERS:
        ORDERS[order_id]["status"] = status.upper()
    return jsonify({"status": "updated"})

# ================= WEB ADMIN =================
@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ADMIN PANEL SULTAN</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: sans-serif; background:#0f172a; color:#fff; }
            .card {
                background:#1e293b;
                padding:15px;
                margin:10px;
                border-radius:10px;
            }
            button {
                padding:8px;
                margin:5px;
                border:none;
                border-radius:5px;
                cursor:pointer;
            }
            .ok { background:#22c55e; color:#fff; }
            .no { background:#ef4444; color:#fff; }
        </style>
    </head>
    <body>

    <h2>📊 ADMIN PANEL ORDER</h2>
    <div id="orders">Loading...</div>

    <script>
    async function loadOrders(){
        let res = await fetch('/api/orders')
        let data = await res.json()

        let html = ''

        for(let id in data){
            let o = data[id]

            html += `
            <div class="card">
                <b>🆔 ID:</b> ${id}<br>
                👤 Nama: ${o.data.nama}<br>
                📦 Jumlah: ${o.data.jumlah}<br>
                🐔 Umur: ${o.data.umur}<br>
                💰 Total: Rp${o.data.total}<br>
                📍 Alamat: ${o.data.alamat}<br>
                ⏳ Status: ${o.status}<br>

                <button class="ok" onclick="update('${id}','lunas')">✅ Lunas</button>
                <button class="no" onclick="update('${id}','ditolak')">❌ Tolak</button>
            </div>`
        }

        document.getElementById("orders").innerHTML = html
    }

    async function update(id, status){
        await fetch(`/api/update/${id}/${status}`)
        loadOrders()
    }

    loadOrders()
    setInterval(loadOrders, 3000)
    </script>

    </body>
    </html>
    """

# ================= RUN =================
app.run(host="0.0.0.0", port=5000)
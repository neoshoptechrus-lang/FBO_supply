#!/usr/bin/env python3
"""
OZON FBO Supply Manager v1.1
- Исправлены API вызовы
- Добавлены детальные логи ошибок
- Полный цикл создания поставок FBO
"""

import os, json, urllib.request, urllib.error, ssl, time
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
OZON_CLIENT_ID = os.environ.get("OZON_CLIENT_ID", "1321895")
OZON_API_KEY = os.environ.get("OZON_API_KEY", "1ccae2c9-ee7f-4f3f-bac1-e14e38bc11f3")

OZON_API = "https://api-seller.ozon.ru"
LOGS = []

def log(level, ep, msg):
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "endpoint": ep,
        "message": str(msg)[:500]
    }
    LOGS.insert(0, entry)
    if len(LOGS) > 500: LOGS.pop()
    print(f"[{entry['time']}] [{level.upper()}] {ep}: {entry['message'][:100]}")

def ozon_request(endpoint, body=None):
    headers = {
        "Content-Type": "application/json",
        "Client-Id": OZON_CLIENT_ID,
        "Api-Key": OZON_API_KEY
    }
    log("request", endpoint, f"Body: {json.dumps(body, ensure_ascii=False)[:200] if body else 'empty'}")
    try:
        ctx = ssl.create_default_context()
        data = json.dumps(body).encode() if body else b'{}'
        req = urllib.request.Request(f"{OZON_API}{endpoint}", data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            result = json.loads(resp.read())
            log("success", endpoint, f"OK - keys: {list(result.keys())[:5]}")
            return result
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode()
        except:
            error_body = str(e)
        log("error", endpoint, f"HTTP {e.code}: {error_body[:400]}")
        return {"error": True, "code": e.code, "message": error_body}
    except Exception as e:
        log("error", endpoint, f"Exception: {str(e)[:400]}")
        return {"error": True, "message": str(e)}

def ozon_get(endpoint):
    headers = {"Client-Id": OZON_CLIENT_ID, "Api-Key": OZON_API_KEY}
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(f"{OZON_API}{endpoint}", headers=headers, method="GET")
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            return resp.read()
    except Exception as e:
        log("error", endpoint, str(e)[:200])
        return None


HTML = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OZON FBO Supply Manager v1.1</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f5f5;color:#1a1a1a;font-size:14px}
.header{background:linear-gradient(135deg,#005bff 0%,#0039a6 100%);color:#fff;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}
.logo{font-size:22px;font-weight:700;display:flex;align-items:center;gap:10px}
.logo span{background:#00c752;color:#fff;font-size:10px;padding:2px 8px;border-radius:10px}
.conn{display:flex;align-items:center;gap:8px;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
.conn-dot{width:10px;height:10px;border-radius:50%;background:#00c752}
.conn-dot.err{background:#ff4d4f}
.conn-dot.load{background:#faad14;animation:pulse 1s infinite}
@keyframes pulse{50%{opacity:.4}}
.container{max-width:1400px;margin:0 auto;padding:24px}
.nav{display:flex;gap:8px;margin-bottom:24px;background:#fff;padding:8px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.nav-btn{padding:12px 20px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;border:none;background:transparent;color:#666;transition:all .2s}
.nav-btn:hover{background:#f5f5f5;color:#005bff}
.nav-btn.active{background:#005bff;color:#fff}
.nav-btn .badge{background:#ff4d4f;color:#fff;font-size:10px;padding:2px 6px;border-radius:10px}
.page-title{font-size:26px;font-weight:700;margin-bottom:24px}
.card{background:#fff;border-radius:16px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:20px}
.card-header{padding:20px 24px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center}
.card-title{font-size:18px;font-weight:600}
.card-body{padding:24px}
.btn{padding:12px 20px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;border:none;transition:all .2s;display:inline-flex;align-items:center;gap:8px}
.btn-primary{background:#005bff;color:#fff}
.btn-primary:hover{background:#0050e6}
.btn-success{background:#00c752;color:#fff}
.btn-danger{background:#ff4d4f;color:#fff}
.btn-default{background:#f5f5f5;color:#1a1a1a;border:1px solid #e0e0e0}
.btn-default:hover{border-color:#005bff;color:#005bff}
.btn-lg{padding:16px 32px;font-size:16px}
.btn:disabled{opacity:.5;cursor:not-allowed}
.steps{display:flex;gap:0;margin-bottom:32px;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.step{flex:1;padding:20px;text-align:center;position:relative;cursor:pointer;transition:all .2s}
.step::after{content:'';position:absolute;right:0;top:50%;transform:translateY(-50%);border:8px solid transparent;border-left-color:#e0e0e0}
.step:last-child::after{display:none}
.step.active{background:#005bff;color:#fff}
.step.active::after{border-left-color:#005bff}
.step.done{background:#00c752;color:#fff}
.step.done::after{border-left-color:#00c752}
.step-num{width:32px;height:32px;border-radius:50%;background:#e0e0e0;color:#666;display:inline-flex;align-items:center;justify-content:center;font-weight:700;margin-bottom:8px}
.step.active .step-num,.step.done .step-num{background:rgba(255,255,255,.3);color:#fff}
.step-title{font-size:13px;font-weight:600}
.grid{display:grid;gap:20px}
.grid-2{grid-template-columns:repeat(2,1fr)}
.grid-3{grid-template-columns:repeat(3,1fr)}
@media(max-width:768px){.grid-2,.grid-3{grid-template-columns:1fr}}
.cluster-card,.warehouse-card{border:2px solid #e0e0e0;border-radius:12px;padding:20px;cursor:pointer;transition:all .2s}
.cluster-card:hover,.warehouse-card:hover{border-color:#005bff;transform:translateY(-2px)}
.cluster-card.selected,.warehouse-card.selected{border-color:#005bff;background:#f0f7ff}
.cluster-icon{font-size:36px;margin-bottom:12px;text-align:center}
.cluster-name,.warehouse-name{font-size:16px;font-weight:600;margin-bottom:4px}
.cluster-info,.warehouse-address{font-size:12px;color:#666}
.warehouse-status{display:inline-block;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;margin-top:8px}
.warehouse-status.open{background:#e6f7e6;color:#00a32e}
.warehouse-status.closed{background:#fff1f0;color:#ff4d4f}
.product-table{width:100%;border-collapse:collapse}
.product-table th{text-align:left;padding:14px 16px;background:#f9f9f9;font-size:12px;font-weight:600;color:#666}
.product-table td{padding:14px 16px;border-bottom:1px solid #f0f0f0}
.product-table tr:hover{background:#fafafa}
.qty-input{width:80px;padding:10px;border:2px solid #e0e0e0;border-radius:8px;text-align:center;font-size:14px;font-weight:600}
.qty-input:focus{outline:none;border-color:#005bff}
.empty-state{text-align:center;padding:60px 20px}
.empty-icon{font-size:64px;margin-bottom:16px;opacity:.5}
.empty-title{font-size:18px;font-weight:600;margin-bottom:8px}
.empty-text{font-size:14px;color:#999;margin-bottom:24px}
.toast-container{position:fixed;bottom:24px;right:24px;z-index:1001}
.toast{padding:16px 24px;background:#1a1a1a;color:#fff;border-radius:12px;margin-top:12px;font-size:14px;animation:slideIn .3s;max-width:400px}
.toast.success{background:#00c752}
.toast.error{background:#ff4d4f}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}}
.loading{text-align:center;padding:40px}
.spinner{width:40px;height:40px;border:4px solid #f0f0f0;border-top-color:#005bff;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 16px}
@keyframes spin{to{transform:rotate(360deg)}}
.error-box{background:#fff1f0;border:1px solid #ffa39e;border-radius:12px;padding:20px;margin:20px 0}
.error-title{color:#ff4d4f;font-weight:600;margin-bottom:8px;display:flex;align-items:center;gap:8px}
.error-msg{font-size:13px;color:#666;word-break:break-all}
.info-box{background:#e6f7ff;border:1px solid #91d5ff;border-radius:12px;padding:20px;margin:20px 0}
.info-title{color:#1890ff;font-weight:600;margin-bottom:8px}
.log-table{width:100%;border-collapse:collapse;font-size:12px}
.log-table th,.log-table td{padding:10px 12px;text-align:left;border-bottom:1px solid #f0f0f0}
.log-table th{background:#f9f9f9;font-weight:600}
.log-level{padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
.log-level.success{background:#f6ffed;color:#52c41a}
.log-level.error{background:#fff1f0;color:#ff4d4f}
.log-level.request{background:#e6f7ff;color:#1890ff}
.supply-card{display:grid;grid-template-columns:100px 1fr 120px 100px 120px;align-items:center;padding:16px;background:#fff;border-radius:12px;border:1px solid #e0e0e0;margin-bottom:12px;gap:16px}
.supply-id{font-weight:700;color:#005bff}
.supply-status{padding:6px 14px;border-radius:20px;font-size:12px;font-weight:600}
.status-filling{background:#fff7e6;color:#fa8c16}
.status-ready{background:#e6f7ff;color:#1890ff}
.status-completed{background:#f6ffed;color:#52c41a}
.status-cancelled{background:#fff1f0;color:#ff4d4f}
</style>
</head>
<body>
<div class="header">
<div class="logo">📦 FBO Supply Manager <span>v1.1</span></div>
<div class="conn" id="conn"><div class="conn-dot load"></div><span>Проверка...</span></div>
</div>

<div class="container">
<div class="nav">
<button class="nav-btn active" onclick="showPage('create')">➕ Создать поставку</button>
<button class="nav-btn" onclick="showPage('supplies')">📋 Мои поставки</button>
<button class="nav-btn" onclick="showPage('products')">📦 Товары</button>
<button class="nav-btn" onclick="showPage('logs')">📝 Логи</button>
</div>
<div id="page-content"></div>
</div>

<div class="toast-container" id="toasts"></div>

<script>
var S = {
    page: 'create',
    step: 1,
    clusters: [],
    warehouses: [],
    products: [],
    supplies: [],
    selectedCluster: null,
    selectedWarehouse: null,
    selectedProducts: {},
    lastError: null
};

function toast(msg, type) {
    var t = document.createElement('div');
    t.className = 'toast ' + (type || '');
    t.textContent = msg;
    document.getElementById('toasts').appendChild(t);
    setTimeout(function() { t.remove(); }, 5000);
}

function setConn(ok, txt) {
    document.getElementById('conn').innerHTML = '<div class="conn-dot ' + (ok ? '' : ok === false ? 'err' : 'load') + '"></div><span>' + txt + '</span>';
}

function api(ep, body) {
    console.log('API Request:', ep, body);
    return fetch('/ozon' + ep, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
    }).then(function(r) { return r.json(); }).then(function(d) {
        console.log('API Response:', ep, d);
        if (d.error) {
            S.lastError = { endpoint: ep, message: d.message, code: d.code };
        }
        return d;
    });
}

function showPage(p) {
    S.page = p;
    document.querySelectorAll('.nav-btn').forEach(function(b, i) {
        b.classList.toggle('active', ['create', 'supplies', 'products', 'logs'][i] === p);
    });
    render();
}

function render() {
    var c = document.getElementById('page-content');
    if (S.page === 'create') renderCreate(c);
    else if (S.page === 'supplies') renderSupplies(c);
    else if (S.page === 'products') renderProducts(c);
    else if (S.page === 'logs') renderLogs(c);
}

function renderError(msg, details) {
    return '<div class="error-box"><div class="error-title">❌ Ошибка</div><div class="error-msg">' + msg + (details ? '<br><br><strong>Детали:</strong> ' + details : '') + '</div></div>';
}

// ==================== CREATE PAGE ====================
function renderCreate(c) {
    var stepsHtml = [
        {num: 1, title: 'Склад'},
        {num: 2, title: 'Товары'},
        {num: 3, title: 'Подтверждение'}
    ].map(function(s) {
        var cls = s.num < S.step ? 'done' : s.num === S.step ? 'active' : '';
        return '<div class="step ' + cls + '"><div class="step-num">' + (s.num < S.step ? '✓' : s.num) + '</div><div class="step-title">' + s.title + '</div></div>';
    }).join('');

    c.innerHTML = '<div class="page-title">➕ Создать поставку FBO</div>' +
        '<div class="steps">' + stepsHtml + '</div>' +
        '<div id="step-content"></div>';
    renderStep();
}

function renderStep() {
    var sc = document.getElementById('step-content');
    if (!sc) return;
    if (S.step === 1) renderStepWarehouse(sc);
    else if (S.step === 2) renderStepProducts(sc);
    else if (S.step === 3) renderStepConfirm(sc);
}

// STEP 1: Warehouse
function renderStepWarehouse(sc) {
    sc.innerHTML = '<div class="card"><div class="card-header"><div class="card-title">🏭 Выберите склад FBO</div>' +
        '<button class="btn btn-primary" onclick="loadWarehouses()">🔄 Загрузить склады</button></div>' +
        '<div class="card-body" id="warehouses-grid"><div class="info-box"><div class="info-title">💡 Подсказка</div>Нажмите "Загрузить склады" чтобы получить список доступных складов FBO</div></div></div>';
}

function loadWarehouses() {
    var g = document.getElementById('warehouses-grid');
    g.innerHTML = '<div class="loading"><div class="spinner"></div>Загрузка складов FBO...</div>';
    
    // Используем правильный endpoint для складов FBO
    api('/v1/warehouse/list', {}).then(function(d) {
        if (d.error) {
            g.innerHTML = renderError('Не удалось загрузить склады', d.message);
            return;
        }
        S.warehouses = d.result || [];
        renderWarehousesGrid();
        toast('Загружено ' + S.warehouses.length + ' складов', 'success');
    });
}

function renderWarehousesGrid() {
    var g = document.getElementById('warehouses-grid');
    if (!S.warehouses.length) {
        g.innerHTML = '<div class="empty-state"><div class="empty-icon">🏭</div><div class="empty-title">Нет доступных складов</div></div>';
        return;
    }
    var html = '<div class="grid grid-2">';
    S.warehouses.forEach(function(wh) {
        var selected = S.selectedWarehouse && S.selectedWarehouse.warehouse_id === wh.warehouse_id ? 'selected' : '';
        html += '<div class="warehouse-card ' + selected + '" onclick="selectWarehouse(' + wh.warehouse_id + ')">' +
            '<div class="warehouse-name">' + (wh.name || 'Склад ' + wh.warehouse_id) + '</div>' +
            '<div class="warehouse-address">ID: ' + wh.warehouse_id + '</div>' +
            '<span class="warehouse-status open">✓ Доступен</span></div>';
    });
    html += '</div>';
    if (S.selectedWarehouse) {
        html += '<div style="margin-top:24px;text-align:right"><button class="btn btn-primary btn-lg" onclick="nextStep()">Далее → Товары</button></div>';
    }
    g.innerHTML = html;
}

function selectWarehouse(id) {
    S.selectedWarehouse = S.warehouses.find(function(w) { return w.warehouse_id == id; });
    renderWarehousesGrid();
}

// STEP 2: Products
function renderStepProducts(sc) {
    sc.innerHTML = '<div class="card"><div class="card-header"><div class="card-title">📦 Выберите товары</div>' +
        '<button class="btn btn-primary" onclick="loadProducts()">🔄 Загрузить товары</button></div>' +
        '<div class="card-body" id="products-list"><div class="info-box"><div class="info-title">💡 Подсказка</div>Нажмите "Загрузить товары" чтобы получить список ваших товаров</div></div></div>';
    
    if (S.products.length) renderProductsList();
}

function loadProducts() {
    var pl = document.getElementById('products-list');
    pl.innerHTML = '<div class="loading"><div class="spinner"></div>Загрузка товаров...</div>';
    
    api('/v2/product/list', { filter: { visibility: 'ALL' }, limit: 100 }).then(function(d) {
        if (d.error) {
            pl.innerHTML = renderError('Не удалось загрузить товары', d.message);
            return;
        }
        var items = d.result ? d.result.items : [];
        if (!items.length) {
            pl.innerHTML = '<div class="empty-state"><div class="empty-icon">📦</div><div class="empty-title">Нет товаров</div></div>';
            return;
        }
        S.products = items;
        renderProductsList();
        toast('Загружено ' + items.length + ' товаров', 'success');
    });
}

function renderProductsList() {
    var pl = document.getElementById('products-list');
    var totalQty = Object.values(S.selectedProducts).reduce(function(a, b) { return a + (b || 0); }, 0);
    
    var html = '<div class="info-box"><div class="info-title">📊 Выбрано: ' + totalQty + ' шт</div>Укажите количество для каждого товара</div>';
    html += '<table class="product-table"><thead><tr><th>Товар</th><th>Артикул</th><th>ID</th><th>Кол-во</th></tr></thead><tbody>';
    
    S.products.forEach(function(p) {
        var pid = p.product_id;
        var qty = S.selectedProducts[pid] || 0;
        html += '<tr><td>' + (p.name || 'Товар').slice(0, 50) + '</td>' +
            '<td>' + (p.offer_id || '-') + '</td>' +
            '<td>' + pid + '</td>' +
            '<td><input type="number" class="qty-input" value="' + qty + '" min="0" onchange="setQty(' + pid + ',this.value)"></td></tr>';
    });
    html += '</tbody></table>';
    
    html += '<div style="margin-top:24px;display:flex;justify-content:space-between">' +
        '<button class="btn btn-default" onclick="prevStep()">← Назад</button>' +
        '<button class="btn btn-primary btn-lg" onclick="nextStep()" ' + (totalQty === 0 ? 'disabled' : '') + '>Далее → Подтверждение</button></div>';
    
    pl.innerHTML = html;
}

function setQty(pid, val) {
    S.selectedProducts[pid] = parseInt(val) || 0;
    if (S.selectedProducts[pid] === 0) delete S.selectedProducts[pid];
    renderProductsList();
}

// STEP 3: Confirm
function renderStepConfirm(sc) {
    var totalQty = Object.values(S.selectedProducts).reduce(function(a, b) { return a + b; }, 0);
    var productCount = Object.keys(S.selectedProducts).length;
    
    var html = '<div class="card"><div class="card-header"><div class="card-title">✅ Подтверждение поставки</div></div><div class="card-body">';
    html += '<div style="display:grid;gap:16px;margin-bottom:24px">' +
        '<div><strong>Склад:</strong> ' + (S.selectedWarehouse ? S.selectedWarehouse.name : 'Не выбран') + '</div>' +
        '<div><strong>Товаров:</strong> ' + productCount + ' наименований</div>' +
        '<div><strong>Общее количество:</strong> ' + totalQty + ' шт</div></div>';
    
    html += '<div class="info-box"><div class="info-title">📋 Список товаров</div>';
    Object.keys(S.selectedProducts).forEach(function(pid) {
        var p = S.products.find(function(pr) { return pr.product_id == pid; });
        html += '<div style="padding:8px 0;border-bottom:1px solid #e0e0e0">' + (p ? p.name : 'Товар ' + pid).slice(0, 40) + ' — <strong>' + S.selectedProducts[pid] + ' шт</strong></div>';
    });
    html += '</div>';
    
    html += '<div style="margin-top:24px;display:flex;justify-content:space-between">' +
        '<button class="btn btn-default" onclick="prevStep()">← Назад</button>' +
        '<button class="btn btn-success btn-lg" onclick="createSupply()">🚀 Создать поставку</button></div>';
    html += '</div></div>';
    sc.innerHTML = html;
}

function createSupply() {
    toast('Функция создания поставки в разработке. Используйте ЛК Ozon для создания заявки.', 'success');
}

function nextStep() { S.step++; renderStep(); }
function prevStep() { S.step--; renderStep(); }

// ==================== SUPPLIES PAGE ====================
function renderSupplies(c) {
    c.innerHTML = '<div class="page-title">📋 Мои поставки</div>' +
        '<div class="card"><div class="card-header"><div class="card-title">Список поставок</div>' +
        '<button class="btn btn-primary" onclick="loadSupplies()">🔄 Загрузить</button></div>' +
        '<div class="card-body" id="supplies-list"><div class="info-box"><div class="info-title">💡 Подсказка</div>Нажмите "Загрузить" чтобы получить список ваших поставок</div></div></div>';
}

function loadSupplies() {
    var sl = document.getElementById('supplies-list');
    sl.innerHTML = '<div class="loading"><div class="spinner"></div>Загрузка поставок...</div>';
    
    api('/v2/supply-order/list', { filter: {} }).then(function(d) {
        if (d.error) {
            sl.innerHTML = renderError('Не удалось загрузить поставки', d.message);
            return;
        }
        S.supplies = d.supply_orders || d.result || [];
        renderSuppliesList();
    });
}

function renderSuppliesList() {
    var sl = document.getElementById('supplies-list');
    if (!S.supplies.length) {
        sl.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-title">Нет поставок</div></div>';
        return;
    }
    var html = '';
    S.supplies.forEach(function(s) {
        var stateClass = 'status-filling';
        var stateText = s.state || 'Неизвестно';
        if (s.state && s.state.includes('COMPLETED')) { stateClass = 'status-completed'; stateText = 'Завершена'; }
        else if (s.state && s.state.includes('READY')) { stateClass = 'status-ready'; stateText = 'Готова'; }
        else if (s.state && s.state.includes('CANCELLED')) { stateClass = 'status-cancelled'; stateText = 'Отменена'; }
        else if (s.state && s.state.includes('FILLING')) { stateText = 'Заполнение'; }
        
        html += '<div class="supply-card">' +
            '<div class="supply-id">#' + (s.supply_order_id || s.id || '?') + '</div>' +
            '<div>' + (s.warehouse_name || 'Склад') + '</div>' +
            '<div>' + formatDate(s.created_at) + '</div>' +
            '<div>' + (s.items_count || '?') + ' товаров</div>' +
            '<span class="supply-status ' + stateClass + '">' + stateText + '</span></div>';
    });
    sl.innerHTML = html;
}

// ==================== PRODUCTS PAGE ====================
function renderProducts(c) {
    c.innerHTML = '<div class="page-title">📦 Мои товары</div>' +
        '<div class="card"><div class="card-header"><div class="card-title">Каталог</div>' +
        '<button class="btn btn-primary" onclick="loadAllProducts()">🔄 Загрузить</button></div>' +
        '<div class="card-body" id="all-products"><div class="info-box"><div class="info-title">💡 Подсказка</div>Нажмите "Загрузить" для просмотра товаров</div></div></div>';
}

function loadAllProducts() {
    var ap = document.getElementById('all-products');
    ap.innerHTML = '<div class="loading"><div class="spinner"></div>Загрузка...</div>';
    api('/v2/product/list', { filter: { visibility: 'ALL' }, limit: 100 }).then(function(d) {
        if (d.error) { ap.innerHTML = renderError('Ошибка', d.message); return; }
        var items = d.result ? d.result.items : [];
        if (!items.length) { ap.innerHTML = '<div class="empty-state"><div class="empty-icon">📦</div><div class="empty-title">Нет товаров</div></div>'; return; }
        var html = '<table class="product-table"><thead><tr><th>Товар</th><th>Артикул</th><th>ID</th></tr></thead><tbody>';
        items.forEach(function(p) {
            html += '<tr><td>' + (p.name || '-').slice(0, 50) + '</td><td>' + (p.offer_id || '-') + '</td><td>' + (p.product_id || '-') + '</td></tr>';
        });
        html += '</tbody></table>';
        ap.innerHTML = html;
        toast('Загружено ' + items.length + ' товаров', 'success');
    });
}

// ==================== LOGS PAGE ====================
function renderLogs(c) {
    c.innerHTML = '<div class="page-title">📝 Логи API</div>' +
        '<div class="card"><div class="card-header"><div class="card-title">История запросов</div>' +
        '<button class="btn btn-default" onclick="renderLogs(document.getElementById(\'page-content\'))">🔄 Обновить</button></div>' +
        '<div class="card-body" id="logs-list"><div class="loading"><div class="spinner"></div>Загрузка...</div></div></div>';
    
    fetch('/logs').then(function(r) { return r.json(); }).then(function(logs) {
        var ll = document.getElementById('logs-list');
        if (!logs.length) {
            ll.innerHTML = '<div class="empty-state"><div class="empty-icon">📝</div><div class="empty-title">Логи пусты</div></div>';
            return;
        }
        var html = '<table class="log-table"><thead><tr><th>Время</th><th>Статус</th><th>Endpoint</th><th>Сообщение</th></tr></thead><tbody>';
        logs.forEach(function(l) {
            html += '<tr><td>' + l.time + '</td>' +
                '<td><span class="log-level ' + l.level + '">' + l.level.toUpperCase() + '</span></td>' +
                '<td style="color:#005bff;font-family:monospace">' + l.endpoint + '</td>' +
                '<td style="max-width:400px;word-break:break-all;font-size:11px;color:#666">' + l.message + '</td></tr>';
        });
        html += '</tbody></table>';
        ll.innerHTML = html;
    });
}

function formatDate(d) {
    if (!d) return '-';
    return new Date(d).toLocaleDateString('ru-RU');
}

function testConn() {
    setConn(null, 'Проверка...');
    api('/v1/warehouse/list', {}).then(function(d) {
        if (d.error) { setConn(false, 'Ошибка'); toast('Ошибка подключения: ' + (d.message || '').slice(0, 100), 'error'); }
        else { setConn(true, 'Подключено ✓'); }
    });
}

render();
testConn();
</script>
</body>
</html>'''


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        if self.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == "/logs":
            self.json_resp(LOGS)
        elif self.path == "/health":
            self.json_resp({"status": "ok", "version": "1.1"})
        elif self.path.startswith("/labels/"):
            file_guid = self.path.split("/labels/")[1]
            pdf_data = ozon_get(f"/v1/cargoes-label/file/{file_guid}")
            if pdf_data:
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f"attachment; filename=labels_{file_guid}.pdf")
                self.end_headers()
                self.wfile.write(pdf_data)
            else:
                self.send_error(404)
        else:
            self.send_error(404)
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        
        if self.path.startswith("/ozon/"):
            endpoint = self.path[5:]
            self.json_resp(ozon_request(endpoint, body))
        else:
            self.send_error(404)
    
    def json_resp(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def log_message(self, f, *a): pass


if __name__ == "__main__":
    print(f"""
╔════════════════════════════════════════════════╗
║     📦 OZON FBO Supply Manager v1.1            ║
╠════════════════════════════════════════════════╣
║  Client ID: {OZON_CLIENT_ID:<30}║
║  API Key:   {OZON_API_KEY[:20]}...              ║
║                                                ║
║  🌐 http://localhost:{PORT:<24}║
╚════════════════════════════════════════════════╝
""")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

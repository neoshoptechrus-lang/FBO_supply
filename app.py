#!/usr/bin/env python3
"""
OZON FBO Supply Manager v3.0
Полностью переделан по реальному интерфейсу Ozon:
1. Товары - поиск и выбор
2. Точка отгрузки - период + выбор СЦ/ФФ/ППЗ/ПВЗ
3. Варианты отгрузки - подтверждение
"""

import os, json, urllib.request, urllib.error, ssl
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
OZON_CLIENT_ID = os.environ.get("OZON_CLIENT_ID", "1321895")
OZON_API_KEY = os.environ.get("OZON_API_KEY", "1ccae2c9-ee7f-4f3f-bac1-e14e38bc11f3")

OZON_API = "https://api-seller.ozon.ru"
LOGS = []

def log(level, ep, msg):
    entry = {"time": datetime.now().strftime("%H:%M:%S"), "level": level, "endpoint": ep, "message": str(msg)[:500]}
    LOGS.insert(0, entry)
    if len(LOGS) > 500: LOGS.pop()
    print(f"[{entry['time']}] [{level.upper()}] {ep}: {str(msg)[:100]}")

def ozon_request(endpoint, body=None):
    headers = {"Content-Type": "application/json", "Client-Id": OZON_CLIENT_ID, "Api-Key": OZON_API_KEY}
    log("request", endpoint, f"Body: {json.dumps(body, ensure_ascii=False)[:200] if body else 'empty'}")
    try:
        ctx = ssl.create_default_context()
        data = json.dumps(body).encode() if body else b'{}'
        req = urllib.request.Request(f"{OZON_API}{endpoint}", data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            result = json.loads(resp.read())
            log("success", endpoint, f"OK")
            return result
    except urllib.error.HTTPError as e:
        error_body = ""
        try: error_body = e.read().decode()
        except: error_body = str(e)
        log("error", endpoint, f"HTTP {e.code}: {error_body[:300]}")
        return {"error": True, "code": e.code, "message": error_body}
    except Exception as e:
        log("error", endpoint, str(e)[:300])
        return {"error": True, "message": str(e)}


HTML = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FBO Supply Manager v3</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f2f3f5;color:#001a34;font-size:14px}

/* Header like Ozon */
.header{background:#fff;border-bottom:1px solid #e4e7ed;padding:12px 24px;display:flex;align-items:center;gap:24px}
.logo{display:flex;align-items:center;gap:8px;font-size:20px;font-weight:700;color:#005bff}
.logo img{height:28px}
.header-nav{display:flex;gap:4px}
.header-nav a{padding:8px 16px;color:#001a34;text-decoration:none;font-size:14px;border-radius:8px}
.header-nav a:hover{background:#f2f3f5}
.header-nav a.active{background:#005bff;color:#fff}
.header-right{margin-left:auto;display:flex;align-items:center;gap:16px}
.conn-status{display:flex;align-items:center;gap:6px;font-size:13px;padding:6px 12px;background:#f2f3f5;border-radius:8px}
.conn-dot{width:8px;height:8px;border-radius:50%}
.conn-dot.ok{background:#00a676}
.conn-dot.err{background:#f91155}
.conn-dot.load{background:#ffaa00;animation:pulse 1s infinite}
@keyframes pulse{50%{opacity:.4}}

/* Main layout */
.main{max-width:1200px;margin:0 auto;padding:24px}
.page-header{margin-bottom:24px}
.page-title{font-size:24px;font-weight:600;margin-bottom:8px}
.breadcrumb{font-size:13px;color:#5c6b7a}
.breadcrumb a{color:#005bff;text-decoration:none}

/* Steps */
.steps-container{display:flex;gap:8px;margin-bottom:24px}
.step-item{display:flex;align-items:center;gap:8px;padding:12px 20px;background:#fff;border-radius:12px;border:2px solid #e4e7ed;cursor:pointer;transition:all .2s}
.step-item:hover{border-color:#005bff}
.step-item.active{border-color:#005bff;background:#f0f6ff}
.step-item.done{border-color:#00a676;background:#e6f9f1}
.step-num{width:28px;height:28px;border-radius:50%;background:#e4e7ed;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:13px}
.step-item.active .step-num{background:#005bff;color:#fff}
.step-item.done .step-num{background:#00a676;color:#fff}
.step-title{font-weight:500}

/* Content grid */
.content-grid{display:grid;grid-template-columns:1fr 320px;gap:24px}
@media(max-width:900px){.content-grid{grid-template-columns:1fr}}

/* Cards */
.card{background:#fff;border-radius:16px;border:1px solid #e4e7ed}
.card-header{padding:20px 24px;border-bottom:1px solid #e4e7ed;display:flex;justify-content:space-between;align-items:center}
.card-title{font-size:16px;font-weight:600}
.card-body{padding:24px}

/* Sidebar */
.sidebar-card{background:#fff;border-radius:16px;border:1px solid #e4e7ed;margin-bottom:16px}
.sidebar-header{padding:16px 20px;border-bottom:1px solid #e4e7ed;font-weight:600}
.sidebar-body{padding:16px 20px}
.sidebar-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f2f3f5}
.sidebar-row:last-child{border-bottom:none}
.sidebar-label{color:#5c6b7a;font-size:13px}
.sidebar-value{font-weight:500;display:flex;align-items:center;gap:6px}
.sidebar-value .icon-ok{color:#00a676}

/* Search */
.search-box{position:relative;margin-bottom:20px}
.search-input{width:100%;padding:14px 16px 14px 44px;border:2px solid #e4e7ed;border-radius:12px;font-size:14px;transition:all .2s}
.search-input:focus{outline:none;border-color:#005bff}
.search-icon{position:absolute;left:16px;top:50%;transform:translateY(-50%);color:#5c6b7a}

/* Product list */
.product-list{max-height:400px;overflow-y:auto}
.product-item{display:flex;align-items:center;gap:12px;padding:12px;border:1px solid #e4e7ed;border-radius:12px;margin-bottom:8px;cursor:pointer;transition:all .2s}
.product-item:hover{border-color:#005bff;background:#f8faff}
.product-item.selected{border-color:#005bff;background:#f0f6ff}
.product-img{width:48px;height:48px;border-radius:8px;background:#f2f3f5;display:flex;align-items:center;justify-content:center;font-size:24px}
.product-info{flex:1}
.product-name{font-size:13px;font-weight:500;margin-bottom:2px;line-height:1.3}
.product-sku{font-size:11px;color:#5c6b7a}
.product-qty{display:flex;align-items:center;gap:8px}
.qty-btn{width:32px;height:32px;border:1px solid #e4e7ed;border-radius:8px;background:#fff;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center}
.qty-btn:hover{background:#f2f3f5}
.qty-input{width:60px;height:32px;border:1px solid #e4e7ed;border-radius:8px;text-align:center;font-size:14px;font-weight:600}
.qty-input:focus{outline:none;border-color:#005bff}

/* Date picker */
.date-section{margin-bottom:24px}
.date-label{font-size:13px;color:#5c6b7a;margin-bottom:8px}
.date-inputs{display:flex;gap:12px}
.date-input{padding:12px 16px;border:2px solid #e4e7ed;border-radius:12px;font-size:14px;cursor:pointer}
.date-input:focus{outline:none;border-color:#005bff}

/* Point types */
.point-types{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px}
.point-type{padding:10px 16px;border:2px solid #e4e7ed;border-radius:10px;cursor:pointer;font-size:13px;font-weight:500;transition:all .2s}
.point-type:hover{border-color:#005bff}
.point-type.active{border-color:#005bff;background:#f0f6ff;color:#005bff}

/* Points list */
.point-item{display:flex;align-items:center;gap:12px;padding:16px;border:2px solid #e4e7ed;border-radius:12px;margin-bottom:8px;cursor:pointer;transition:all .2s}
.point-item:hover{border-color:#005bff}
.point-item.selected{border-color:#005bff;background:#f0f6ff}
.point-icon{width:40px;height:40px;border-radius:10px;background:#f2f3f5;display:flex;align-items:center;justify-content:center;font-size:20px}
.point-info{flex:1}
.point-name{font-weight:600;margin-bottom:2px}
.point-address{font-size:12px;color:#5c6b7a}

/* Buttons */
.btn{padding:12px 24px;border-radius:12px;font-size:14px;font-weight:600;cursor:pointer;border:none;transition:all .2s;display:inline-flex;align-items:center;gap:8px}
.btn-primary{background:#005bff;color:#fff}
.btn-primary:hover{background:#0050e6}
.btn-secondary{background:#f2f3f5;color:#001a34}
.btn-secondary:hover{background:#e4e7ed}
.btn-success{background:#00a676;color:#fff}
.btn-success:hover{background:#008c63}
.btn-lg{padding:16px 32px;font-size:16px}
.btn:disabled{opacity:.5;cursor:not-allowed}

/* Footer actions */
.footer-actions{display:flex;justify-content:space-between;margin-top:24px;padding-top:24px;border-top:1px solid #e4e7ed}

/* Info box */
.info-box{background:#fff8e6;border:1px solid #ffd666;border-radius:12px;padding:16px;margin-bottom:20px;display:flex;gap:12px}
.info-box.blue{background:#e6f4ff;border-color:#91caff}
.info-icon{font-size:20px}
.info-text{font-size:13px;line-height:1.5}

/* Loading */
.loading{text-align:center;padding:40px}
.spinner{width:40px;height:40px;border:4px solid #e4e7ed;border-top-color:#005bff;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 16px}
@keyframes spin{to{transform:rotate(360deg)}}

/* Empty state */
.empty-state{text-align:center;padding:48px 24px}
.empty-icon{font-size:48px;margin-bottom:16px;opacity:.5}
.empty-title{font-size:16px;font-weight:600;margin-bottom:8px}
.empty-text{font-size:13px;color:#5c6b7a}

/* Toast */
.toast-container{position:fixed;bottom:24px;right:24px;z-index:1001}
.toast{padding:14px 20px;background:#001a34;color:#fff;border-radius:12px;margin-top:8px;font-size:13px;animation:slideIn .3s;max-width:360px}
.toast.success{background:#00a676}
.toast.error{background:#f91155}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}}

/* Log table */
.log-table{width:100%;border-collapse:collapse;font-size:12px}
.log-table th,.log-table td{padding:10px;text-align:left;border-bottom:1px solid #e4e7ed}
.log-table th{background:#f8f9fa;font-weight:600}
.log-level{padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;text-transform:uppercase}
.log-level.success{background:#e6f9f1;color:#00a676}
.log-level.error{background:#ffe6eb;color:#f91155}
.log-level.request{background:#e6f4ff;color:#005bff}

/* Selected products summary */
.selected-products{margin-top:16px}
.selected-item{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f2f3f5;font-size:13px}
.selected-item:last-child{border-bottom:none}
.selected-name{flex:1;margin-right:12px}
.selected-qty{font-weight:600;color:#005bff}
.remove-btn{width:24px;height:24px;border:none;background:#f2f3f5;border-radius:6px;cursor:pointer;color:#5c6b7a;margin-left:8px}
.remove-btn:hover{background:#ffe6eb;color:#f91155}
</style>
</head>
<body>

<div class="header">
    <div class="logo">📦 FBO Supply</div>
    <div class="header-nav">
        <a href="#" class="active" onclick="showPage('create')">Создать поставку</a>
        <a href="#" onclick="showPage('drafts')">Черновики</a>
        <a href="#" onclick="showPage('logs')">Логи</a>
    </div>
    <div class="header-right">
        <div class="conn-status" id="conn">
            <div class="conn-dot load"></div>
            <span>Проверка...</span>
        </div>
    </div>
</div>

<div class="main">
    <div class="page-header">
        <div class="breadcrumb"><a href="#">FBO</a> → Заявки на поставку</div>
        <div class="page-title" id="page-title">Создание черновика</div>
    </div>
    
    <div id="page-content"></div>
</div>

<div class="toast-container" id="toasts"></div>

<script>
var S = {
    page: 'create',
    step: 1,
    products: [],
    selectedProducts: {}, // {product_id: {product, qty}}
    dateFrom: '',
    dateTo: '',
    pointType: 'SC',
    points: [],
    selectedPoint: null,
    draftId: null
};

// Init dates
var today = new Date();
var tomorrow = new Date(today.getTime() + 24*60*60*1000);
S.dateFrom = today.toISOString().split('T')[0];
S.dateTo = tomorrow.toISOString().split('T')[0];

function toast(msg, type) {
    var t = document.createElement('div');
    t.className = 'toast ' + (type || '');
    t.textContent = msg;
    document.getElementById('toasts').appendChild(t);
    setTimeout(function() { t.remove(); }, 4000);
}

function setConn(ok, txt) {
    var c = document.getElementById('conn');
    c.innerHTML = '<div class="conn-dot ' + (ok ? 'ok' : ok === false ? 'err' : 'load') + '"></div><span>' + txt + '</span>';
}

function api(ep, body) {
    return fetch('/ozon' + ep, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body || {})
    }).then(r => r.json());
}

function showPage(p) {
    S.page = p;
    document.querySelectorAll('.header-nav a').forEach((a, i) => {
        a.classList.toggle('active', ['create', 'drafts', 'logs'][i] === p);
    });
    render();
}

function render() {
    var c = document.getElementById('page-content');
    var t = document.getElementById('page-title');
    
    if (S.page === 'create') {
        t.textContent = 'Создание черновика';
        renderCreate(c);
    } else if (S.page === 'drafts') {
        t.textContent = 'Черновики';
        renderDrafts(c);
    } else if (S.page === 'logs') {
        t.textContent = 'Логи API';
        renderLogs(c);
    }
}

function renderCreate(c) {
    var steps = [
        {num: 1, title: 'Товары'},
        {num: 2, title: 'Точка отгрузки'},
        {num: 3, title: 'Подтверждение'}
    ];
    
    var stepsHtml = steps.map(s => {
        var cls = s.num < S.step ? 'done' : s.num === S.step ? 'active' : '';
        var icon = s.num < S.step ? '✓' : s.num;
        return `<div class="step-item ${cls}" onclick="goStep(${s.num})">
            <div class="step-num">${icon}</div>
            <div class="step-title">${s.title}</div>
        </div>`;
    }).join('');
    
    var sidebarHtml = renderSidebar();
    
    c.innerHTML = `
        <div class="steps-container">${stepsHtml}</div>
        <div class="content-grid">
            <div class="card">
                <div class="card-body" id="step-content"></div>
            </div>
            <div class="sidebar">${sidebarHtml}</div>
        </div>
    `;
    
    renderStepContent();
}

function renderSidebar() {
    var totalQty = Object.values(S.selectedProducts).reduce((a, b) => a + b.qty, 0);
    var totalProducts = Object.keys(S.selectedProducts).length;
    var totalVolume = Object.values(S.selectedProducts).reduce((a, b) => a + (b.qty * 0.3), 0).toFixed(1);
    
    var hasProducts = totalProducts > 0;
    var hasPoint = S.selectedPoint !== null;
    var hasDates = S.dateFrom && S.dateTo;
    
    return `
        <div class="sidebar-card">
            <div class="sidebar-header">Финальная заявка</div>
            <div class="sidebar-body">
                <div class="sidebar-row">
                    <span class="sidebar-label">Товарный состав</span>
                    <span class="sidebar-value">
                        ${hasProducts ? `<span class="icon-ok">✓</span>` : ''}
                        ${totalProducts} товар, ${totalQty} шт, ${totalVolume} л
                    </span>
                </div>
                <div class="sidebar-row">
                    <span class="sidebar-label">Период отгрузки</span>
                    <span class="sidebar-value">
                        ${hasDates ? `<span class="icon-ok">✓</span>` : ''}
                        ${S.dateFrom ? formatDateShort(S.dateFrom) + ' - ' + formatDateShort(S.dateTo) : 'Не выбран'}
                    </span>
                </div>
                <div class="sidebar-row">
                    <span class="sidebar-label">Точка отгрузки</span>
                    <span class="sidebar-value">
                        ${hasPoint ? `<span class="icon-ok">✓</span>` : ''}
                        ${S.selectedPoint ? S.selectedPoint.name : 'Не выбрана'}
                    </span>
                </div>
            </div>
        </div>
    `;
}

function renderStepContent() {
    var sc = document.getElementById('step-content');
    if (S.step === 1) renderStep1(sc);
    else if (S.step === 2) renderStep2(sc);
    else if (S.step === 3) renderStep3(sc);
}

// STEP 1: Products
function renderStep1(sc) {
    var selectedHtml = '';
    var selectedCount = Object.keys(S.selectedProducts).length;
    
    if (selectedCount > 0) {
        selectedHtml = '<div class="selected-products"><div style="font-weight:600;margin-bottom:12px">Выбранные товары:</div>';
        Object.values(S.selectedProducts).forEach(item => {
            selectedHtml += `<div class="selected-item">
                <span class="selected-name">${item.product.name.slice(0, 40)}...</span>
                <span class="selected-qty">${item.qty} шт</span>
                <button class="remove-btn" onclick="removeProduct(${item.product.product_id})">×</button>
            </div>`;
        });
        selectedHtml += '</div>';
    }
    
    sc.innerHTML = `
        <div style="font-size:18px;font-weight:600;margin-bottom:20px">Добавьте товары и укажите количество</div>
        
        <div class="search-box">
            <span class="search-icon">🔍</span>
            <input type="text" class="search-input" id="search" placeholder="Название, артикул или SKU" onkeyup="searchProducts(this.value)">
        </div>
        
        <div style="font-size:13px;color:#5c6b7a;margin-bottom:12px">Некоторые из ваших товаров</div>
        
        <div class="product-list" id="product-list">
            <div class="loading"><div class="spinner"></div>Загрузка товаров...</div>
        </div>
        
        ${selectedHtml}
        
        <div class="footer-actions">
            <div></div>
            <button class="btn btn-primary" onclick="nextStep()" ${selectedCount === 0 ? 'disabled' : ''}>Продолжить</button>
        </div>
    `;
    
    loadProducts();
}

function loadProducts() {
    api('/v3/product/list', {filter: {visibility: 'ALL'}, limit: 50}).then(d => {
        if (d.error) {
            document.getElementById('product-list').innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><div class="empty-title">Ошибка загрузки</div><div class="empty-text">${d.message}</div></div>`;
            return;
        }
        S.products = d.result ? d.result.items : [];
        renderProductList();
    });
}

function renderProductList(filter) {
    var pl = document.getElementById('product-list');
    var items = S.products;
    
    if (filter) {
        filter = filter.toLowerCase();
        items = items.filter(p => 
            (p.name && p.name.toLowerCase().includes(filter)) ||
            (p.offer_id && p.offer_id.toLowerCase().includes(filter)) ||
            (p.product_id && p.product_id.toString().includes(filter))
        );
    }
    
    if (!items.length) {
        pl.innerHTML = '<div class="empty-state"><div class="empty-icon">📦</div><div class="empty-title">Товары не найдены</div></div>';
        return;
    }
    
    pl.innerHTML = items.slice(0, 20).map(p => {
        var isSelected = S.selectedProducts[p.product_id];
        var qty = isSelected ? isSelected.qty : 0;
        return `<div class="product-item ${isSelected ? 'selected' : ''}" id="product-${p.product_id}">
            <div class="product-img">📦</div>
            <div class="product-info">
                <div class="product-name">${(p.name || 'Товар').slice(0, 60)}</div>
                <div class="product-sku">Ozon ID ${p.offer_id || p.product_id}</div>
            </div>
            <div class="product-qty">
                <button class="qty-btn" onclick="changeQty(${p.product_id}, -1)">−</button>
                <input type="number" class="qty-input" value="${qty}" min="0" onchange="setQty(${p.product_id}, this.value)" id="qty-${p.product_id}">
                <button class="qty-btn" onclick="changeQty(${p.product_id}, 1)">+</button>
            </div>
        </div>`;
    }).join('');
}

function searchProducts(val) {
    renderProductList(val);
}

function changeQty(pid, delta) {
    var input = document.getElementById('qty-' + pid);
    var newVal = Math.max(0, (parseInt(input.value) || 0) + delta);
    input.value = newVal;
    setQty(pid, newVal);
}

function setQty(pid, val) {
    var qty = parseInt(val) || 0;
    var product = S.products.find(p => p.product_id == pid);
    
    if (qty > 0 && product) {
        S.selectedProducts[pid] = {product: product, qty: qty};
    } else {
        delete S.selectedProducts[pid];
    }
    
    var item = document.getElementById('product-' + pid);
    if (item) item.classList.toggle('selected', qty > 0);
    
    // Update sidebar
    document.querySelector('.sidebar').innerHTML = renderSidebar();
    
    // Update button state
    var btn = document.querySelector('.footer-actions .btn-primary');
    if (btn) btn.disabled = Object.keys(S.selectedProducts).length === 0;
}

function removeProduct(pid) {
    delete S.selectedProducts[pid];
    renderStep1(document.getElementById('step-content'));
}

// STEP 2: Point
function renderStep2(sc) {
    var pointTypes = [
        {id: 'SC', name: 'Сортировочные центры (СЦ)'},
        {id: 'FF', name: 'Фулфилменты (ФФ)'},
        {id: 'PPZ', name: 'Пункты приёма (ППЗ)'},
        {id: 'PVZ', name: 'Пункты выдачи (ПВЗ)'}
    ];
    
    sc.innerHTML = `
        <div style="font-size:18px;font-weight:600;margin-bottom:20px">Поставка через виртуальный распределительный центр (вРЦ)</div>
        
        <div class="info-box blue">
            <span class="info-icon">💡</span>
            <div class="info-text">Распределим товары по нескольким складам, где на них будет наибольший спрос. Укажите, когда и куда вам удобно привезти товары.</div>
        </div>
        
        <div class="date-section">
            <div class="date-label">Период отгрузки</div>
            <div class="date-inputs">
                <input type="date" class="date-input" value="${S.dateFrom}" onchange="S.dateFrom=this.value;updateSidebar()">
                <span style="padding:12px">—</span>
                <input type="date" class="date-input" value="${S.dateTo}" onchange="S.dateTo=this.value;updateSidebar()">
            </div>
        </div>
        
        <div style="font-size:14px;font-weight:600;margin-bottom:12px">Точка отгрузки</div>
        <div style="font-size:13px;color:#5c6b7a;margin-bottom:12px">Можно указать свой склад — покажем точки возле него</div>
        
        <div class="point-types">
            ${pointTypes.map(pt => `<div class="point-type ${S.pointType === pt.id ? 'active' : ''}" onclick="selectPointType('${pt.id}')">${pt.name}</div>`).join('')}
        </div>
        
        <div id="points-list">
            <div class="loading"><div class="spinner"></div>Загрузка точек...</div>
        </div>
        
        <div class="footer-actions">
            <button class="btn btn-secondary" onclick="prevStep()">Назад</button>
            <button class="btn btn-primary" onclick="nextStep()" ${!S.selectedPoint ? 'disabled' : ''}>Продолжить</button>
        </div>
    `;
    
    loadPoints();
}

function selectPointType(type) {
    S.pointType = type;
    S.selectedPoint = null;
    document.querySelectorAll('.point-type').forEach(el => el.classList.remove('active'));
    document.querySelector(`.point-type[onclick*="${type}"]`).classList.add('active');
    loadPoints();
}

function loadPoints() {
    // Load warehouses/points
    api('/v1/warehouse/list', {}).then(d => {
        if (d.error) {
            document.getElementById('points-list').innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><div class="empty-text">${d.message}</div></div>`;
            return;
        }
        S.points = d.result || [];
        renderPoints();
    });
}

function renderPoints() {
    var pl = document.getElementById('points-list');
    
    if (!S.points.length) {
        pl.innerHTML = '<div class="empty-state"><div class="empty-icon">📍</div><div class="empty-title">Точки не найдены</div></div>';
        return;
    }
    
    pl.innerHTML = S.points.slice(0, 10).map((p, i) => {
        var isSelected = S.selectedPoint && S.selectedPoint.warehouse_id === p.warehouse_id;
        return `<div class="point-item ${isSelected ? 'selected' : ''}" onclick="selectPoint(${i})">
            <div class="point-icon">📍</div>
            <div class="point-info">
                <div class="point-name">${p.name || 'Склад ' + p.warehouse_id}</div>
                <div class="point-address">ID: ${p.warehouse_id}</div>
            </div>
        </div>`;
    }).join('');
}

function selectPoint(idx) {
    S.selectedPoint = S.points[idx];
    renderPoints();
    updateSidebar();
    
    var btn = document.querySelector('.footer-actions .btn-primary');
    if (btn) btn.disabled = false;
}

function updateSidebar() {
    document.querySelector('.sidebar').innerHTML = renderSidebar();
}

// STEP 3: Confirm
function renderStep3(sc) {
    var totalQty = Object.values(S.selectedProducts).reduce((a, b) => a + b.qty, 0);
    var totalProducts = Object.keys(S.selectedProducts).length;
    
    sc.innerHTML = `
        <div style="font-size:18px;font-weight:600;margin-bottom:20px">Подтверждение заявки</div>
        
        <div class="info-box">
            <span class="info-icon">📋</span>
            <div class="info-text">
                <strong>Товаров:</strong> ${totalProducts} наименований, ${totalQty} шт<br>
                <strong>Период:</strong> ${formatDateShort(S.dateFrom)} — ${formatDateShort(S.dateTo)}<br>
                <strong>Точка:</strong> ${S.selectedPoint ? S.selectedPoint.name : 'Не выбрана'}
            </div>
        </div>
        
        <div style="margin:24px 0">
            <div style="font-weight:600;margin-bottom:12px">Состав поставки:</div>
            ${Object.values(S.selectedProducts).map(item => `
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #e4e7ed">
                    <span>${item.product.name.slice(0, 50)}...</span>
                    <strong>${item.qty} шт</strong>
                </div>
            `).join('')}
        </div>
        
        <div class="footer-actions">
            <button class="btn btn-secondary" onclick="prevStep()">Назад</button>
            <button class="btn btn-success btn-lg" onclick="createDraft()">🚀 Создать черновик</button>
        </div>
    `;
}

function createDraft() {
    toast('Создание черновика...', '');
    
    // Prepare items
    var items = Object.values(S.selectedProducts).map(item => ({
        sku: item.product.product_id,
        quantity: item.qty
    }));
    
    api('/v1/draft/create', {
        items: items,
        warehouse_id: S.selectedPoint ? S.selectedPoint.warehouse_id : undefined
    }).then(d => {
        if (d.error) {
            toast('Ошибка: ' + (d.message || '').slice(0, 100), 'error');
            return;
        }
        S.draftId = d.draft_id || d.operation_id || d.result;
        toast('Черновик создан! ID: ' + S.draftId, 'success');
        
        // Reset
        setTimeout(() => {
            S.step = 1;
            S.selectedProducts = {};
            S.selectedPoint = null;
            render();
        }, 2000);
    });
}

function goStep(n) {
    if (n <= S.step) {
        S.step = n;
        renderStepContent();
        updateSidebar();
    }
}

function nextStep() {
    S.step++;
    renderStepContent();
    updateSidebar();
}

function prevStep() {
    S.step--;
    renderStepContent();
    updateSidebar();
}

// Drafts page
function renderDrafts(c) {
    c.innerHTML = `
        <div class="card">
            <div class="card-header">
                <div class="card-title">Черновики заявок</div>
                <button class="btn btn-primary" onclick="loadDrafts()">🔄 Обновить</button>
            </div>
            <div class="card-body" id="drafts-list">
                <div class="info-box blue">
                    <span class="info-icon">💡</span>
                    <div class="info-text">Здесь будут отображаться созданные черновики. Нажмите "Обновить" для загрузки.</div>
                </div>
            </div>
        </div>
    `;
}

function loadDrafts() {
    var dl = document.getElementById('drafts-list');
    dl.innerHTML = '<div class="loading"><div class="spinner"></div>Загрузка...</div>';
    
    api('/v1/supply-order/list', {filter: {}}).then(d => {
        if (d.error) {
            dl.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><div class="empty-text">${d.message}</div></div>`;
            return;
        }
        var items = d.supply_orders || d.result || [];
        if (!items.length) {
            dl.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-title">Нет заявок</div></div>';
            return;
        }
        dl.innerHTML = items.map(s => `
            <div style="padding:16px;border:1px solid #e4e7ed;border-radius:12px;margin-bottom:8px">
                <div style="font-weight:600">#${s.supply_order_id || s.id}</div>
                <div style="font-size:13px;color:#5c6b7a">${s.state || 'Статус неизвестен'}</div>
            </div>
        `).join('');
    });
}

// Logs page
function renderLogs(c) {
    c.innerHTML = `
        <div class="card">
            <div class="card-header">
                <div class="card-title">История API запросов</div>
                <button class="btn btn-secondary" onclick="render()">🔄 Обновить</button>
            </div>
            <div class="card-body" id="logs-container">
                <div class="loading"><div class="spinner"></div></div>
            </div>
        </div>
    `;
    
    fetch('/logs').then(r => r.json()).then(logs => {
        var lc = document.getElementById('logs-container');
        if (!logs.length) {
            lc.innerHTML = '<div class="empty-state"><div class="empty-icon">📝</div><div class="empty-title">Логов пока нет</div></div>';
            return;
        }
        lc.innerHTML = `<table class="log-table">
            <thead><tr><th>Время</th><th>Статус</th><th>Endpoint</th><th>Сообщение</th></tr></thead>
            <tbody>${logs.slice(0, 50).map(l => `
                <tr>
                    <td>${l.time}</td>
                    <td><span class="log-level ${l.level}">${l.level}</span></td>
                    <td style="font-family:monospace;color:#005bff">${l.endpoint}</td>
                    <td style="max-width:300px;font-size:11px;color:#5c6b7a;word-break:break-all">${l.message}</td>
                </tr>
            `).join('')}</tbody>
        </table>`;
    });
}

// Utils
function formatDateShort(d) {
    if (!d) return '';
    var date = new Date(d);
    return date.toLocaleDateString('ru-RU', {day: '2-digit', month: '2-digit'});
}

function testConn() {
    setConn(null, 'Проверка...');
    api('/v1/warehouse/list', {}).then(d => {
        if (d.error) {
            setConn(false, 'Ошибка');
        } else {
            setConn(true, 'Подключено');
        }
    });
}

// Init
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
            self.json_resp({"status": "ok", "version": "3.0"})
        else:
            self.send_error(404)
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        if self.path.startswith("/ozon/"):
            self.json_resp(ozon_request(self.path[5:], body))
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
╔══════════════════════════════════════════════════╗
║      📦 FBO Supply Manager v3.0                  ║
╠══════════════════════════════════════════════════╣
║  Интерфейс как в Ozon Seller                     ║
║  Client ID: {OZON_CLIENT_ID}                            ║
║                                                  ║
║  🌐 http://localhost:{PORT}                         ║
╚══════════════════════════════════════════════════╝
""")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

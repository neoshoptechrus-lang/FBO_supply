#!/usr/bin/env python3
"""
OZON FBO Supply Manager v1.0
Полный цикл создания поставок FBO:
1. Выбор кластера и склада
2. Добавление товаров
3. Создание черновика
4. Выбор таймслота
5. Формирование грузомест
6. Генерация этикеток
7. Просмотр статуса поставок
"""

import os, json, urllib.request, urllib.error, ssl, time
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
OZON_CLIENT_ID = os.environ.get("OZON_CLIENT_ID", "1321895")
OZON_API_KEY = os.environ.get("OZON_API_KEY", "310cded9-e724-4480-b95a-4d74bf152129")

OZON_API = "https://api-seller.ozon.ru"
LOGS = []

def log(level, ep, msg):
    LOGS.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "level": level, "endpoint": ep, "message": str(msg)[:200]})
    if len(LOGS) > 300: LOGS.pop()

def ozon_request(endpoint, body=None):
    headers = {"Content-Type": "application/json", "Client-Id": OZON_CLIENT_ID, "Api-Key": OZON_API_KEY}
    log("request", endpoint, f"Body: {json.dumps(body)[:100] if body else 'empty'}")
    try:
        ctx = ssl.create_default_context()
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(f"{OZON_API}{endpoint}", data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            result = json.loads(resp.read())
            log("success", endpoint, "OK")
            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else str(e)
        log("error", endpoint, f"HTTP {e.code}: {error_body[:150]}")
        return {"error": True, "code": e.code, "message": error_body}
    except Exception as e:
        log("error", endpoint, str(e)[:150])
        return {"error": True, "message": str(e)}

def ozon_get(endpoint):
    """GET запрос для скачивания файлов"""
    headers = {"Client-Id": OZON_CLIENT_ID, "Api-Key": OZON_API_KEY}
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(f"{OZON_API}{endpoint}", headers=headers, method="GET")
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            return resp.read()
    except Exception as e:
        log("error", endpoint, str(e)[:150])
        return None


HTML = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OZON FBO Supply Manager</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f5f5;color:#1a1a1a;font-size:14px}
.header{background:linear-gradient(135deg,#005bff 0%,#0039a6 100%);color:#fff;padding:16px 24px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.logo{font-size:22px;font-weight:700;display:flex;align-items:center;gap:10px}
.logo-icon{font-size:28px}
.logo span{background:#00c752;color:#fff;font-size:10px;padding:2px 8px;border-radius:10px;margin-left:8px}
.conn{display:flex;align-items:center;gap:8px;font-size:13px;background:rgba(255,255,255,.15);padding:8px 14px;border-radius:8px}
.conn-dot{width:10px;height:10px;border-radius:50%;background:#00c752}
.conn-dot.err{background:#ff4d4f}
.conn-dot.load{background:#faad14;animation:pulse 1s infinite}
@keyframes pulse{50%{opacity:.4}}

.container{max-width:1400px;margin:0 auto;padding:24px}
.nav{display:flex;gap:8px;margin-bottom:24px;background:#fff;padding:8px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.nav-btn{padding:12px 20px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;border:none;background:transparent;color:#666;transition:all .2s;display:flex;align-items:center;gap:8px}
.nav-btn:hover{background:#f5f5f5;color:#005bff}
.nav-btn.active{background:#005bff;color:#fff}
.nav-btn .badge{background:#ff4d4f;color:#fff;font-size:10px;padding:2px 6px;border-radius:10px;margin-left:4px}

.page-title{font-size:26px;font-weight:700;margin-bottom:24px;display:flex;align-items:center;gap:12px}
.page-subtitle{font-size:14px;color:#666;font-weight:400;margin-left:12px}

.card{background:#fff;border-radius:16px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:20px;overflow:hidden}
.card-header{padding:20px 24px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center}
.card-title{font-size:18px;font-weight:600;display:flex;align-items:center;gap:10px}
.card-body{padding:24px}

.btn{padding:12px 20px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;border:none;transition:all .2s;display:inline-flex;align-items:center;gap:8px}
.btn-primary{background:#005bff;color:#fff}
.btn-primary:hover{background:#0050e6;transform:translateY(-1px)}
.btn-success{background:#00c752;color:#fff}
.btn-success:hover{background:#00b348}
.btn-danger{background:#ff4d4f;color:#fff}
.btn-danger:hover{background:#e6393b}
.btn-warning{background:#faad14;color:#fff}
.btn-warning:hover{background:#d99200}
.btn-default{background:#f5f5f5;color:#1a1a1a;border:1px solid #e0e0e0}
.btn-default:hover{border-color:#005bff;color:#005bff}
.btn-lg{padding:16px 32px;font-size:16px}
.btn:disabled{opacity:.5;cursor:not-allowed;transform:none}

.form-group{margin-bottom:20px}
.form-label{display:block;font-size:13px;font-weight:600;margin-bottom:8px;color:#333}
.form-hint{font-size:12px;color:#999;margin-top:4px}
.form-input,.form-select{width:100%;padding:14px 16px;border:2px solid #e0e0e0;border-radius:10px;font-size:14px;transition:all .2s}
.form-input:focus,.form-select:focus{outline:none;border-color:#005bff;box-shadow:0 0 0 3px rgba(0,91,255,.1)}
.form-select{cursor:pointer;background:#fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 8L1 3h10z'/%3E%3C/svg%3E") no-repeat right 16px center}

.steps{display:flex;gap:0;margin-bottom:32px;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.step{flex:1;padding:20px;text-align:center;position:relative;cursor:pointer;transition:all .2s}
.step::after{content:'';position:absolute;right:0;top:50%;transform:translateY(-50%);border:8px solid transparent;border-left-color:#e0e0e0}
.step:last-child::after{display:none}
.step:hover{background:#f9f9f9}
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
.grid-4{grid-template-columns:repeat(4,1fr)}
@media(max-width:768px){.grid-2,.grid-3,.grid-4{grid-template-columns:1fr}}

.cluster-card{border:2px solid #e0e0e0;border-radius:12px;padding:20px;cursor:pointer;transition:all .2s;text-align:center}
.cluster-card:hover{border-color:#005bff;transform:translateY(-2px)}
.cluster-card.selected{border-color:#005bff;background:#f0f7ff}
.cluster-icon{font-size:36px;margin-bottom:12px}
.cluster-name{font-size:16px;font-weight:600;margin-bottom:4px}
.cluster-info{font-size:12px;color:#666}

.warehouse-card{border:2px solid #e0e0e0;border-radius:12px;padding:16px;cursor:pointer;transition:all .2s}
.warehouse-card:hover{border-color:#005bff}
.warehouse-card.selected{border-color:#005bff;background:#f0f7ff}
.warehouse-name{font-size:14px;font-weight:600;margin-bottom:4px}
.warehouse-address{font-size:12px;color:#666;margin-bottom:8px}
.warehouse-status{display:inline-block;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600}
.warehouse-status.open{background:#e6f7e6;color:#00a32e}
.warehouse-status.closed{background:#fff1f0;color:#ff4d4f}

.product-table{width:100%;border-collapse:collapse}
.product-table th{text-align:left;padding:14px 16px;background:#f9f9f9;font-size:12px;font-weight:600;color:#666;text-transform:uppercase}
.product-table td{padding:14px 16px;border-bottom:1px solid #f0f0f0}
.product-table tr:hover{background:#fafafa}
.product-img{width:50px;height:50px;border-radius:8px;object-fit:cover;background:#f5f5f5}
.product-name{font-size:13px;font-weight:500;margin-bottom:2px}
.product-sku{font-size:11px;color:#999}
.qty-input{width:80px;padding:10px;border:2px solid #e0e0e0;border-radius:8px;text-align:center;font-size:14px;font-weight:600}
.qty-input:focus{outline:none;border-color:#005bff}

.cargo-box{border:2px dashed #e0e0e0;border-radius:12px;padding:20px;margin-bottom:16px;transition:all .2s}
.cargo-box:hover{border-color:#005bff}
.cargo-box.filled{border-style:solid;border-color:#00c752;background:#f6ffed}
.cargo-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.cargo-title{font-size:16px;font-weight:600;display:flex;align-items:center;gap:8px}
.cargo-type{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;background:#f0f0f0;color:#666}
.cargo-type.pallet{background:#fff7e6;color:#fa8c16}
.cargo-type.box{background:#e6f7ff;color:#1890ff}
.cargo-items{display:flex;flex-wrap:wrap;gap:8px}
.cargo-item{background:#f5f5f5;padding:8px 12px;border-radius:8px;font-size:12px;display:flex;align-items:center;gap:6px}
.cargo-item-qty{font-weight:700;color:#005bff}

.timeslot-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}
.timeslot-card{border:2px solid #e0e0e0;border-radius:12px;padding:16px;cursor:pointer;transition:all .2s;text-align:center}
.timeslot-card:hover{border-color:#005bff}
.timeslot-card.selected{border-color:#005bff;background:#f0f7ff}
.timeslot-card.unavailable{opacity:.5;cursor:not-allowed}
.timeslot-date{font-size:16px;font-weight:700;margin-bottom:4px}
.timeslot-time{font-size:14px;color:#666}
.timeslot-capacity{font-size:11px;color:#999;margin-top:8px}

.supply-list{display:flex;flex-direction:column;gap:12px}
.supply-card{display:grid;grid-template-columns:100px 1fr 120px 120px 100px 120px;align-items:center;padding:16px 20px;background:#fff;border-radius:12px;border:1px solid #e0e0e0;gap:16px}
.supply-card:hover{box-shadow:0 2px 8px rgba(0,0,0,.08)}
.supply-id{font-size:14px;font-weight:700;color:#005bff}
.supply-warehouse{font-size:13px}
.supply-warehouse small{display:block;color:#999;font-size:11px}
.supply-date{font-size:13px}
.supply-items{font-size:13px;color:#666}
.supply-status{display:inline-block;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:600}
.status-draft{background:#f5f5f5;color:#666}
.status-filling{background:#fff7e6;color:#fa8c16}
.status-ready{background:#e6f7ff;color:#1890ff}
.status-accepted{background:#f0f5ff;color:#722ed1}
.status-completed{background:#f6ffed;color:#52c41a}
.status-cancelled{background:#fff1f0;color:#ff4d4f}

.summary-box{background:#f9f9f9;border-radius:12px;padding:20px}
.summary-row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #e0e0e0}
.summary-row:last-child{border-bottom:none;font-weight:700;font-size:16px}
.summary-label{color:#666}
.summary-value{font-weight:600}

.empty-state{text-align:center;padding:60px 20px}
.empty-icon{font-size:64px;margin-bottom:16px;opacity:.5}
.empty-title{font-size:18px;font-weight:600;margin-bottom:8px;color:#333}
.empty-text{font-size:14px;color:#999;margin-bottom:24px}

.toast-container{position:fixed;bottom:24px;right:24px;z-index:1001}
.toast{padding:16px 24px;background:#1a1a1a;color:#fff;border-radius:12px;margin-top:12px;font-size:14px;animation:slideIn .3s;display:flex;align-items:center;gap:10px;box-shadow:0 4px 12px rgba(0,0,0,.15)}
.toast.success{background:#00c752}
.toast.error{background:#ff4d4f}
.toast.warning{background:#faad14}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}}

.loading{text-align:center;padding:40px}
.spinner{width:40px;height:40px;border:4px solid #f0f0f0;border-top-color:#005bff;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 16px}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-text{color:#666;font-size:14px}

.modal{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;align-items:center;justify-content:center;z-index:1000}
.modal.active{display:flex}
.modal-content{background:#fff;border-radius:16px;width:700px;max-width:95%;max-height:90vh;overflow:auto}
.modal-header{padding:20px 24px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center}
.modal-title{font-size:20px;font-weight:700}
.modal-close{width:36px;height:36px;border-radius:10px;border:none;background:#f5f5f5;cursor:pointer;font-size:20px;display:flex;align-items:center;justify-content:center}
.modal-close:hover{background:#e0e0e0}
.modal-body{padding:24px}
.modal-footer{padding:20px 24px;border-top:1px solid #f0f0f0;display:flex;justify-content:flex-end;gap:12px}

.progress-panel{background:#fff;border-radius:12px;padding:24px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.progress-title{font-size:16px;font-weight:600;margin-bottom:16px}
.progress-bar{height:12px;background:#f0f0f0;border-radius:6px;overflow:hidden}
.progress-fill{height:100%;background:linear-gradient(90deg,#005bff,#00c752);transition:width .3s;border-radius:6px}
.progress-text{margin-top:12px;font-size:13px;color:#666}

.info-banner{background:#e6f7ff;border:1px solid #91d5ff;border-radius:12px;padding:16px 20px;margin-bottom:20px;display:flex;align-items:flex-start;gap:12px}
.info-banner-icon{font-size:20px;color:#1890ff}
.info-banner-text{font-size:13px;color:#1890ff;line-height:1.5}

.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.stat-card{background:#fff;border-radius:12px;padding:20px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.stat-value{font-size:32px;font-weight:700;color:#005bff;margin-bottom:4px}
.stat-label{font-size:12px;color:#666;text-transform:uppercase}
.stat-card.warning .stat-value{color:#faad14}
.stat-card.success .stat-value{color:#00c752}
.stat-card.danger .stat-value{color:#ff4d4f}
</style>
</head>
<body>
<div class="header">
<div class="logo">
<span class="logo-icon">📦</span>
FBO Supply Manager
<span>v1.0</span>
</div>
<div class="conn" id="conn"><div class="conn-dot load"></div><span>Проверка...</span></div>
</div>

<div class="container">
<div class="nav">
<button class="nav-btn active" onclick="showPage('create')">➕ Создать поставку</button>
<button class="nav-btn" onclick="showPage('supplies')">📋 Мои поставки <span class="badge" id="badge-supplies">0</span></button>
<button class="nav-btn" onclick="showPage('products')">📦 Товары</button>
<button class="nav-btn" onclick="showPage('logs')">📝 Логи</button>
</div>

<div id="page-content"></div>
</div>

<div class="modal" id="modal">
<div class="modal-content">
<div class="modal-header"><h3 class="modal-title" id="modal-title">Модальное окно</h3><button class="modal-close" onclick="closeModal()">&times;</button></div>
<div class="modal-body" id="modal-body"></div>
<div class="modal-footer" id="modal-footer"></div>
</div>
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
    // Draft data
    selectedCluster: null,
    selectedWarehouse: null,
    selectedProducts: {},
    selectedTimeslot: null,
    cargoes: [],
    draftId: null,
    supplyId: null
};

function toast(msg, type) {
    var t = document.createElement('div');
    t.className = 'toast ' + (type || '');
    t.innerHTML = '<span>' + (type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️') + '</span>' + msg;
    document.getElementById('toasts').appendChild(t);
    setTimeout(function() { t.remove(); }, 4000);
}

function setConn(ok, txt) {
    document.getElementById('conn').innerHTML = '<div class="conn-dot ' + (ok ? '' : ok === false ? 'err' : 'load') + '"></div><span>' + txt + '</span>';
}

function api(ep, body) {
    return fetch('/ozon' + ep, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
    }).then(function(r) { return r.json(); });
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

// ==================== CREATE SUPPLY PAGE ====================
function renderCreate(c) {
    var stepsHtml = [
        {num: 1, title: 'Кластер', icon: '🗺️'},
        {num: 2, title: 'Склад', icon: '🏭'},
        {num: 3, title: 'Товары', icon: '📦'},
        {num: 4, title: 'Таймслот', icon: '📅'},
        {num: 5, title: 'Грузоместа', icon: '📤'},
        {num: 6, title: 'Этикетки', icon: '🏷️'}
    ].map(function(s) {
        var cls = s.num < S.step ? 'done' : s.num === S.step ? 'active' : '';
        return '<div class="step ' + cls + '" onclick="goToStep(' + s.num + ')"><div class="step-num">' + (s.num < S.step ? '✓' : s.num) + '</div><div class="step-title">' + s.icon + ' ' + s.title + '</div></div>';
    }).join('');

    c.innerHTML = '<div class="page-title">➕ Создать поставку FBO</div>' +
        '<div class="steps">' + stepsHtml + '</div>' +
        '<div id="step-content"></div>';

    renderStep();
}

function goToStep(n) {
    if (n < S.step) {
        S.step = n;
        renderStep();
    }
}

function renderStep() {
    var sc = document.getElementById('step-content');
    if (!sc) return;

    if (S.step === 1) renderStepCluster(sc);
    else if (S.step === 2) renderStepWarehouse(sc);
    else if (S.step === 3) renderStepProducts(sc);
    else if (S.step === 4) renderStepTimeslot(sc);
    else if (S.step === 5) renderStepCargoes(sc);
    else if (S.step === 6) renderStepLabels(sc);
}

// STEP 1: Cluster selection
function renderStepCluster(sc) {
    sc.innerHTML = '<div class="card"><div class="card-header"><div class="card-title">🗺️ Выберите кластер</div>' +
        '<button class="btn btn-default" onclick="loadClusters()">🔄 Обновить</button></div>' +
        '<div class="card-body" id="clusters-grid"><div class="loading"><div class="spinner"></div><div class="loading-text">Загрузка кластеров...</div></div></div></div>';
    
    if (!S.clusters.length) loadClusters();
    else renderClustersGrid();
}

function loadClusters() {
    document.getElementById('clusters-grid').innerHTML = '<div class="loading"><div class="spinner"></div><div class="loading-text">Загрузка кластеров...</div></div>';
    api('/v1/cluster/list', {}).then(function(d) {
        if (d.error) { toast('Ошибка: ' + d.message, 'error'); return; }
        S.clusters = d.clusters || [];
        renderClustersGrid();
        toast('Загружено ' + S.clusters.length + ' кластеров', 'success');
    });
}

function renderClustersGrid() {
    var g = document.getElementById('clusters-grid');
    if (!S.clusters.length) {
        g.innerHTML = '<div class="empty-state"><div class="empty-icon">🗺️</div><div class="empty-title">Нет доступных кластеров</div></div>';
        return;
    }
    var html = '<div class="grid grid-3">';
    S.clusters.forEach(function(cl) {
        var selected = S.selectedCluster && S.selectedCluster.id === cl.id ? 'selected' : '';
        html += '<div class="cluster-card ' + selected + '" onclick="selectCluster(\'' + cl.id + '\')">' +
            '<div class="cluster-icon">📍</div>' +
            '<div class="cluster-name">' + (cl.name || 'Кластер ' + cl.id) + '</div>' +
            '<div class="cluster-info">' + (cl.warehouses_count || '?') + ' складов</div></div>';
    });
    html += '</div>';
    if (S.selectedCluster) {
        html += '<div style="margin-top:24px;text-align:right"><button class="btn btn-primary btn-lg" onclick="nextStep()">Далее → Выбор склада</button></div>';
    }
    g.innerHTML = html;
}

function selectCluster(id) {
    S.selectedCluster = S.clusters.find(function(c) { return c.id === id; });
    S.selectedWarehouse = null;
    S.warehouses = [];
    renderClustersGrid();
}

// STEP 2: Warehouse selection
function renderStepWarehouse(sc) {
    sc.innerHTML = '<div class="card"><div class="card-header"><div class="card-title">🏭 Выберите склад</div>' +
        '<button class="btn btn-default" onclick="loadWarehouses()">🔄 Обновить</button></div>' +
        '<div class="card-body" id="warehouses-grid"><div class="loading"><div class="spinner"></div><div class="loading-text">Загрузка складов...</div></div></div></div>';
    
    loadWarehouses();
}

function loadWarehouses() {
    document.getElementById('warehouses-grid').innerHTML = '<div class="loading"><div class="spinner"></div><div class="loading-text">Загрузка складов...</div></div>';
    api('/v1/warehouse/fbo/list', { cluster_id: S.selectedCluster ? S.selectedCluster.id : undefined }).then(function(d) {
        if (d.error) { toast('Ошибка: ' + d.message, 'error'); return; }
        S.warehouses = d.warehouses || d.result || [];
        renderWarehousesGrid();
        toast('Загружено ' + S.warehouses.length + ' складов', 'success');
    });
}

function renderWarehousesGrid() {
    var g = document.getElementById('warehouses-grid');
    if (!S.warehouses.length) {
        g.innerHTML = '<div class="empty-state"><div class="empty-icon">🏭</div><div class="empty-title">Нет доступных складов</div><div class="empty-text">Попробуйте выбрать другой кластер</div></div>';
        return;
    }
    var html = '<div class="grid grid-2">';
    S.warehouses.forEach(function(wh) {
        var selected = S.selectedWarehouse && S.selectedWarehouse.id === wh.id ? 'selected' : '';
        var isOpen = wh.is_available !== false;
        html += '<div class="warehouse-card ' + selected + '" onclick="selectWarehouse(\'' + wh.id + '\')">' +
            '<div class="warehouse-name">' + (wh.name || 'Склад ' + wh.id) + '</div>' +
            '<div class="warehouse-address">' + (wh.address || wh.city || 'Адрес не указан') + '</div>' +
            '<span class="warehouse-status ' + (isOpen ? 'open' : 'closed') + '">' + (isOpen ? '✓ Доступен' : '✗ Закрыт') + '</span></div>';
    });
    html += '</div>';
    if (S.selectedWarehouse) {
        html += '<div style="margin-top:24px;display:flex;justify-content:space-between">' +
            '<button class="btn btn-default" onclick="prevStep()">← Назад</button>' +
            '<button class="btn btn-primary btn-lg" onclick="nextStep()">Далее → Товары</button></div>';
    }
    g.innerHTML = html;
}

function selectWarehouse(id) {
    S.selectedWarehouse = S.warehouses.find(function(w) { return w.id == id; });
    renderWarehousesGrid();
}

// STEP 3: Products
function renderStepProducts(sc) {
    sc.innerHTML = '<div class="card"><div class="card-header"><div class="card-title">📦 Выберите товары для поставки</div>' +
        '<button class="btn btn-default" onclick="loadProducts()">🔄 Загрузить товары</button></div>' +
        '<div class="card-body" id="products-container"><div class="loading"><div class="spinner"></div><div class="loading-text">Загрузка товаров...</div></div></div></div>';
    
    if (!S.products.length) loadProducts();
    else renderProductsTable();
}

function loadProducts() {
    document.getElementById('products-container').innerHTML = '<div class="loading"><div class="spinner"></div><div class="loading-text">Загрузка товаров...</div></div>';
    api('/v2/product/list', { filter: { visibility: 'ALL' }, limit: 100 }).then(function(d) {
        if (d.error) { toast('Ошибка: ' + d.message, 'error'); return; }
        var items = d.result ? d.result.items : [];
        if (!items.length) {
            renderProductsTable();
            return;
        }
        // Get detailed info
        var ids = items.map(function(i) { return i.product_id; });
        api('/v2/product/info/list', { product_id: ids }).then(function(info) {
            S.products = info.result ? info.result.items : items;
            renderProductsTable();
            toast('Загружено ' + S.products.length + ' товаров', 'success');
        });
    });
}

function renderProductsTable() {
    var pc = document.getElementById('products-container');
    if (!S.products.length) {
        pc.innerHTML = '<div class="empty-state"><div class="empty-icon">📦</div><div class="empty-title">Нет товаров</div></div>';
        return;
    }

    var selectedCount = Object.keys(S.selectedProducts).filter(function(k) { return S.selectedProducts[k] > 0; }).length;
    var totalQty = Object.values(S.selectedProducts).reduce(function(a, b) { return a + (b || 0); }, 0);

    var html = '<div class="info-banner"><span class="info-banner-icon">💡</span><div class="info-banner-text">Укажите количество товаров для поставки. Выбрано товаров: <strong>' + selectedCount + '</strong>, общее количество: <strong>' + totalQty + '</strong> шт.</div></div>';
    
    html += '<table class="product-table"><thead><tr><th style="width:60px"></th><th>Товар</th><th style="width:100px">Артикул</th><th style="width:100px">Остаток FBO</th><th style="width:120px">Количество</th></tr></thead><tbody>';
    
    S.products.forEach(function(p) {
        var pid = p.id || p.product_id;
        var qty = S.selectedProducts[pid] || 0;
        var fboStock = 0;
        if (p.stocks) {
            var fbo = p.stocks.find(function(s) { return s.type === 'fbo'; });
            if (fbo) fboStock = fbo.present || 0;
        }
        html += '<tr>' +
            '<td><div class="product-img" style="display:flex;align-items:center;justify-content:center;font-size:24px">📦</div></td>' +
            '<td><div class="product-name">' + (p.name || 'Товар').slice(0, 60) + '</div><div class="product-sku">ID: ' + pid + '</div></td>' +
            '<td>' + (p.offer_id || '-') + '</td>' +
            '<td>' + fboStock + ' шт</td>' +
            '<td><input type="number" class="qty-input" value="' + qty + '" min="0" max="9999" onchange="setProductQty(' + pid + ', this.value)"></td></tr>';
    });
    html += '</tbody></table>';

    html += '<div style="margin-top:24px;display:flex;justify-content:space-between">' +
        '<button class="btn btn-default" onclick="prevStep()">← Назад</button>' +
        '<button class="btn btn-primary btn-lg" onclick="nextStep()" ' + (totalQty === 0 ? 'disabled' : '') + '>Далее → Выбор времени</button></div>';
    
    pc.innerHTML = html;
}

function setProductQty(pid, val) {
    S.selectedProducts[pid] = parseInt(val) || 0;
    if (S.selectedProducts[pid] === 0) delete S.selectedProducts[pid];
    // Update button state
    var totalQty = Object.values(S.selectedProducts).reduce(function(a, b) { return a + (b || 0); }, 0);
    var btn = document.querySelector('#products-container .btn-primary');
    if (btn) btn.disabled = totalQty === 0;
}

// STEP 4: Timeslot
function renderStepTimeslot(sc) {
    sc.innerHTML = '<div class="card"><div class="card-header"><div class="card-title">📅 Выберите дату и время поставки</div></div>' +
        '<div class="card-body" id="timeslots-container"><div class="loading"><div class="spinner"></div><div class="loading-text">Создание черновика и загрузка таймслотов...</div></div></div></div>';
    
    createDraftAndLoadTimeslots();
}

function createDraftAndLoadTimeslots() {
    // First create draft
    var products = Object.keys(S.selectedProducts).map(function(pid) {
        return { sku: parseInt(pid), quantity: S.selectedProducts[pid] };
    });
    
    api('/v1/draft/create', {
        warehouse_id: S.selectedWarehouse ? S.selectedWarehouse.id : undefined,
        items: products
    }).then(function(d) {
        if (d.error) {
            document.getElementById('timeslots-container').innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><div class="empty-title">Ошибка создания черновика</div><div class="empty-text">' + d.message + '</div></div>';
            return;
        }
        S.draftId = d.draft_id || d.operation_id;
        toast('Черновик создан: ' + S.draftId, 'success');
        
        // Wait and check status, then load timeslots
        setTimeout(function() { loadTimeslots(); }, 1000);
    });
}

function loadTimeslots() {
    api('/v1/draft/timeslot/info', { draft_id: S.draftId }).then(function(d) {
        if (d.error) {
            document.getElementById('timeslots-container').innerHTML = '<div class="empty-state"><div class="empty-icon">📅</div><div class="empty-title">Ошибка загрузки таймслотов</div><div class="empty-text">' + d.message + '</div></div>';
            return;
        }
        renderTimeslotsGrid(d.timeslots || d.result || []);
    });
}

function renderTimeslotsGrid(timeslots) {
    var tc = document.getElementById('timeslots-container');
    
    if (!timeslots.length) {
        // Generate mock timeslots for demo
        timeslots = [];
        var now = new Date();
        for (var i = 1; i <= 7; i++) {
            var d = new Date(now.getTime() + i * 24 * 60 * 60 * 1000);
            timeslots.push({
                date: d.toISOString().split('T')[0],
                time_from: '09:00',
                time_to: '18:00',
                available: i !== 3
            });
        }
    }

    var html = '<div class="timeslot-grid">';
    timeslots.forEach(function(ts, idx) {
        var selected = S.selectedTimeslot && S.selectedTimeslot.date === ts.date ? 'selected' : '';
        var unavailable = ts.available === false ? 'unavailable' : '';
        var dateStr = new Date(ts.date).toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'short' });
        html += '<div class="timeslot-card ' + selected + ' ' + unavailable + '" onclick="selectTimeslot(' + idx + ')">' +
            '<div class="timeslot-date">' + dateStr + '</div>' +
            '<div class="timeslot-time">' + (ts.time_from || '09:00') + ' - ' + (ts.time_to || '18:00') + '</div>' +
            '<div class="timeslot-capacity">' + (ts.available === false ? 'Недоступно' : 'Доступно') + '</div></div>';
    });
    html += '</div>';

    html += '<div style="margin-top:24px;display:flex;justify-content:space-between">' +
        '<button class="btn btn-default" onclick="prevStep()">← Назад</button>' +
        '<button class="btn btn-primary btn-lg" onclick="nextStep()" ' + (!S.selectedTimeslot ? 'disabled' : '') + '>Далее → Грузоместа</button></div>';
    
    tc.innerHTML = html;
    
    // Store timeslots for selection
    S.availableTimeslots = timeslots;
}

function selectTimeslot(idx) {
    S.selectedTimeslot = S.availableTimeslots[idx];
    if (S.selectedTimeslot.available === false) {
        toast('Этот слот недоступен', 'warning');
        S.selectedTimeslot = null;
        return;
    }
    renderTimeslotsGrid(S.availableTimeslots);
}

// STEP 5: Cargoes
function renderStepCargoes(sc) {
    var totalQty = Object.values(S.selectedProducts).reduce(function(a, b) { return a + (b || 0); }, 0);
    
    var html = '<div class="card"><div class="card-header"><div class="card-title">📤 Формирование грузомест</div>' +
        '<div style="display:flex;gap:8px"><button class="btn btn-default" onclick="addCargo(\'box\')">📦 + Коробка</button>' +
        '<button class="btn btn-default" onclick="addCargo(\'pallet\')">🎁 + Палета</button></div></div>' +
        '<div class="card-body">';

    html += '<div class="info-banner"><span class="info-banner-icon">📋</span><div class="info-banner-text">' +
        'Всего товаров: <strong>' + totalQty + ' шт</strong>. Распределите товары по грузоместам (коробкам или палетам). ' +
        'С 3 сентября 2025 для бесплатной приёмки используйте <strong>моногрузоместа</strong> (один SKU на коробку).</div></div>';

    html += '<div id="cargoes-list">';
    if (!S.cargoes.length) {
        html += '<div class="empty-state"><div class="empty-icon">📤</div><div class="empty-title">Нет грузомест</div><div class="empty-text">Добавьте коробки или палеты</div></div>';
    } else {
        S.cargoes.forEach(function(cargo, idx) {
            var itemsInCargo = Object.values(cargo.items || {}).reduce(function(a, b) { return a + b; }, 0);
            var isFilled = itemsInCargo > 0;
            html += '<div class="cargo-box ' + (isFilled ? 'filled' : '') + '">' +
                '<div class="cargo-header"><div class="cargo-title">' +
                '<span class="cargo-type ' + cargo.type + '">' + (cargo.type === 'pallet' ? '🎁 Палета' : '📦 Коробка') + ' #' + (idx + 1) + '</span>' +
                '<span style="margin-left:12px;color:#666;font-size:13px">' + itemsInCargo + ' шт</span></div>' +
                '<div><button class="btn btn-default" style="padding:8px 12px" onclick="editCargo(' + idx + ')">✏️</button> ' +
                '<button class="btn btn-danger" style="padding:8px 12px" onclick="removeCargo(' + idx + ')">🗑️</button></div></div>';
            
            if (isFilled) {
                html += '<div class="cargo-items">';
                Object.keys(cargo.items).forEach(function(pid) {
                    var p = S.products.find(function(pr) { return (pr.id || pr.product_id) == pid; });
                    var name = p ? (p.name || '').slice(0, 30) : 'Товар ' + pid;
                    html += '<div class="cargo-item"><span>' + name + '</span><span class="cargo-item-qty">× ' + cargo.items[pid] + '</span></div>';
                });
                html += '</div>';
            }
            html += '</div>';
        });
    }
    html += '</div>';

    // Summary
    var distributed = 0;
    S.cargoes.forEach(function(c) {
        Object.values(c.items || {}).forEach(function(q) { distributed += q; });
    });
    var remaining = totalQty - distributed;

    html += '<div class="summary-box" style="margin-top:20px">' +
        '<div class="summary-row"><span class="summary-label">Всего товаров:</span><span class="summary-value">' + totalQty + ' шт</span></div>' +
        '<div class="summary-row"><span class="summary-label">Распределено:</span><span class="summary-value" style="color:#00c752">' + distributed + ' шт</span></div>' +
        '<div class="summary-row"><span class="summary-label">Осталось распределить:</span><span class="summary-value" style="color:' + (remaining > 0 ? '#ff4d4f' : '#00c752') + '">' + remaining + ' шт</span></div>' +
        '<div class="summary-row"><span class="summary-label">Грузомест:</span><span class="summary-value">' + S.cargoes.length + '</span></div></div>';

    html += '<div style="margin-top:24px;display:flex;justify-content:space-between">' +
        '<button class="btn btn-default" onclick="prevStep()">← Назад</button>' +
        '<button class="btn btn-primary btn-lg" onclick="createSupplyOrder()" ' + (remaining !== 0 || !S.cargoes.length ? 'disabled' : '') + '>✅ Создать заявку</button></div>';
    
    html += '</div></div>';
    sc.innerHTML = html;
}

function addCargo(type) {
    S.cargoes.push({ type: type, items: {} });
    renderStep();
}

function removeCargo(idx) {
    S.cargoes.splice(idx, 1);
    renderStep();
}

function editCargo(idx) {
    var cargo = S.cargoes[idx];
    var html = '<div style="max-height:400px;overflow:auto">';
    
    Object.keys(S.selectedProducts).forEach(function(pid) {
        var p = S.products.find(function(pr) { return (pr.id || pr.product_id) == pid; });
        var name = p ? (p.name || 'Товар').slice(0, 50) : 'Товар ' + pid;
        var maxQty = S.selectedProducts[pid];
        var currentQty = cargo.items[pid] || 0;
        
        // Calculate already distributed in other cargoes
        var otherDistributed = 0;
        S.cargoes.forEach(function(c, i) {
            if (i !== idx) otherDistributed += (c.items[pid] || 0);
        });
        var available = maxQty - otherDistributed;
        
        html += '<div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid #f0f0f0">' +
            '<div><div style="font-weight:500">' + name + '</div><div style="font-size:12px;color:#999">Доступно: ' + available + ' из ' + maxQty + '</div></div>' +
            '<input type="number" class="qty-input" id="cargo-qty-' + pid + '" value="' + currentQty + '" min="0" max="' + available + '"></div>';
    });
    html += '</div>';
    
    document.getElementById('modal-title').textContent = (cargo.type === 'pallet' ? '🎁 Палета' : '📦 Коробка') + ' #' + (idx + 1);
    document.getElementById('modal-body').innerHTML = html;
    document.getElementById('modal-footer').innerHTML = '<button class="btn btn-default" onclick="closeModal()">Отмена</button>' +
        '<button class="btn btn-success" onclick="saveCargoItems(' + idx + ')">💾 Сохранить</button>';
    document.getElementById('modal').classList.add('active');
}

function saveCargoItems(idx) {
    var cargo = S.cargoes[idx];
    cargo.items = {};
    Object.keys(S.selectedProducts).forEach(function(pid) {
        var input = document.getElementById('cargo-qty-' + pid);
        if (input) {
            var val = parseInt(input.value) || 0;
            if (val > 0) cargo.items[pid] = val;
        }
    });
    closeModal();
    renderStep();
}

function createSupplyOrder() {
    var btn = document.querySelector('#step-content .btn-primary');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Создание заявки...'; }
    
    // Create supply from draft
    api('/v1/draft/supply/create', {
        draft_id: S.draftId,
        timeslot: S.selectedTimeslot
    }).then(function(d) {
        if (d.error) {
            toast('Ошибка: ' + d.message, 'error');
            if (btn) { btn.disabled = false; btn.textContent = '✅ Создать заявку'; }
            return;
        }
        S.supplyId = d.supply_id || d.order_id;
        toast('Заявка создана: ' + S.supplyId, 'success');
        
        // Now create cargoes
        createCargoesForSupply();
    });
}

function createCargoesForSupply() {
    var cargoesData = S.cargoes.map(function(c, idx) {
        return {
            cargo_type: c.type === 'pallet' ? 'PALLET' : 'BOX',
            items: Object.keys(c.items).map(function(pid) {
                return { sku: parseInt(pid), quantity: c.items[pid] };
            })
        };
    });
    
    api('/v1/cargoes/create', {
        supply_id: S.supplyId,
        cargoes: cargoesData,
        delete_current_version: true
    }).then(function(d) {
        if (d.error) {
            toast('Ошибка создания грузомест: ' + d.message, 'error');
            return;
        }
        toast('Грузоместа добавлены', 'success');
        S.step = 6;
        renderStep();
    });
}

// STEP 6: Labels
function renderStepLabels(sc) {
    var html = '<div class="card"><div class="card-header"><div class="card-title">🏷️ Этикетки для грузомест</div></div>' +
        '<div class="card-body">';
    
    html += '<div class="empty-state" style="padding:40px"><div class="empty-icon">✅</div>' +
        '<div class="empty-title">Заявка на поставку создана!</div>' +
        '<div class="empty-text">Номер заявки: <strong>' + (S.supplyId || S.draftId || 'N/A') + '</strong></div>' +
        '<div style="margin-top:24px;display:flex;gap:12px;justify-content:center">' +
        '<button class="btn btn-primary btn-lg" onclick="generateLabels()">🏷️ Сгенерировать этикетки</button>' +
        '<button class="btn btn-success btn-lg" onclick="showPage(\'supplies\')">📋 К списку поставок</button></div></div>';
    
    html += '<div id="labels-result"></div>';
    html += '</div></div>';
    
    html += '<div style="margin-top:24px"><button class="btn btn-success btn-lg" onclick="resetAndCreateNew()">➕ Создать новую поставку</button></div>';
    
    sc.innerHTML = html;
}

function generateLabels() {
    var lr = document.getElementById('labels-result');
    lr.innerHTML = '<div class="loading"><div class="spinner"></div><div class="loading-text">Генерация этикеток...</div></div>';
    
    api('/v1/cargoes-label/create', { supply_order_id: S.supplyId }).then(function(d) {
        if (d.error) {
            lr.innerHTML = '<div class="info-banner" style="background:#fff1f0;border-color:#ffa39e"><span class="info-banner-icon" style="color:#ff4d4f">❌</span><div class="info-banner-text" style="color:#ff4d4f">Ошибка: ' + d.message + '</div></div>';
            return;
        }
        var opId = d.operation_id;
        toast('Генерация запущена', 'success');
        
        // Poll for result
        setTimeout(function() { checkLabelsStatus(opId); }, 2000);
    });
}

function checkLabelsStatus(opId) {
    api('/v1/cargoes-label/get', { operation_id: opId }).then(function(d) {
        if (d.error || d.status === 'pending') {
            setTimeout(function() { checkLabelsStatus(opId); }, 2000);
            return;
        }
        
        var fileGuid = d.file_guid || d.uid;
        if (fileGuid) {
            document.getElementById('labels-result').innerHTML = 
                '<div class="info-banner" style="background:#f6ffed;border-color:#b7eb8f">' +
                '<span class="info-banner-icon" style="color:#52c41a">✅</span>' +
                '<div class="info-banner-text" style="color:#52c41a">Этикетки готовы! ' +
                '<a href="/labels/' + fileGuid + '" target="_blank" class="btn btn-success" style="margin-left:12px">📥 Скачать PDF</a></div></div>';
            toast('Этикетки готовы!', 'success');
        } else {
            document.getElementById('labels-result').innerHTML = 
                '<div class="info-banner"><span class="info-banner-icon">ℹ️</span><div class="info-banner-text">Статус: ' + (d.status || 'неизвестно') + '</div></div>';
        }
    });
}

function resetAndCreateNew() {
    S.step = 1;
    S.selectedCluster = null;
    S.selectedWarehouse = null;
    S.selectedProducts = {};
    S.selectedTimeslot = null;
    S.cargoes = [];
    S.draftId = null;
    S.supplyId = null;
    render();
}

function nextStep() {
    S.step++;
    renderStep();
}

function prevStep() {
    S.step--;
    renderStep();
}

// ==================== SUPPLIES LIST PAGE ====================
function renderSupplies(c) {
    c.innerHTML = '<div class="page-title">📋 Мои поставки FBO</div>' +
        '<div class="stat-grid" id="supplies-stats"></div>' +
        '<div class="card"><div class="card-header"><div class="card-title">Список заявок</div>' +
        '<button class="btn btn-primary" onclick="loadSupplies()">🔄 Обновить</button></div>' +
        '<div class="card-body" id="supplies-list"><div class="loading"><div class="spinner"></div><div class="loading-text">Загрузка поставок...</div></div></div></div>';
    
    loadSupplies();
}

function loadSupplies() {
    document.getElementById('supplies-list').innerHTML = '<div class="loading"><div class="spinner"></div><div class="loading-text">Загрузка поставок...</div></div>';
    
    api('/v2/supply-order/list', { filter: {} }).then(function(d) {
        if (d.error) { toast('Ошибка: ' + d.message, 'error'); return; }
        S.supplies = d.supply_orders || d.result || [];
        renderSuppliesList();
        document.getElementById('badge-supplies').textContent = S.supplies.length;
    });
}

function renderSuppliesList() {
    var sl = document.getElementById('supplies-list');
    
    // Stats
    var stats = { total: S.supplies.length, filling: 0, ready: 0, completed: 0 };
    S.supplies.forEach(function(s) {
        if (s.state === 'ORDER_STATE_DATA_FILLING') stats.filling++;
        else if (s.state === 'ORDER_STATE_READY_TO_SUPPLY') stats.ready++;
        else if (s.state === 'ORDER_STATE_COMPLETED' || s.state === 'ORDER_STATE_ACCEPTED') stats.completed++;
    });
    
    document.getElementById('supplies-stats').innerHTML = 
        '<div class="stat-card"><div class="stat-value">' + stats.total + '</div><div class="stat-label">Всего</div></div>' +
        '<div class="stat-card warning"><div class="stat-value">' + stats.filling + '</div><div class="stat-label">В работе</div></div>' +
        '<div class="stat-card"><div class="stat-value">' + stats.ready + '</div><div class="stat-label">Готовы</div></div>' +
        '<div class="stat-card success"><div class="stat-value">' + stats.completed + '</div><div class="stat-label">Завершены</div></div>';
    
    if (!S.supplies.length) {
        sl.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div><div class="empty-title">Нет поставок</div><div class="empty-text">Создайте первую поставку</div></div>';
        return;
    }
    
    var html = '<div class="supply-list">';
    S.supplies.forEach(function(s) {
        var stateClass = 'status-draft';
        var stateText = s.state || 'Неизвестно';
        if (s.state === 'ORDER_STATE_DATA_FILLING') { stateClass = 'status-filling'; stateText = 'Заполнение'; }
        else if (s.state === 'ORDER_STATE_READY_TO_SUPPLY') { stateClass = 'status-ready'; stateText = 'Готова'; }
        else if (s.state === 'ORDER_STATE_ACCEPTED_AT_SUPPLY_WAREHOUSE') { stateClass = 'status-accepted'; stateText = 'Принята'; }
        else if (s.state === 'ORDER_STATE_COMPLETED') { stateClass = 'status-completed'; stateText = 'Завершена'; }
        else if (s.state === 'ORDER_STATE_CANCELLED') { stateClass = 'status-cancelled'; stateText = 'Отменена'; }
        
        html += '<div class="supply-card">' +
            '<div class="supply-id">#' + (s.supply_order_id || s.id) + '</div>' +
            '<div class="supply-warehouse">' + (s.warehouse_name || 'Склад') + '<small>' + (s.warehouse_city || '') + '</small></div>' +
            '<div class="supply-date">' + formatDate(s.timeslot_date || s.created_at) + '</div>' +
            '<div class="supply-items">' + (s.items_count || '?') + ' товаров</div>' +
            '<div><span class="supply-status ' + stateClass + '">' + stateText + '</span></div>' +
            '<div><button class="btn btn-default" style="padding:8px 12px" onclick="viewSupply(\'' + (s.supply_order_id || s.id) + '\')">👁️</button></div></div>';
    });
    html += '</div>';
    sl.innerHTML = html;
}

function viewSupply(id) {
    api('/v2/supply-order/get', { supply_order_id: parseInt(id) }).then(function(d) {
        if (d.error) { toast('Ошибка: ' + d.message, 'error'); return; }
        var s = d.result || d;
        
        var html = '<div style="display:grid;gap:16px">' +
            '<div><strong>ID:</strong> ' + (s.supply_order_id || s.id) + '</div>' +
            '<div><strong>Склад:</strong> ' + (s.warehouse_name || 'N/A') + '</div>' +
            '<div><strong>Статус:</strong> ' + (s.state || 'N/A') + '</div>' +
            '<div><strong>Дата:</strong> ' + formatDate(s.timeslot_date || s.created_at) + '</div>' +
            '<div><strong>Товаров:</strong> ' + (s.items_count || '?') + '</div></div>';
        
        document.getElementById('modal-title').textContent = 'Поставка #' + (s.supply_order_id || s.id);
        document.getElementById('modal-body').innerHTML = html;
        document.getElementById('modal-footer').innerHTML = '<button class="btn btn-default" onclick="closeModal()">Закрыть</button>' +
            '<button class="btn btn-danger" onclick="cancelSupply(\'' + (s.supply_order_id || s.id) + '\')">❌ Отменить</button>';
        document.getElementById('modal').classList.add('active');
    });
}

function cancelSupply(id) {
    if (!confirm('Отменить поставку #' + id + '?')) return;
    api('/v1/supply-order/cancel', { supply_order_id: parseInt(id) }).then(function(d) {
        if (d.error) { toast('Ошибка: ' + d.message, 'error'); return; }
        toast('Поставка отменена', 'success');
        closeModal();
        loadSupplies();
    });
}

// ==================== PRODUCTS PAGE ====================
function renderProducts(c) {
    c.innerHTML = '<div class="page-title">📦 Мои товары</div>' +
        '<div class="card"><div class="card-header"><div class="card-title">Каталог товаров</div>' +
        '<button class="btn btn-primary" onclick="loadAllProducts()">🔄 Обновить</button></div>' +
        '<div class="card-body" id="all-products"><div class="loading"><div class="spinner"></div><div class="loading-text">Загрузка...</div></div></div></div>';
    
    loadAllProducts();
}

function loadAllProducts() {
    document.getElementById('all-products').innerHTML = '<div class="loading"><div class="spinner"></div><div class="loading-text">Загрузка товаров...</div></div>';
    api('/v2/product/list', { filter: { visibility: 'ALL' }, limit: 100 }).then(function(d) {
        if (d.error) { toast('Ошибка: ' + d.message, 'error'); return; }
        var items = d.result ? d.result.items : [];
        renderAllProductsList(items);
    });
}

function renderAllProductsList(items) {
    var ap = document.getElementById('all-products');
    if (!items.length) {
        ap.innerHTML = '<div class="empty-state"><div class="empty-icon">📦</div><div class="empty-title">Нет товаров</div></div>';
        return;
    }
    
    var html = '<table class="product-table"><thead><tr><th>Товар</th><th>Артикул</th><th>ID</th><th>Статус</th></tr></thead><tbody>';
    items.forEach(function(p) {
        html += '<tr><td><div class="product-name">' + (p.name || 'Товар').slice(0, 60) + '</div></td>' +
            '<td>' + (p.offer_id || '-') + '</td>' +
            '<td>' + (p.product_id || '-') + '</td>' +
            '<td><span style="color:' + (p.is_fbo_visible ? '#00c752' : '#ff4d4f') + '">' + (p.is_fbo_visible ? '✓ FBO' : '✗') + '</span></td></tr>';
    });
    html += '</tbody></table>';
    ap.innerHTML = html;
}

// ==================== LOGS PAGE ====================
function renderLogs(c) {
    c.innerHTML = '<div class="page-title">📝 Логи API</div>' +
        '<div class="card"><div class="card-header"><div class="card-title">История запросов</div>' +
        '<button class="btn btn-default" onclick="render()">🔄 Обновить</button></div>' +
        '<div class="card-body" id="logs-list"></div></div>';
    
    fetch('/logs').then(function(r) { return r.json(); }).then(function(logs) {
        var ll = document.getElementById('logs-list');
        if (!logs.length) {
            ll.innerHTML = '<div class="empty-state"><div class="empty-icon">📝</div><div class="empty-title">Логи пусты</div></div>';
            return;
        }
        var html = '<table class="product-table"><thead><tr><th>Время</th><th>Endpoint</th><th>Статус</th><th>Сообщение</th></tr></thead><tbody>';
        logs.slice(0, 100).forEach(function(l) {
            var color = l.level === 'success' ? '#00c752' : l.level === 'error' ? '#ff4d4f' : '#666';
            html += '<tr><td>' + l.time + '</td><td style="color:#005bff">' + l.endpoint + '</td>' +
                '<td style="color:' + color + '">' + l.level + '</td><td style="color:#666;max-width:300px;overflow:hidden;text-overflow:ellipsis">' + l.message + '</td></tr>';
        });
        html += '</tbody></table>';
        ll.innerHTML = html;
    });
}

// ==================== UTILS ====================
function formatDate(d) {
    if (!d) return '-';
    var dt = new Date(d);
    return dt.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function closeModal() {
    document.getElementById('modal').classList.remove('active');
}

function testConn() {
    setConn(null, 'Проверка...');
    api('/v1/warehouse/list', {}).then(function(d) {
        if (d.error) throw new Error();
        setConn(true, 'Подключено ✓');
    }).catch(function() { setConn(false, 'Ошибка'); });
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
            self.json_resp({"status": "ok", "version": "1.0"})
        elif self.path.startswith("/labels/"):
            # Download labels PDF
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
            endpoint = self.path[5:]  # Remove /ozon prefix
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
║     📦 OZON FBO Supply Manager v1.0            ║
╠════════════════════════════════════════════════╣
║  Полный цикл создания поставок FBO             ║
║                                                ║
║  🌐 http://localhost:{PORT:<24}║
╚════════════════════════════════════════════════╝
""")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

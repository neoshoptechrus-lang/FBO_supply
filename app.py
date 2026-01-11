#!/usr/bin/env python3
"""
OZON Manager Pro v8.0 - Ozon-style Interface
- Интерфейс как у Ozon
- Защита от повторных ответов
- Кнопка СТОП
- Вкладки: Все / Новые / Просмотренные / Обработанные
"""

import os, json, urllib.request, urllib.error, ssl
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
OZON_CLIENT_ID = os.environ.get("OZON_CLIENT_ID", "1321895")
OZON_API_KEY = os.environ.get("OZON_API_KEY", "310cded9-e724-4480-b95a-4d74bf152129")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")

OZON_API = "https://api-seller.ozon.ru"
CLAUDE_API = "https://api.anthropic.com/v1/messages"
LOGS = []

KNOWLEDGE_BASE = {
    "scripts": [
        {"id": 1, "triggers": ["синий", "синяя", "синее", "пленка", "плёнка", "голубой"], "problem": "Синяя плёнка", "solution": "На дисплее весов находится защитная плёнка синего цвета. Пожалуйста, аккуратно снимите её — под ней обычный дисплей."},
        {"id": 2, "triggers": ["неточно", "врут", "врёт", "неправильно", "погрешность"], "problem": "Неточные показания", "solution": "Для точных измерений установите весы на ровную твёрдую поверхность (плитка, ламинат). На ковре возможны погрешности."},
        {"id": 3, "triggers": ["показывают вес", "без нагрузки", "не ноль", "калибровка"], "problem": "Не обнуляются", "solution": "При первом включении весы должны стоять на ровной поверхности. Если держать в руках — калибровка будет некорректной."},
        {"id": 4, "triggers": ["не включаются", "не работают", "сломались", "брак"], "problem": "Не работают", "solution": "Проверьте батарейки или замените их. Если проблема сохранится — оформите возврат."},
        {"id": 5, "triggers": ["батарейки", "батареи", "питания"], "problem": "Батарейки", "solution": "Весы работают от стандартных батареек, которые можно приобрести в любом магазине."},
        {"id": 6, "triggers": ["упаковка", "помята", "мятая"], "problem": "Упаковка", "solution": "Приносим извинения за состояние упаковки. Если товар работает исправно — будем благодарны за понимание."}
    ]
}

def log(level, ep, msg):
    LOGS.insert(0, {"time": datetime.now().strftime("%H:%M:%S"), "level": level, "endpoint": ep, "message": msg})
    if len(LOGS) > 200: LOGS.pop()

def ozon_request(endpoint, body):
    headers = {"Content-Type": "application/json", "Client-Id": OZON_CLIENT_ID, "Api-Key": OZON_API_KEY}
    log("request", endpoint, "Sending...")
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(f"{OZON_API}{endpoint}", data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            result = json.loads(resp.read())
            log("success", endpoint, "OK")
            return result
    except Exception as e:
        log("error", endpoint, str(e)[:100])
        return {"error": True, "message": str(e)}

def claude_request(prompt):
    if not CLAUDE_API_KEY:
        return {"error": True, "message": "Claude API key not configured"}
    headers = {"Content-Type": "application/json", "x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01"}
    body = {"model": "claude-sonnet-4-20250514", "max_tokens": 300, "messages": [{"role": "user", "content": prompt}]}
    log("ai", "/claude", "Generating...")
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(CLAUDE_API, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            result = json.loads(resp.read())
            text = result.get("content", [{}])[0].get("text", "")
            log("success", "/claude", f"OK {len(text)}ch")
            return {"success": True, "response": text}
    except Exception as e:
        log("error", "/claude", str(e)[:100])
        return {"error": True, "message": str(e)}

def find_script(text, rating):
    text_lower = (text or "").lower()
    for s in KNOWLEDGE_BASE["scripts"]:
        for t in s["triggers"]:
            if t in text_lower:
                return s
    return None

def build_prompt(review, script=None):
    r = review.get("rating", 5)
    txt = review.get("text", "")
    prod = review.get("product", {}).get("name", "товар")
    p = f"Напиши короткий ответ на отзыв покупателя. Рейтинг: {r}/5. Товар: {prod}. Отзыв: {txt}. "
    if script:
        p += f"Используй решение: {script['solution']}. "
    if r >= 4:
        p += "Поблагодари за покупку. "
    else:
        p += "Извинись и предложи решение. "
    p += "2-3 предложения. Без эмодзи. Только текст ответа:"
    return p


HTML = r'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OZON Manager Pro v8</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f2f3f5;color:#1a1a1a;font-size:14px}
.header{background:#fff;border-bottom:1px solid #e4e4e4;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.logo{font-size:20px;font-weight:700;color:#005bff}
.logo span{color:#00c752;font-size:12px;margin-left:8px}
.conn{display:flex;align-items:center;gap:6px;font-size:12px;color:#666}
.conn-dot{width:8px;height:8px;border-radius:50%;background:#00c752}
.conn-dot.err{background:#ff4d4f}
.conn-dot.load{background:#faad14;animation:pulse 1s infinite}
@keyframes pulse{50%{opacity:.4}}
.container{max-width:1400px;margin:0 auto;padding:20px}
.page-title{font-size:24px;font-weight:600;margin-bottom:20px;display:flex;align-items:center;gap:12px}
.tabs{display:flex;gap:0;margin-bottom:20px;border-bottom:2px solid #e4e4e4}
.tab{padding:12px 20px;font-size:14px;font-weight:500;color:#666;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;transition:all .2s}
.tab:hover{color:#005bff}
.tab.active{color:#005bff;border-bottom-color:#005bff}
.tab .cnt{background:#f2f3f5;color:#666;padding:2px 8px;border-radius:10px;font-size:12px;margin-left:6px}
.tab.active .cnt{background:#005bff;color:#fff}
.toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:12px}
.search{display:flex;gap:8px;align-items:center}
.search input{padding:10px 14px;border:1px solid #d9d9d9;border-radius:8px;font-size:13px;width:280px}
.search input:focus{outline:none;border-color:#005bff}
.btn{padding:10px 18px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;transition:all .2s;display:inline-flex;align-items:center;gap:6px}
.btn-primary{background:#005bff;color:#fff}
.btn-primary:hover{background:#0050e6}
.btn-success{background:#00c752;color:#fff}
.btn-success:hover{background:#00b348}
.btn-danger{background:#ff4d4f;color:#fff}
.btn-danger:hover{background:#e6393b}
.btn-default{background:#fff;color:#1a1a1a;border:1px solid #d9d9d9}
.btn-default:hover{border-color:#005bff;color:#005bff}
.btn:disabled{opacity:.5;cursor:not-allowed}
.card{background:#fff;border-radius:12px;box-shadow:0 1px 2px rgba(0,0,0,.06);margin-bottom:12px}
.review-row{display:grid;grid-template-columns:50px 1fr 90px 90px 50px 90px 50px;align-items:center;padding:14px 16px;border-bottom:1px solid #f2f3f5;gap:12px}
.review-row:last-child{border-bottom:none}
.review-row:hover{background:#fafafa}
.review-img{width:40px;height:40px;border-radius:6px;object-fit:cover;background:#f2f3f5}
.review-product{font-size:13px;font-weight:500}
.review-product small{display:block;color:#999;font-size:11px;font-weight:400}
.review-text{font-size:13px;color:#666;margin-top:4px}
.review-status{font-size:11px;padding:4px 10px;border-radius:4px;font-weight:500}
.status-new{background:#fff7e6;color:#fa8c16}
.status-viewed{background:#f0f5ff;color:#1890ff}
.status-done{background:#f6ffed;color:#52c41a}
.review-rating{display:flex;align-items:center;gap:2px}
.star{color:#fadb14;font-size:14px}
.review-date{font-size:12px;color:#999}
.review-actions .btn{padding:6px 10px;font-size:11px}
.stats-bar{display:flex;gap:20px;margin-bottom:20px;padding:16px 20px;background:#fff;border-radius:12px}
.stat-item{text-align:center}
.stat-value{font-size:28px;font-weight:700;color:#1a1a1a}
.stat-label{font-size:12px;color:#999}
.stat-item.warning .stat-value{color:#fa8c16}
.stat-item.success .stat-value{color:#52c41a}
.progress-panel{background:#fff;border-radius:12px;padding:20px;margin-bottom:20px}
.progress-bar{height:8px;background:#f2f3f5;border-radius:4px;overflow:hidden;margin:12px 0}
.progress-fill{height:100%;background:linear-gradient(90deg,#005bff,#00c752);transition:width .3s}
.progress-text{font-size:13px;color:#666}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;align-items:center;justify-content:center;z-index:1000}
.modal.active{display:flex}
.modal-content{background:#fff;border-radius:12px;width:600px;max-width:90%;max-height:80vh;overflow:auto}
.modal-header{padding:16px 20px;border-bottom:1px solid #e4e4e4;display:flex;justify-content:space-between;align-items:center}
.modal-header h3{font-size:18px;font-weight:600}
.modal-close{width:32px;height:32px;border-radius:8px;border:none;background:#f2f3f5;cursor:pointer;font-size:18px}
.modal-close:hover{background:#e4e4e4}
.modal-body{padding:20px}
.modal-footer{padding:16px 20px;border-top:1px solid #e4e4e4;display:flex;justify-content:flex-end;gap:8px}
.form-group{margin-bottom:16px}
.form-group label{display:block;font-size:13px;font-weight:500;margin-bottom:6px;color:#666}
.form-group textarea{width:100%;padding:12px;border:1px solid #d9d9d9;border-radius:8px;font-size:13px;min-height:100px;resize:vertical;font-family:inherit}
.form-group textarea:focus{outline:none;border-color:#005bff}
.script-tag{display:inline-block;padding:4px 8px;background:#fff7e6;color:#fa8c16;border-radius:4px;font-size:11px;font-weight:500;margin-bottom:8px}
.toast-container{position:fixed;bottom:20px;right:20px;z-index:1001}
.toast{padding:12px 20px;background:#1a1a1a;color:#fff;border-radius:8px;margin-top:8px;font-size:13px;animation:slideIn .2s}
.toast.success{background:#52c41a}
.toast.error{background:#ff4d4f}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}}
.empty{text-align:center;padding:60px 20px;color:#999}
.empty-icon{font-size:48px;margin-bottom:12px}
.nav{display:flex;gap:8px;margin-bottom:20px}
.nav-btn{padding:10px 16px;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;border:none;background:#fff;color:#666;border:1px solid #e4e4e4}
.nav-btn:hover{border-color:#005bff;color:#005bff}
.nav-btn.active{background:#005bff;color:#fff;border-color:#005bff}
.loading{text-align:center;padding:40px}
.spinner{width:32px;height:32px;border:3px solid #f2f3f5;border-top-color:#005bff;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="header">
<div class="logo">OZON Manager Pro <span>v8.0</span></div>
<div class="conn" id="conn"><div class="conn-dot load"></div><span>Проверка...</span></div>
</div>

<div class="container">
<div class="nav">
<button class="nav-btn active" onclick="showPage('reviews')">⭐ Отзывы</button>
<button class="nav-btn" onclick="showPage('knowledge')">📚 База знаний</button>
<button class="nav-btn" onclick="showPage('logs')">📋 Логи</button>
</div>

<div id="page-content"></div>
</div>

<div class="modal" id="modal">
<div class="modal-content">
<div class="modal-header"><h3 id="modal-title">Ответ на отзыв</h3><button class="modal-close" onclick="closeModal()">&times;</button></div>
<div class="modal-body" id="modal-body"></div>
<div class="modal-footer" id="modal-footer"></div>
</div>
</div>

<div class="toast-container" id="toasts"></div>

<script>
var S={page:"reviews",tab:"new",reviews:[],answered:{},stopFlag:false};

function toast(msg,type){var t=document.createElement("div");t.className="toast "+(type||"");t.textContent=msg;document.getElementById("toasts").appendChild(t);setTimeout(function(){t.remove()},3000)}
function setConn(ok,txt){document.getElementById("conn").innerHTML='<div class="conn-dot '+(ok?"":ok===false?"err":"load")+'"></div><span>'+txt+'</span>'}

function api(ep,body){return fetch("/ozon"+ep,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body||{})}).then(function(r){return r.json()})}
function smartAI(review){return fetch("/smart-ai",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(review)}).then(function(r){return r.json()})}

function showPage(p){
S.page=p;
document.querySelectorAll(".nav-btn").forEach(function(b,i){b.classList.toggle("active",["reviews","knowledge","logs"][i]===p)});
render();
}

function render(){
var c=document.getElementById("page-content");
if(S.page==="reviews")renderReviews(c);
else if(S.page==="knowledge")renderKnowledge(c);
else if(S.page==="logs")renderLogs(c);
}

function renderReviews(c){
c.innerHTML='<div class="page-title">⭐ Отзывы покупателей</div>'+
'<div class="stats-bar"><div class="stat-item"><div class="stat-value" id="st-total">-</div><div class="stat-label">Всего</div></div>'+
'<div class="stat-item warning"><div class="stat-value" id="st-new">-</div><div class="stat-label">Новые</div></div>'+
'<div class="stat-item success"><div class="stat-value" id="st-done">-</div><div class="stat-label">С ответом</div></div></div>'+
'<div class="tabs"><div class="tab active" data-tab="new">Новые <span class="cnt" id="cnt-new">0</span></div>'+
'<div class="tab" data-tab="all">Все <span class="cnt" id="cnt-all">0</span></div>'+
'<div class="tab" data-tab="done">С ответом <span class="cnt" id="cnt-done">0</span></div></div>'+
'<div class="toolbar"><div class="search"><input type="text" placeholder="Поиск по отзывам..." id="search-input" onkeyup="filterReviews()">'+
'<select id="rating-filter" onchange="filterReviews()" style="padding:10px;border:1px solid #d9d9d9;border-radius:8px"><option value="">Все оценки</option><option value="5">5 ⭐</option><option value="4">4 ⭐</option><option value="3">3 ⭐</option><option value="2">2 ⭐</option><option value="1">1 ⭐</option></select></div>'+
'<div style="display:flex;gap:8px"><button class="btn btn-primary" onclick="loadReviews()">🔄 Загрузить</button>'+
'<button class="btn btn-success" id="btn-auto" onclick="autoRespond()">🤖 Авто-ответ</button>'+
'<button class="btn btn-danger" id="btn-stop" onclick="stopAuto()" style="display:none">⏹ Стоп</button></div></div>'+
'<div id="progress-panel" style="display:none" class="progress-panel"><div class="progress-text" id="progress-text">Подготовка...</div><div class="progress-bar"><div class="progress-fill" id="progress-fill" style="width:0%"></div></div></div>'+
'<div class="card" id="reviews-list"><div class="review-row" style="background:#f9f9f9;font-weight:600;font-size:12px;color:#666"><div></div><div>Товар / Отзыв</div><div>Статус</div><div>Оценка</div><div>Отв.</div><div>Дата</div><div></div></div><div class="loading"><div class="spinner"></div>Нажмите "Загрузить"</div></div>';

document.querySelectorAll(".tab").forEach(function(t){t.onclick=function(){
document.querySelectorAll(".tab").forEach(function(x){x.classList.remove("active")});
t.classList.add("active");
S.tab=t.dataset.tab;
renderReviewsList();
}});
}

function loadReviews(){
var el=document.getElementById("reviews-list");
el.innerHTML='<div class="loading"><div class="spinner"></div>Загрузка отзывов...</div>';
S.reviews=[];
S.reviewIds={};
var maxPages=5;

function addReviews(revs,isAnswered){
revs.forEach(function(r){
var rid=r.id||r.review_id;
if(S.reviewIds[rid])return;
S.reviewIds[rid]=true;
r._answered=isAnswered;
S.reviews.push(r);
});
}

function loadBatch(isAnswered,offset,cb){
api("/v1/review/list",{sort_dir:"DESC",offset:offset,limit:100,is_answered:isAnswered}).then(function(d){
var revs=d.reviews||[];
addReviews(revs,isAnswered);
el.innerHTML='<div class="loading"><div class="spinner"></div>Загружено: '+S.reviews.length+'</div>';
if(revs.length===100&&offset<400){loadBatch(isAnswered,offset+100,cb)}
else{cb()}
}).catch(function(){cb()});
}

loadBatch(false,0,function(){
loadBatch(true,0,function(){
S.reviews.sort(function(a,b){return new Date(b.published_at)-new Date(a.published_at)});
updateStats();
renderReviewsList();
toast("Загружено "+S.reviews.length+" отзывов","success");
});
});
}

function updateStats(){
var total=S.reviews.length;
var newCnt=S.reviews.filter(function(r){return !hasResponse(r)}).length;
var doneCnt=total-newCnt;
document.getElementById("st-total").textContent=total;
document.getElementById("st-new").textContent=newCnt;
document.getElementById("st-done").textContent=doneCnt;
document.getElementById("cnt-all").textContent=total;
document.getElementById("cnt-new").textContent=newCnt;
document.getElementById("cnt-done").textContent=doneCnt;
}

function hasResponse(r){
if(r._answered===true)return true;
if(S.answered[r.id||r.review_id])return true;
return false;
}

function filterReviews(){renderReviewsList()}

function renderReviewsList(){
var el=document.getElementById("reviews-list");
var search=(document.getElementById("search-input").value||"").toLowerCase();
var rating=document.getElementById("rating-filter").value;
var list=S.reviews.filter(function(r){
if(S.tab==="new"&&hasResponse(r))return false;
if(S.tab==="done"&&!hasResponse(r))return false;
if(search&&(r.text||"").toLowerCase().indexOf(search)<0)return false;
if(rating&&r.rating!=rating)return false;
return true;
});
if(!list.length){el.innerHTML='<div class="empty"><div class="empty-icon">📭</div>Нет отзывов</div>';return}
var html='<div style="padding:8px 16px;background:#f9f9f9;font-size:12px;color:#999;border-bottom:1px solid #f2f3f5">Показано: '+list.length+' из '+S.reviews.length+'</div>';
list.slice(0,100).forEach(function(r,idx){
var i=S.reviews.indexOf(r);
var stars="";for(var s=0;s<5;s++)stars+='<span class="star">'+(s<r.rating?"★":"☆")+'</span>';
var hasResp=hasResponse(r);
var status=hasResp?'<span class="review-status status-done">Отвечен</span>':'<span class="review-status status-new">Новый</span>';
var prodName=r.product_name||r.product&&r.product.name||r.product&&r.product.offer_id||"Товар";
var prodSku=r.product&&r.product.offer_id||r.sku||"";
var respCount=hasResp?1:0;
html+='<div class="review-row" id="row-'+i+'">'+
'<div class="review-img" style="background:#f0f0f0;display:flex;align-items:center;justify-content:center;font-size:20px">📦</div>'+
'<div><div class="review-product">'+prodName.slice(0,55)+(prodName.length>55?"...":"")+'<small>'+prodSku+'</small></div>'+
'<div class="review-text">'+(r.text||"—").slice(0,100)+(r.text&&r.text.length>100?"...":"")+'</div></div>'+
status+'<div class="review-rating">'+stars+'</div>'+
'<div style="text-align:center;font-weight:600;color:'+(respCount>0?"#52c41a":"#999")+'">'+respCount+'</div>'+
'<div class="review-date">'+formatDate(r.published_at)+'</div>'+
'<div class="review-actions">'+(hasResp?'<button class="btn btn-default" onclick="viewResponse('+i+')">👁</button>':'<button class="btn btn-primary" onclick="openReply('+i+')">💬</button>')+'</div></div>';
});
el.innerHTML=html;
}

function formatDate(d){if(!d)return"-";var dt=new Date(d);return dt.toLocaleDateString("ru-RU",{day:"2-digit",month:"2-digit",year:"2-digit"})}

function openReply(i){
var r=S.reviews[i];
if(hasResponse(r)){toast("Уже есть ответ!","error");return}
document.getElementById("modal-title").textContent="Ответ на отзыв";
var stars="";for(var s=0;s<r.rating;s++)stars+="⭐";
document.getElementById("modal-body").innerHTML='<div style="margin-bottom:16px;padding:12px;background:#f9f9f9;border-radius:8px">'+
'<div style="margin-bottom:8px"><strong>'+stars+'</strong> '+(r.product&&r.product.name?r.product.name.slice(0,40):"")+'</div>'+
'<div style="color:#666">'+(r.text||"Без текста")+'</div></div>'+
'<div id="script-info"></div>'+
'<div class="form-group"><label>Ваш ответ:</label><textarea id="reply-text" placeholder="Введите ответ или нажмите Сгенерировать..."></textarea></div>';
document.getElementById("modal-footer").innerHTML='<button class="btn btn-default" onclick="closeModal()">Отмена</button>'+
'<button class="btn btn-primary" onclick="generateReply('+i+')">🤖 Сгенерировать</button>'+
'<button class="btn btn-success" onclick="sendReply('+i+')">✅ Отправить</button>';
document.getElementById("modal").classList.add("active");
}

function generateReply(i){
var r=S.reviews[i];
var txt=document.getElementById("reply-text");
txt.value="Генерация...";
txt.disabled=true;
smartAI(r).then(function(d){
txt.disabled=false;
if(d.error){txt.value="";toast("Ошибка: "+d.message,"error");return}
txt.value=d.response;
if(d.script)document.getElementById("script-info").innerHTML='<div class="script-tag">📚 '+d.script.problem+'</div>';
toast("Ответ сгенерирован","success");
}).catch(function(e){txt.disabled=false;txt.value="";toast("Ошибка","error")});
}

function sendReply(i){
var r=S.reviews[i];
var rid=r.id||r.review_id;
if(S.answered[rid]){toast("Уже отправлено!","error");return}
var txt=document.getElementById("reply-text").value;
if(!txt){toast("Введите текст","error");return}
api("/v1/review/comment/create",{review_id:rid,text:txt}).then(function(d){
if(d.error){toast("Ошибка: "+d.message,"error");return}
S.answered[rid]=true;
closeModal();
updateStats();
renderReviewsList();
toast("Ответ отправлен!","success");
});
}

function viewResponse(i){
var r=S.reviews[i];
var txt=r.comment?r.comment.text:(S.answered[r.id||r.review_id]?"Ответ отправлен":"");
document.getElementById("modal-title").textContent="Ответ на отзыв";
document.getElementById("modal-body").innerHTML='<div style="padding:12px;background:#f6ffed;border-radius:8px;border-left:3px solid #52c41a"><strong style="color:#52c41a">✅ Ваш ответ:</strong><p style="margin-top:8px">'+txt+'</p></div>';
document.getElementById("modal-footer").innerHTML='<button class="btn btn-default" onclick="closeModal()">Закрыть</button>';
document.getElementById("modal").classList.add("active");
}

function closeModal(){document.getElementById("modal").classList.remove("active")}

function autoRespond(){
var pending=S.reviews.filter(function(r){return !hasResponse(r)});
if(!pending.length){toast("Нет отзывов без ответа","success");return}
S.stopFlag=false;
document.getElementById("btn-auto").style.display="none";
document.getElementById("btn-stop").style.display="inline-flex";
document.getElementById("progress-panel").style.display="block";
var done=0,errs=0,total=Math.min(pending.length,50);
function next(idx){
if(S.stopFlag||idx>=total){
finish();
return;
}
var r=pending[idx];
var rid=r.id||r.review_id;
var pct=Math.round((idx/total)*100);
document.getElementById("progress-fill").style.width=pct+"%";
document.getElementById("progress-text").textContent="Обработка "+(idx+1)+" из "+total+"... ("+done+" отправлено, "+errs+" ошибок)";
smartAI(r).then(function(d){
if(d.error)throw new Error(d.message);
return api("/v1/review/comment/create",{review_id:rid,text:d.response});
}).then(function(res){
if(res.error)throw new Error(res.message);
S.answered[rid]=true;
done++;
var row=document.getElementById("row-"+S.reviews.indexOf(r));
if(row)row.style.opacity="0.5";
}).catch(function(){errs++}).finally(function(){
setTimeout(function(){next(idx+1)},2500);
});
}
function finish(){
document.getElementById("btn-auto").style.display="inline-flex";
document.getElementById("btn-stop").style.display="none";
document.getElementById("progress-fill").style.width="100%";
document.getElementById("progress-text").textContent="Готово! Отправлено: "+done+", ошибок: "+errs;
updateStats();
renderReviewsList();
toast("Авто-ответ завершён: "+done+" отправлено","success");
}
next(0);
}

function stopAuto(){
S.stopFlag=true;
toast("Остановка...","");
}

function renderKnowledge(c){
fetch("/knowledge").then(function(r){return r.json()}).then(function(kb){
var html='<div class="page-title">📚 База знаний</div><div class="card" style="padding:20px">';
kb.scripts.forEach(function(s){
html+='<div style="padding:16px;border:1px solid #e4e4e4;border-radius:8px;margin-bottom:12px">'+
'<div style="font-weight:600;margin-bottom:8px;color:#fa8c16">'+s.problem+'</div>'+
'<div style="margin-bottom:8px;display:flex;flex-wrap:wrap;gap:4px">';
s.triggers.forEach(function(t){html+='<span style="padding:2px 8px;background:#f2f3f5;border-radius:4px;font-size:11px">'+t+'</span>'});
html+='</div><div style="padding:10px;background:#f9f9f9;border-radius:6px;font-size:13px;color:#666">💡 '+s.solution+'</div></div>';
});
html+='</div>';
c.innerHTML=html;
});
}

function renderLogs(c){
fetch("/logs").then(function(r){return r.json()}).then(function(logs){
var html='<div class="page-title">📋 Логи API</div><div class="card">';
if(!logs.length)html+='<div class="empty">Логи пусты</div>';
else{
html+='<table style="width:100%;border-collapse:collapse;font-size:13px"><tr style="background:#f9f9f9"><th style="padding:10px;text-align:left">Время</th><th style="padding:10px;text-align:left">Endpoint</th><th style="padding:10px;text-align:left">Сообщение</th></tr>';
logs.slice(0,50).forEach(function(l){html+='<tr style="border-bottom:1px solid #f2f3f5"><td style="padding:10px">'+l.time+'</td><td style="padding:10px;color:#005bff">'+l.endpoint+'</td><td style="padding:10px;color:#666">'+l.message+'</td></tr>'});
html+='</table>';
}
html+='</div>';
c.innerHTML=html;
});
}

function testConn(){
setConn(null,"Проверка...");
api("/v1/warehouse/list",{}).then(function(d){
if(d.error)throw new Error();
setConn(true,"Подключено ✓");
}).catch(function(){setConn(false,"Ошибка")});
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
        elif self.path == "/knowledge":
            self.json_resp(KNOWLEDGE_BASE)
        elif self.path == "/health":
            self.json_resp({"status": "ok", "version": "8.0"})
        else:
            self.send_error(404)
    
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        if self.path.startswith("/ozon/"):
            self.json_resp(ozon_request(self.path[5:], body))
        elif self.path == "/smart-ai":
            script = find_script(body.get("text", ""), body.get("rating", 5))
            prompt = build_prompt(body, script)
            result = claude_request(prompt)
            if result.get("error"):
                self.json_resp(result)
            else:
                self.json_resp({"success": True, "response": result["response"], "script": {"problem": script["problem"]} if script else None})
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
    print(f"\n🚀 OZON Manager Pro v8.0\n📍 http://localhost:{PORT}\n")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

from flask import Flask, request, render_template_string, jsonify
import requests
import re
import json
import os
from datetime import datetime

app = Flask(__name__)

LLBOT_API = "http://127.0.0.1:3000"  # 改回 3000 端口

# 消息缓存文件
CACHE_FILE = "msg_cache.json"

# 加载历史消息
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

# 保存消息到文件
def save_cache(cache):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass

# 初始化缓存
msg_cache = load_cache()
MAX_MSG_PER_TARGET = 500

# ==================== 前端 HTML ====================
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>QQ 控制台</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: system-ui, sans-serif;
            background: #f0f2f5;
            height: 100vh;
            display: flex;
        }
        .sidebar {
            width: 320px;
            background: #2c3e50;
            color: white;
            display: flex;
            flex-direction: column;
        }
        .sidebar-header {
            padding: 20px;
            background: #1a252f;
        }
        .sidebar-header h2 { font-size: 18px; display: flex; align-items: center; justify-content: space-between; }
        .refresh-btn {
            background: #3498db;
            border: none;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 11px;
        }
        .tabs {
            display: flex;
            border-bottom: 1px solid #34495e;
        }
        .tab {
            flex: 1;
            padding: 12px;
            text-align: center;
            cursor: pointer;
            background: #34495e;
            border: none;
            color: #bdc3c7;
            font-size: 14px;
        }
        .tab.active {
            background: #2c3e50;
            color: white;
            border-bottom: 2px solid #3498db;
        }
        .contact-list {
            flex: 1;
            overflow-y: auto;
        }
        .contact-item {
            padding: 12px 20px;
            cursor: pointer;
            border-bottom: 1px solid #34495e;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .contact-item:hover { background: #3d566e; }
        .contact-item.active { background: #3498db; }
        .contact-info { flex: 1; overflow: hidden; }
        .contact-name { font-weight: 500; }
        .contact-id { font-size: 10px; opacity: 0.6; margin-top: 2px; }
        .contact-preview {
            font-size: 10px;
            opacity: 0.5;
            margin-top: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .unread-badge {
            background: #e74c3c;
            color: white;
            border-radius: 12px;
            padding: 2px 8px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 8px;
        }
        .chat-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #f8f9fa;
        }
        .chat-header {
            padding: 15px 20px;
            background: white;
            border-bottom: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .chat-header h3 { font-size: 18px; }
        .load-history-btn {
            background: #6c757d;
            border: none;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            cursor: pointer;
            font-size: 12px;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .message {
            margin-bottom: 12px;
            display: flex;
        }
        .message.sent { justify-content: flex-end; }
        .message.received { justify-content: flex-start; }
        .bubble {
            max-width: 70%;
            padding: 10px 14px;
            border-radius: 18px;
        }
        .sent .bubble {
            background: #3498db;
            color: white;
        }
        .received .bubble {
            background: white;
            color: #333;
            border: 1px solid #ddd;
        }
        .time {
            font-size: 10px;
            color: #999;
            margin-top: 4px;
        }
        .input-area {
            padding: 15px 20px;
            background: white;
            border-top: 1px solid #ddd;
            display: flex;
            gap: 10px;
        }
        .input-area input {
            flex: 1;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 24px;
            outline: none;
            font-size: 14px;
        }
        .input-area button {
            background: #3498db;
            color: white;
            border: none;
            padding: 0 24px;
            border-radius: 24px;
            cursor: pointer;
            font-weight: 500;
        }
        .loading { text-align: center; padding: 40px; color: #999; }
        .load-more {
            text-align: center;
            padding: 10px;
            color: #3498db;
            cursor: pointer;
            font-size: 12px;
        }
        .load-more:hover { text-decoration: underline; }
    </style>
</head>
<body>
<div class="sidebar">
    <div class="sidebar-header">
        <h2>📱 QQ 控制台
            <button class="refresh-btn" onclick="location.reload()">🔄 刷新</button>
        </h2>
    </div>
    <div class="tabs">
        <button class="tab active" id="tab-friend" onclick="switchTab('friend')">👤 好友</button>
        <button class="tab" id="tab-group" onclick="switchTab('group')">👥 群聊</button>
    </div>
    <div class="contact-list" id="contact-list"><div class="loading">加载中...</div></div>
</div>
<div class="chat-area">
    <div class="chat-header" id="chat-header">
        <div><h3>请选择聊天对象</h3></div>
    </div>
    <div class="messages" id="messages"><div class="loading">暂无消息</div></div>
    <div class="input-area">
        <input type="text" id="msg-input" placeholder="输入消息... (Enter 发送)" autocomplete="off">
        <button onclick="sendMsg()">发送</button>
    </div>
</div>

<script>
    let currentType = 'friend';
    let currentId = null;
    let currentName = null;
    let friends = [];
    let groups = [];
    let allMessages = {};
    let unreadCounts = {};
    let sending = false;
    let currentPage = 0;
    let hasMore = true;
    
    function switchTab(type) {
        currentType = type;
        document.getElementById('tab-friend').classList.toggle('active', type === 'friend');
        document.getElementById('tab-group').classList.toggle('active', type === 'group');
        currentId = null;
        currentPage = 0;
        document.getElementById('chat-header').innerHTML = '<div><h3>请选择聊天对象</h3></div>';
        document.getElementById('messages').innerHTML = '<div class="loading">暂无消息</div>';
        renderContacts();
    }
    
    async function loadContacts() {
        try {
            let res = await fetch('/api/contacts');
            let data = await res.json();
            friends = data.friends || [];
            groups = data.groups || [];
            renderContacts();
        } catch(e) { console.error(e); }
    }
    
    function renderContacts() {
        let list = currentType === 'friend' ? friends : groups;
        let container = document.getElementById('contact-list');
        if (list.length === 0) {
            container.innerHTML = '<div class="loading">暂无联系人</div>';
            return;
        }
        container.innerHTML = list.map(item => {
            let id = currentType === 'friend' ? item.user_id : item.group_id;
            let name = item.name || id;
            let unread = unreadCounts[id] || 0;
            let lastMsg = getLastMessage(id);
            return `
                <div class="contact-item ${currentId == id ? 'active' : ''}" onclick="selectContact('${currentType}', '${id}', '${escapeHtml(name)}')">
                    <div class="contact-info">
                        <div class="contact-name">${escapeHtml(name)}</div>
                        <div class="contact-id">${id}</div>
                        <div class="contact-preview">${escapeHtml(lastMsg)}</div>
                    </div>
                    ${unread > 0 ? `<div class="unread-badge">${unread}</div>` : ''}
                </div>
            `;
        }).join('');
    }
    
    function getLastMessage(targetId) {
        let msgs = allMessages[targetId] || [];
        if (msgs.length === 0) return '暂无消息';
        let last = msgs[msgs.length-1];
        let content = last.content || '';
        if (content.length > 25) content = content.substring(0, 25) + '...';
        return content;
    }
    
    async function selectContact(type, id, name) {
        if (unreadCounts[id]) {
            unreadCounts[id] = 0;
            renderContacts();
        }
        currentType = type;
        currentId = id;
        currentName = name;
        currentPage = 0;
        hasMore = true;
        document.getElementById('chat-header').innerHTML = `
            <div><h3>💬 ${escapeHtml(name)} (${type === 'friend' ? '好友' : '群聊'})</h3></div>
            <button class="load-history-btn" onclick="loadHistory()">📜 加载更早消息</button>
        `;
        renderContacts();
        await loadMessages(true);
    }
    
    async function loadMessages(reset = true) {
        if (!currentId) return;
        try {
            let url = `/api/messages?target=${currentId}&page=${currentPage}`;
            let res = await fetch(url);
            let data = await res.json();
            if (reset) {
                allMessages[currentId] = data.messages || [];
            } else {
                let olderMsgs = data.messages || [];
                allMessages[currentId] = [...olderMsgs, ...(allMessages[currentId] || [])];
            }
            hasMore = data.has_more !== false;
            renderMessages();
        } catch(e) { console.error(e); }
    }
    
    async function loadHistory() {
        if (!hasMore) {
            alert('没有更早的消息了');
            return;
        }
        currentPage++;
        await loadMessages(false);
    }
    
    function renderMessages() {
        let msgs = allMessages[currentId] || [];
        let container = document.getElementById('messages');
        if (msgs.length === 0) {
            container.innerHTML = '<div class="loading">暂无消息</div>';
            return;
        }
        let html = '';
        if (hasMore && msgs.length >= 30) {
            html += '<div class="load-more" onclick="loadHistory()">📜 点击加载更早消息</div>';
        }
        html += msgs.map(msg => `
            <div class="message ${msg.role === 'sent' ? 'sent' : 'received'}">
                <div class="bubble">
                    ${escapeHtml(msg.content)}
                    <div class="time">${msg.time} ${msg.role === 'received' ? msg.nickname : ''}</div>
                </div>
            </div>
        `).join('');
        container.innerHTML = html;
        container.scrollTop = container.scrollHeight;
    }
    
    async function sendMsg() {
        if (!currentId) { alert('请先选择聊天对象'); return; }
        if (sending) return;
        
        let input = document.getElementById('msg-input');
        let content = input.value.trim();
        if (!content) return;
        
        input.value = '';
        sending = true;
        
        let tempMsg = {
            role: 'sent',
            content: content,
            time: new Date().toLocaleTimeString().slice(0,5),
            nickname: '我'
        };
        if (!allMessages[currentId]) allMessages[currentId] = [];
        allMessages[currentId].push(tempMsg);
        renderMessages();
        renderContacts();
        
        try {
            let res = await fetch('/api/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: currentType, target: currentId, message: content })
            });
            let data = await res.json();
            if (!data.success) {
                alert('发送失败');
                allMessages[currentId].pop();
                renderMessages();
            }
        } catch(e) {
            alert('发送失败');
            allMessages[currentId].pop();
            renderMessages();
        } finally {
            sending = false;
        }
    }
    
    // 轮询新消息
    setInterval(async () => {
        if (currentId) {
            try {
                let res = await fetch(`/api/messages?target=${currentId}&page=0`);
                let data = await res.json();
                let newMsgs = data.messages || [];
                let oldCount = (allMessages[currentId] || []).length;
                let newCount = newMsgs.length;
                if (newCount !== oldCount) {
                    allMessages[currentId] = newMsgs;
                    renderMessages();
                }
            } catch(e) {}
        }
        
        for (let f of friends) {
            let id = f.user_id;
            try {
                let res = await fetch(`/api/messages?target=${id}&page=0`);
                let data = await res.json();
                let newMsgs = data.messages || [];
                let oldCount = (allMessages[id] || []).length;
                let newCount = newMsgs.length;
                if (newCount > oldCount) {
                    allMessages[id] = newMsgs;
                    if (id !== currentId) {
                        unreadCounts[id] = (unreadCounts[id] || 0) + (newCount - oldCount);
                        renderContacts();
                    }
                }
            } catch(e) {}
        }
        for (let g of groups) {
            let id = g.group_id;
            try {
                let res = await fetch(`/api/messages?target=${id}&page=0`);
                let data = await res.json();
                let newMsgs = data.messages || [];
                let oldCount = (allMessages[id] || []).length;
                let newCount = newMsgs.length;
                if (newCount > oldCount) {
                    allMessages[id] = newMsgs;
                    if (id !== currentId) {
                        unreadCounts[id] = (unreadCounts[id] || 0) + (newCount - oldCount);
                        renderContacts();
                    }
                }
            } catch(e) {}
        }
    }, 5000);
    
    document.getElementById('msg-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMsg();
        }
    });
    
    function escapeHtml(text) {
        if (!text) return '';
        return text.replace(/[&<>]/g, function(m) {
            if (m === '&') return '&amp;';
            if (m === '<') return '&lt;';
            if (m === '>') return '&gt;';
            return m;
        });
    }
    
    loadContacts();
</script>
</body>
</html>
'''

# ==================== 后端函数 ====================

def clean_message(content):
    if isinstance(content, list):
        texts = []
        for seg in content:
            if seg.get("type") == "text":
                texts.append(seg.get("data", {}).get("text", ""))
            elif seg.get("type") == "image":
                texts.append("[图片]")
        return "".join(texts)
    if isinstance(content, str):
        return re.sub(r'\[CQ:[^\]]+\]', '', content).strip()
    return str(content) if content else ""

def add_msg(target, role, content, nickname=""):
    if target not in msg_cache:
        msg_cache[target] = []
    msg_cache[target].append({
        "role": role,
        "content": clean_message(content) or "[图片]",
        "time": datetime.now().strftime("%H:%M"),
        "nickname": nickname
    })
    if len(msg_cache[target]) > MAX_MSG_PER_TARGET:
        msg_cache[target] = msg_cache[target][-MAX_MSG_PER_TARGET:]
    save_cache(msg_cache)

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/contacts")
def contacts():
    friends = []
    groups = []
    try:
        r = requests.get(f"{LLBOT_API}/get_friend_list", timeout=10)
        data = r.json()
        if "data" in data:
            friends = [{"user_id": str(f.get("user_id")), "name": f.get("remark") or f.get("nickname", str(f.get("user_id")))} 
                       for f in data.get("data", [])]
    except Exception as e:
        print(f"获取好友失败: {e}")
    
    try:
        r = requests.get(f"{LLBOT_API}/get_group_list", timeout=10)
        data = r.json()
        if "data" in data:
            groups = [{"group_id": str(g.get("group_id")), "name": g.get("group_name", str(g.get("group_id")))} 
                      for g in data.get("data", [])]
    except Exception as e:
        print(f"获取群聊失败: {e}")
    
    return jsonify({"friends": friends, "groups": groups})

@app.route("/api/messages")
def messages():
    target = request.args.get("target")
    page = int(request.args.get("page", 0))
    if not target:
        return jsonify({"messages": [], "has_more": False})
    
    msgs = msg_cache.get(target, [])
    page_size = 30
    start = page * page_size
    end = start + page_size
    
    if start >= len(msgs):
        paginated = []
        has_more = False
    else:
        paginated = msgs[max(0, len(msgs) - end):len(msgs) - start] if start > 0 else msgs[-end:]
        has_more = len(msgs) > end
    
    return jsonify({
        "messages": paginated,
        "has_more": has_more
    })

@app.route("/api/send", methods=["POST"])
def send():
    data = request.json
    msg_type = data.get("type")
    target = data.get("target")
    msg = data.get("message")
    try:
        if msg_type == "group":
            requests.post(f"{LLBOT_API}/send_group_msg", json={"group_id": int(target), "message": msg}, timeout=5)
        else:
            requests.post(f"{LLBOT_API}/send_private_msg", json={"user_id": int(target), "message": msg}, timeout=5)
        add_msg(target, "sent", msg, "我")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/receive", methods=["POST"])
def receive():
    """接收 LLOneBot 上报的消息 - WebHook"""
    try:
        data = request.json
        print(f"[WebHook] 收到消息: {data}")  # 调试日志
        
        if data.get("post_type") == "message":
            msg_type = data.get("message_type")
            content = data.get("message", "")
            sender = data.get("sender", {})
            
            if msg_type == "group":
                target = str(data.get("group_id"))
                nickname = sender.get("card") or sender.get("nickname", "未知")
            else:
                target = str(data.get("user_id"))
                nickname = sender.get("nickname", "未知")
            
            # 提取纯文本内容
            clean_content = clean_message(content)
            if clean_content:
                add_msg(target, "received", clean_content, nickname)
                print(f"[WebHook] 收到消息: {nickname} -> {clean_content[:50]}")
        
        return "OK"
    except Exception as e:
        print(f"[WebHook] 错误: {e}")
        return "OK"

if __name__ == "__main__":
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    print("=" * 50)
    print("QQ 控制台已启动")
    print("访问地址: http://127.0.0.1:5000")
    print("=" * 50)
    print("\n⚠️ LLOneBot WebHook 配置:")
    print("   http://127.0.0.1:5000/api/receive")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

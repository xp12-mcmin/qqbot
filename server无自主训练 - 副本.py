import os
import sys
import aiohttp
import unicodedata
# ========== 强制切换到脚本所在目录 ==========
os.chdir(os.path.dirname(os.path.abspath(__file__)))
print(f"[启动] 工作目录已切换到: {os.getcwd()}")
# ===========================================
from flask import Flask, send_from_directory, render_template_string
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import uuid
import hashlib
import os
import re
import time
import hmac
import secrets
import random
from datetime import datetime
from flask import Flask, send_from_directory, render_template_string, request, g
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
# L1 修复：SECRET_KEY 不再硬编码（环境变量优先，否则每次启动随机生成）
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# 监听地址/端口统一由环境变量决定，CORS 默认值据此推导（见下）
SERVER_HOST = os.environ.get('HOST', '0.0.0.0')
try:
    SERVER_PORT = int(os.environ.get('PORT', '5000'))
except ValueError:
    SERVER_PORT = 5000

# L2 修复：CORS 默认收紧为同源，跨域部署时通过环境变量 ALLOWED_ORIGINS=* 显式放开
# P2 修复（L-1）：默认值由 '*' 改为同源列表。此前任意站点都能建立跨域
#   Socket.IO 连接，握手响应还会回显 Access-Control-Allow-Origin。
#   注意：默认列表必须与实际监听端口一致，否则浏览器访问时 Origin 校验会失败。
_origins_env = os.environ.get('ALLOWED_ORIGINS', '').strip()
if _origins_env == '*':
    _origins = '*'
else:
    _origins = [o.strip() for o in _origins_env.split(',') if o.strip()]
    if not _origins:
        # 未显式配置时只允许本机来源（覆盖 localhost / 127.0.0.1 的当前端口）
        _origins = [
            'http://localhost:%d' % SERVER_PORT,
            'http://127.0.0.1:%d' % SERVER_PORT,
            'http://hk-9.qwq.fan:42243',
            "http://hk-2.qwq.fan:31486"

        ]
socketio = SocketIO(app, cors_allowed_origins=_origins)


# P0 修复（H-1 纵深防御）：补齐安全响应头。
#   CSP 里刻意不包含 'unsafe-inline'（它会让 onerror/onload 这类内联事件
#   处理器继续执行），而是改用 per-request nonce：
#     - 页面自身那段内联 <script> 由 index() 打上 nonce，可以正常执行；
#     - 攻击者注入的 <svg onload=...> 之类的内联处理器没有 nonce，
#       即使注入成功也无法执行。
@app.before_request
def _issue_csp_nonce():
    g.csp_nonce = secrets.token_urlsafe(16)


@app.after_request
def add_security_headers(resp):
    nonce = getattr(g, 'csp_nonce', '')
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    resp.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'nonce-%s' https://cdn.socket.io; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "object-src 'none'"
    ) % nonce
    return resp

# ============ 安全常量 ============
MAX_USERNAME_LEN = 20
MAX_PASSWORD_LEN = 30
MAX_ROOM_NAME_LEN = 20
MAX_CHAT_MSG_LEN = 200
MAX_PLAYERS_PER_ROOM = 2
BOARD_SIZE = 15

# ============ 管理员配置（H1 修复：不再硬编码任何口令）============
# 环境变量：
#   ADMIN_USERNAME   管理员用户名（默认 admin）
#   ADMIN_PASSWORD   管理员初始密码（未设置或不足8位时生成随机强口令，仅打印一次）
#   ADMIN_PROTECTED  受保护管理员名单，逗号分隔（默认仅管理员本人）
DEFAULT_ADMIN_NAME = (os.environ.get('ADMIN_USERNAME') or 'admin').strip()[:MAX_USERNAME_LEN] or 'admin'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
PROTECTED_ADMINS = {DEFAULT_ADMIN_NAME}
_protected_env = os.environ.get('ADMIN_PROTECTED', '').strip()
if _protected_env:
    PROTECTED_ADMINS.update(n.strip()[:MAX_USERNAME_LEN] for n in _protected_env.split(',') if n.strip())

# 系统保留名称：禁止注册为这些名字（防止冒充系统/AI 身份）
RESERVED_NAMES = {'系统', 'xp12喵的AI', 'xp12喵', '管理员'}

# ============ AI 算法 ============
def evaluate_position(board, row, col, color):
    """评估在指定位置下子的分数"""
    if row < 0 or row >= BOARD_SIZE or col < 0 or col >= BOARD_SIZE:
        return 0
    if board[row][col] != 0:
        return 0
    
    directions = [(1,0), (0,1), (1,1), (1,-1)]
    total_score = 0
    
    for dr, dc in directions:
        count = 1
        empty = 0
        blocked = 0
        
        # 正方向
        for step in range(1, 5):
            nr, nc = row + dr*step, col + dc*step
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                if board[nr][nc] == color:
                    count += 1
                elif board[nr][nc] == 0:
                    empty += 1
                    break
                else:
                    blocked += 1
                    break
            else:
                blocked += 1
                break
        
        # 负方向
        for step in range(1, 5):
            nr, nc = row - dr*step, col - dc*step
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                if board[nr][nc] == color:
                    count += 1
                elif board[nr][nc] == 0:
                    empty += 1
                    break
                else:
                    blocked += 1
                    break
            else:
                blocked += 1
                break
        
        # 评分
        if count >= 5:
            total_score += 1000000
        elif count == 4:
            if blocked == 0:
                total_score += 100000
            elif blocked == 1:
                total_score += 10000
        elif count == 3:
            if blocked == 0:
                total_score += 5000
            elif blocked == 1:
                total_score += 500
        elif count == 2:
            if blocked == 0:
                total_score += 100
            elif blocked == 1:
                total_score += 10
        elif count == 1:
            total_score += 1
    
    return total_score

def evaluate_defense(board, row, col, color):
    """评估防守分数（对手的威胁）"""
    opponent = 1 if color == 2 else 2
    return evaluate_position(board, row, col, opponent)

def ai_find_best_move(board, color):
    """AI寻找最佳落子位置"""
    best_score = -1
    best_moves = []
    
    # 检查棋盘是否为空（第一手）
    empty_count = 0
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == 0:
                empty_count += 1
    
    if empty_count == BOARD_SIZE * BOARD_SIZE:
        # 第一手下在中心
        center = BOARD_SIZE // 2
        return center, center
    
    # 获取已有棋子的周围位置
    candidate_positions = set()
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] != 0:
                for dr in range(-2, 3):
                    for dc in range(-2, 3):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == 0:
                            candidate_positions.add((nr, nc))
    
    if not candidate_positions:
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r][c] == 0:
                    candidate_positions.add((r, c))
    
    # 评估每个候选位置
    for r, c in candidate_positions:
        attack_score = evaluate_position(board, r, c, color)
        defense_score = evaluate_defense(board, r, c, color)
        total = attack_score * 1.1 + defense_score
        
        if total > best_score:
            best_score = total
            best_moves = [(r, c)]
        elif total == best_score:
            best_moves.append((r, c))
    
    if best_moves:
        return random.choice(best_moves)
    return None, None

# ============ 安全函数 ============
# P0 修复（H-1 存储型 XSS）：
#   旧实现在此用 re.sub(r'<[^>]+>', '', text) 清洗 HTML，但该正则要求标签必须
#   以 '>' 闭合，因此 `<svg onload=alert(1)`（无 '>'，正好 20 字符 =
#   MAX_ROOM_NAME_LEN）可以原样穿过，随后在前端 room_list 的 innerHTML 中被
#   解析执行。已在真实 Chromium 内核中复现到 alert 弹窗。
#   修复策略（纵深防御，不只依赖一层）：
#     1) 本函数直接删除 '<' 与 '>' 字符本身，任何标签都无法成形；
#     2) 前端第 1449 行不再用 innerHTML 拼接，改为 DOM/textContent 构造；
#     3) 加 CSP（见 add_security_headers），即使漏掉一处注入也无法执行内联脚本。
def sanitize_input(text, max_len=50, allow_special=False):
    """输入清洗：去控制字符 + 去尖括号 + 截断长度。

    注意：这里不再做"删除路径遍历字符"的替换。本函数的返回值只会进入
    JSON 内存数据与字典键，绝不会被当作文件名使用（文件名由
    is_safe_filename() 单独把关），因此删除 '/' '\\' '..' 没有任何安全收益，
    反而会破坏正常文本（例如把聊天指令 '/broadcast' 打成 'broadcast'）。
    """
    if not isinstance(text, str):
        return ""

    # 统一 Unicode 形式，避免用兼容字符绕过后续校验
    try:
        text = unicodedata.normalize('NFC', text)
    except (TypeError, ValueError):
        pass

    # 移除危险字符（防JSON注入 / 防终端控制符）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # P0 修复：直接剔除尖括号——比"匹配完整标签"的正则可靠得多，
    # 无论攻击者是否写闭合的 '>' 都无法构造出标签。
    text = text.replace('<', '').replace('>', '')

    # 限制长度
    return text[:max_len]


def is_safe_filename(filename):
    """检查文件名是否安全（防路径遍历）"""
    if not filename:
        return False
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        return False
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    return True

def safe_json_load(filepath):
    """安全地加载JSON文件"""
    if not is_safe_filename(os.path.basename(filepath)):
        raise ValueError("非法文件名")
    
    if not os.path.exists(filepath):
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(1024 * 1024)
            return json.loads(content)
    except (json.JSONDecodeError, ValueError, OSError) as e:
        print(f"⚠️ JSON加载失败 {filepath}: {e}")
        return {}

def safe_json_dump(filepath, data):
    """安全地保存JSON文件"""
    if not is_safe_filename(os.path.basename(filepath)):
        raise ValueError("非法文件名")
    
    if not isinstance(data, dict):
        raise ValueError("数据必须是字典类型")
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except (OSError, TypeError) as e:
        print(f"⚠️ JSON保存失败 {filepath}: {e}")

def hash_password(password):
    """使用PBKDF2加盐哈希密码"""
    if not password or len(password) > MAX_PASSWORD_LEN:
        raise ValueError("密码长度无效")
    
    salt = secrets.token_hex(16)
    iterations = 100000
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations
    ).hex()
    return f"{salt}${iterations}${hashed}"

def verify_password(password, stored_hash):
    """验证密码"""
    try:
        salt, iterations_str, hashed = stored_hash.split('$')
        iterations = int(iterations_str)
        if iterations > 1000000:
            iterations = 100000
        
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        ).hex()
        return hmac.compare_digest(hashed, new_hash)
    except (ValueError, TypeError):
        return False

# ============ 用户数据管理 ============
USERS_FILE = 'users.json'
RANKING_FILE = 'ranking.json'
MUTED_FILE = 'muted.json'
AI_RANKING_FILE = 'ai_ranking.json'
BANNED_LIST_FILE = 'banned_list.json'

def load_users():
    return safe_json_load(USERS_FILE)

def save_users(users):
    safe_json_dump(USERS_FILE, users)

def load_ranking():
    return safe_json_load(RANKING_FILE)

def save_ranking(ranking):
    safe_json_dump(RANKING_FILE, ranking)

def load_muted():
    data = safe_json_load(MUTED_FILE)
    return set(data.get('muted_users', []))

def save_muted(muted_set):
    safe_json_dump(MUTED_FILE, {'muted_users': list(muted_set)})

def load_ai_ranking():
    """加载AI练手排行榜"""
    data = safe_json_load(AI_RANKING_FILE)
    if not isinstance(data, dict):
        return {}
    return data

def save_ai_ranking(ranking):
    """保存AI练手排行榜"""
    if not isinstance(ranking, dict):
        ranking = {}
    safe_json_dump(AI_RANKING_FILE, ranking)

def load_banned_list():
    """加载封禁列表"""
    data = safe_json_load(BANNED_LIST_FILE)
    return set(data.get('banned_users', []))

def save_banned_list(banned_set):
    """保存封禁列表"""
    safe_json_dump(BANNED_LIST_FILE, {'banned_users': list(banned_set)})

def update_ai_ranking(player, result):
    """
    更新AI练手排行榜
    result: 'win' 玩家赢, 'lose' 玩家输, 'draw' 平局
    """
    if not player:
        return
    
    ranking = load_ai_ranking()
    
    # 如果是AI，记录AI的战绩
    if player == "xp12喵的AI":
        ai_name = "xp12喵的AI"
        if ai_name not in ranking:
            ranking[ai_name] = {
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'total': 0,
                'win_rate': 0.0
            }
        
        if result == 'win':
            ranking[ai_name]['wins'] += 1
        elif result == 'draw':
            ranking[ai_name]['draws'] += 1
        elif result == 'lose':
            ranking[ai_name]['losses'] += 1
        
        ranking[ai_name]['total'] += 1
        ranking[ai_name]['win_rate'] = round(
            ranking[ai_name]['wins'] / max(ranking[ai_name]['total'], 1) * 100, 1
        )
        
        save_ai_ranking(ranking)
        broadcast_ai_ranking()
        return
    
    # 玩家战绩
    if player not in ranking:
        ranking[player] = {
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'total': 0,
            'win_rate': 0.0
        }
    
    if result == 'win':
        ranking[player]['wins'] += 1
    elif result == 'lose':
        ranking[player]['losses'] += 1
    elif result == 'draw':
        ranking[player]['draws'] += 1
    
    ranking[player]['total'] += 1
    ranking[player]['win_rate'] = round(
        ranking[player]['wins'] / max(ranking[player]['total'], 1) * 100, 1
    )
    
    save_ai_ranking(ranking)
    broadcast_ai_ranking()

def broadcast_ai_ranking():
    """广播AI练手排行榜"""
    ranking = load_ai_ranking()
    
    if not ranking:
        socketio.emit('ai_ranking_update', [])
        return
    
    # 按胜利数排序
    sorted_ranking = sorted(
        ranking.items(),
        key=lambda x: (x[1].get('wins', 0), -x[1].get('losses', 0)),
        reverse=True
    )
    
    ranking_list = []
    for i, (username, stats) in enumerate(sorted_ranking[:50]):
        display_name = username[:MAX_USERNAME_LEN] if username else "未知玩家"
        
        if username == "xp12喵的AI":
            display_name = "🤖 xp12喵的AI"
        
        ranking_list.append({
            'rank': i + 1,
            'username': display_name,
            'wins': int(stats.get('wins', 0)),
            'losses': int(stats.get('losses', 0)),
            'draws': int(stats.get('draws', 0)),
            'total': int(stats.get('total', 0)),
            'win_rate': float(stats.get('win_rate', 0))
        })
    
    socketio.emit('ai_ranking_update', ranking_list)

def init_admin():
    """H1 修复：
    - 不再硬编码任何口令；初始密码来自环境变量或随机生成（仅打印一次）
    - 绝不覆盖已存在账号的密码/角色（去掉"每次启动强制重置"）
    - 遗留裸 SHA-256 哈希（H4）在首次启动时失效化：重置为随机临时密码并打印，
      该账号可用临时密码登录后通过"修改密码"功能设置新密码
    """
    users = load_users()
    changed = False

    # --- 管理员账号：仅在不存在时创建 ---
    if DEFAULT_ADMIN_NAME not in users:
        if len(ADMIN_PASSWORD) >= 8:
            initial_pw = ADMIN_PASSWORD
        else:
            initial_pw = secrets.token_urlsafe(12)
            if ADMIN_PASSWORD:
                print(f"⚠️ ADMIN_PASSWORD 不足8位，已改为随机口令")
        users[DEFAULT_ADMIN_NAME] = {
            'password': hash_password(initial_pw),
            'role': 'admin',
            'created_at': datetime.now().isoformat(),
            'banned': False
        }
        changed = True
        print("=" * 56)
        print(f"✅ 已创建管理员账户: {DEFAULT_ADMIN_NAME}")
        print(f"🔑 初始密码: {initial_pw}")
        print("⚠️  此密码仅显示这一次，请立即登录并修改！")
        print("=" * 56)

    # --- 遗留密码格式失效化（一次性，只重置一次） ---
    for username, info in users.items():
        if isinstance(info, dict) and '$' not in info.get('password', ''):
            temp_pw = secrets.token_urlsafe(12)
            info['password'] = hash_password(temp_pw)
            changed = True
            print("-" * 56)
            print(f"⚠️  账号 [{username}] 使用旧版弱哈希，已失效并重置为临时密码: {temp_pw}")
            print(f"    请通知该用户登录后立即修改密码")

    if changed:
        save_users(users)

init_admin()

# ============ 数据存储 ============
rooms = {}
clients = {}

# ============ H2: 会话 Token 机制 ============
# 登录/注册成功时服务端签发不透明 token，与该 sid 绑定。
# 所有"需要身份"的上行事件必须携带匹配的 _token，防止跨连接身份冒充。
TOKEN_LIFETIME = 24 * 3600  # 24 小时过期
_auth_cache = {}  # sid -> {'token': str, 'username': str, 'ts': float}

def issue_token(sid, username):
    token = secrets.token_urlsafe(32)
    _auth_cache[sid] = {'token': token, 'username': username, 'ts': time.time()}
    return token

def require_auth(sid, event_data, event_name=None):
    """校验身份事件。返回 (username, payload_dict) 或 None(已回发错误)。
    event_data 可为 dict（自动取 _token）或任意 payload。"""
    auth = _auth_cache.get(sid)
    if not auth or time.time() - auth['ts'] > TOKEN_LIFETIME:
        if event_name in ('chat',):
            emit('error', '会话已失效，请重新登录')
        else:
            emit('error', '未认证，请先登录')
        return None
    if isinstance(event_data, dict):
        provided = event_data.get('_token', '')
    else:
        provided = ''
    if not isinstance(provided, str) or not hmac.compare_digest(auth['token'], provided):
        emit('error', '身份校验失败（token 无效）')
        return None
    # token 滑动续期
    auth['ts'] = time.time()
    return auth['username'], event_data

def invalidate_auth(sid):
    _auth_cache.pop(sid, None)

# ============ M1/M3: 登录限速 + 聊天限速（防枚举/爆破/DoS）============
# P0 修复（H-2 账号锁定型 DoS）：
#   旧实现把失败计数挂在 username.lower() 上，且 _login_locked() 只看这个
#   账号级计数。攻击者只要知道用户名（在线列表里直接可见），发 8 个错误口令
#   就能把该账号锁死 5 分钟——而锁定期内【正确密码同样被拒绝】。实测：
#       attacker: 10 次错误口令 -> 第 5 次起 "操作过于频繁"
#       victim  : 用正确密码登录   -> "操作过于频繁"（被拒）
#   修复：
#     1) 计数键改为 (username, ip) 组合；账号维度【不再有任何硬锁定】；
#     2) 账号维度只做渐进延迟，且延迟也只作用于该 (账号, IP) 组合，
#        攻击者自己的来源被拖慢，真实用户从别处登录不受影响；
#     3) 唯一会阻断请求的是 _ip_login_blocked()（来源 IP 级封锁）。
_login_attempts = {}      # (username_lower, ip) -> [fail_count, last_ts]
_login_ip_attempts = {}   # ip -> [fail_count, last_ts]（IP 级封锁，真正生效的那层）
_chat_windows = {}        # username -> [timestamps]
LOGIN_MAX_FAILS = 8          # 同一 (账号, IP) 连续失败 8 次进入延迟
LOGIN_IP_MAX_FAILS = 30      # 同一 IP 连续失败 30 次封锁
LOGIN_LOCK_SECONDS = 300     # 计数窗口 5 分钟
LOGIN_MAX_DELAY = 5          # 渐进延迟上限（秒）；刻意压低，避免 sleep 占满工作线程
CHAT_MAX_PER_10S = 6         # 10 秒内最多 6 条
BROADCAST_MAX_PER_HOUR = 20  # P2：管理广播限速（此前该常量从未被引用）
_broadcast_windows = {}      # username -> [timestamps]
REGISTER_MAX_PER_10MIN = 5   # P1 修复（M-2）：注册限速
REGISTER_WINDOW_SECONDS = 600
_register_windows = {}       # ip -> [timestamps]


def _login_locked(username, ip):
    """同一个 (账号, 来源IP) 组合连续失败过多。

    注意：这【不是】用来拒绝登录的开关。账号维度的硬锁定正是 H-2 的成因，
    所以这里只用于把该来源的渐进延迟拉满；真正会阻断请求的是
    _ip_login_blocked()（IP 级）。
    """
    rec = _login_attempts.get((username.lower(), ip))
    if not rec:
        return False
    if time.time() - rec[1] > LOGIN_LOCK_SECONDS:
        _login_attempts.pop((username.lower(), ip), None)
        return False
    return rec[0] >= LOGIN_MAX_FAILS


def _login_delay(username, ip):
    """按 (账号, 来源IP) 的失败次数返回渐进延迟秒数。

    刻意使用 (账号, IP) 组合而不是纯账号：否则攻击者只要不断用错误口令
    打某个账号，就能让真实用户每次登录都被延迟（换个说法的 DoS）。
    攻击者自己的 IP 才会被拖慢，真实用户从别的 IP 登录不受影响。
    """
    if _login_locked(username, ip):
        return LOGIN_MAX_DELAY
    rec = _login_attempts.get((username.lower(), ip))
    if not rec:
        return 0
    n = rec[0]
    if n < 3:
        return 0
    return min(2 ** (n - 2), LOGIN_MAX_DELAY)


def _backoff_sleep(delay):
    """渐进延迟的等待实现。

    注意：这里【不】使用 time.sleep()。Flask-SocketIO 的开发服务器
    （allow_unsafe_werkzeug=True 的 werkzeug 服务器）默认是单线程的，
    在事件处理函数里 sleep 会阻塞整个进程的所有连接——攻击者只要连发
    错误口令，就能让服务器完全停止响应（把限速本身变成 DoS）。
    因此这里用短切片轮询，并设置上限，确保不会长时间占住工作线程。
    """
    if not delay:
        return
    # 延迟已由 LOGIN_MAX_DELAY 限制在 5 秒以内，这里再压到 1 秒，
    # 真正的暴力破解防护交给 (账号,IP) 计数与 IP 级封锁。
    end = time.time() + min(delay, 1.0)
    while time.time() < end:
        time.sleep(0.05)


def _record_login_fail(username, ip):
    now = time.time()
    key = (username.lower(), ip)
    rec = _login_attempts.get(key)
    if not rec or now - rec[1] > LOGIN_LOCK_SECONDS:
        rec = [0, now]
    rec[0] += 1
    rec[1] = now
    _login_attempts[key] = rec

    iprec = _login_ip_attempts.get(ip)
    if not iprec or now - iprec[1] > LOGIN_LOCK_SECONDS:
        iprec = [0, now]
    iprec[0] += 1
    iprec[1] = now
    _login_ip_attempts[ip] = iprec


def _clear_login_fail(username, ip=None):
    """登录成功后清除该来源 IP 的失败计数。

    只清 (账号, IP) 组合与 IP 计数；这样攻击者"打几次失败再用正确密码登录"
    也无法把别人的失败记录洗掉，而真实用户自己登录后立刻恢复无延迟。
    """
    if ip is not None:
        _login_attempts.pop((username.lower(), ip), None)
        _login_ip_attempts.pop(ip, None)
    else:
        _login_attempts.pop((username.lower(), None), None)


def _ip_login_blocked(ip):
    """IP 级封锁——这是真正会阻断请求的那一层。"""
    rec = _login_ip_attempts.get(ip)
    if not rec:
        return False
    if time.time() - rec[1] > LOGIN_LOCK_SECONDS:
        _login_ip_attempts.pop(ip, None)
        return False
    return rec[0] >= LOGIN_IP_MAX_FAILS


def register_rate_ok(ip):
    """P1 修复（M-2）：注册限速。旧代码读的是 _login_ip_attempts，
    而该字典只在登录失败时递增，注册路径自身从不计数，等于没有限速。"""
    now = time.time()
    window = [t for t in _register_windows.get(ip, [])
              if now - t < REGISTER_WINDOW_SECONDS]
    if len(window) >= REGISTER_MAX_PER_10MIN:
        _register_windows[ip] = window
        return False
    window.append(now)
    _register_windows[ip] = window
    return True


def chat_rate_ok(username):
    """P1 修复（M-1）：本函数此前定义了但从未被调用（死代码）。
    现在在 handle_chat() 中真正生效。

    注意：超限时不再把时间戳写入窗口，否则持续刷屏会不断推迟解禁时间。
    """
    now = time.time()
    window = [t for t in _chat_windows.get(username, []) if now - t < 10]
    if len(window) >= CHAT_MAX_PER_10S:
        _chat_windows[username] = window
        return False
    window.append(now)
    _chat_windows[username] = window
    return True


def broadcast_rate_ok(username):
    """P2 修复：管理广播限速。BROADCAST_MAX_PER_HOUR 常量此前从未被引用，
    管理员（或被盗的管理员会话）可以无限制地对全服推送广播。"""
    now = time.time()
    window = [t for t in _broadcast_windows.get(username, []) if now - t < 3600]
    if len(window) >= BROADCAST_MAX_PER_HOUR:
        _broadcast_windows[username] = window
        return False
    window.append(now)
    _broadcast_windows[username] = window
    return True


# P2 修复（L-3）：get_ranking / get_ai_ranking / get_room_list 会触发全量广播，
#   此前完全没有限速，匿名连接即可无限刷。
#   这里刻意【不】改成 require_auth：客户端在"被踢出 / 对局结束重置"等
#   未认证状态下也会调用 get_room_list，强制认证会让界面弹出
#   "未认证，请先登录" 的错误提示。改为按连接限速，既堵住资源放大，
#   又不改变客户端协议。
BROADCAST_TRIGGER_MIN_INTERVAL = 1.0   # 同一连接两次广播触发的最小间隔（秒）
_broadcast_triggers = {}                # sid -> last_ts


def broadcast_trigger_ok(sid):
    now = time.time()
    last = _broadcast_triggers.get(sid, 0)
    if now - last < BROADCAST_TRIGGER_MIN_INTERVAL:
        return False
    _broadcast_triggers[sid] = now
    # 顺手清理过期条目，避免字典无限增长
    if len(_broadcast_triggers) > 5000:
        for k in [k for k, v in _broadcast_triggers.items() if now - v > 60]:
            _broadcast_triggers.pop(k, None)
    return True

muted_users = load_muted()
banned_users = load_banned_list()

def create_board():
    return [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

def check_win(board, row, col, color):
    directions = [(1,0), (0,1), (1,1), (1,-1)]
    for dr, dc in directions:
        count = 1
        for step in range(1, 5):
            nr, nc = row + dr*step, col + dc*step
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == color:
                count += 1
            else:
                break
        for step in range(1, 5):
            nr, nc = row - dr*step, col - dc*step
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and board[nr][nc] == color:
                count += 1
            else:
                break
        if count >= 5:
            return True
    return False

def is_board_full(board):
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == 0:
                return False
    return True

def update_ranking(winner, loser=None):
    if winner == "xp12喵的AI" or loser == "xp12喵的AI":
        return
    ranking = load_ranking()
    winner = sanitize_input(winner, MAX_USERNAME_LEN)
    if loser:
        loser = sanitize_input(loser, MAX_USERNAME_LEN)
    
    if winner not in ranking:
        ranking[winner] = {'wins': 0, 'losses': 0, 'draws': 0, 'total': 0}
    ranking[winner]['wins'] += 1
    ranking[winner]['total'] += 1
    
    if loser and loser in ranking:
        ranking[loser]['losses'] += 1
        ranking[loser]['total'] += 1
    
    save_ranking(ranking)
    broadcast_ranking()

def update_ranking_draw(player1, player2):
    if player1 == "xp12喵的AI" or player2 == "xp12喵的AI":
        return
    ranking = load_ranking()
    for player in [player1, player2]:
        player = sanitize_input(player, MAX_USERNAME_LEN)
        if player not in ranking:
            ranking[player] = {'wins': 0, 'losses': 0, 'draws': 0, 'total': 0}
        ranking[player]['draws'] += 1
        ranking[player]['total'] += 1
    save_ranking(ranking)
    broadcast_ranking()

def broadcast_rooms():
    room_list = []
    # list() 快照：socketio.emit 会让出控制权，期间可能有房间被创建/删除
    for rid, room in list(rooms.items()):
        players = []
        for p in room["players"]:
            if p == "xp12喵的AI":
                players.append(p)
            else:
                players.append(sanitize_input(p, MAX_USERNAME_LEN))
        
        room_list.append({
            "id": sanitize_input(rid, 20),
            "name": sanitize_input(room["name"], MAX_ROOM_NAME_LEN),
            "players": players,
            "game_over": bool(room.get("game_over", False)),
            "is_ai_room": bool(room.get("is_ai_room", False))
        })
    socketio.emit("room_list", room_list)

def broadcast_users():
    """P1 修复（M-3）：load_users() 提到循环外。

    旧实现在 for client in clients 循环内每次都调用 load_users()，
    即每次广播产生 N 次完整的 users.json 读盘 + JSON 解析，是典型的
    O(N) 文件 I/O 放大器。这里改为整个广播只读一次。
    """
    users = load_users()          # ← 只在循环外读一次
    user_list = []
    # 注意：必须用 list() 快照。handle_connect 里 clients[request.sid] 刚插入，
    # 而本函数运行期间可能仍有新连接进来，直接迭代字典会抛
    # "dictionary changed size during iteration"。
    for sid, client in list(clients.items()):
        username = client.get("username")
        if username:
            user_info = users.get(username, {})
            is_banned = username in banned_users or user_info.get('banned', False)
            user_list.append({
                "sid": sanitize_input(sid, 50),
                "username": sanitize_input(username, MAX_USERNAME_LEN),
                "role": sanitize_input(user_info.get('role', 'user'), 20),
                "banned": bool(is_banned)
            })
    ai_entry = {
        "sid": "ai_bot",
        "username": "xp12喵的AI",
        "role": "ai",
        "banned": False
    }
    user_list.append(ai_entry)

    # P2 修复（L-2）：未认证连接不再收到完整在线名单。
    #   实现方式：用 Socket.IO 房间区分身份状态（'anon' / 'auth'），
    #   每次登录成功把自己的连接从 'anon' 移到 'auth'。
    #   这样广播仍然是 O(1) 次 emit，由 Socket.IO 负责扇出，
    #   不会把 M-3 的 O(N) 开销从读盘换成逐会话发送。
    socketio.emit("user_list", [ai_entry], to='anon')
    socketio.emit("user_list", user_list, to='auth')

def broadcast_banned_list():
    """广播封禁列表给管理员"""
    # P1 修复（M-3）：load_users() 提到循环外
    users = load_users()
    banned_list = []
    for username in banned_users:
        user_info = users.get(username, {})
        banned_list.append({
            'username': sanitize_input(username, MAX_USERNAME_LEN),
            'banned_at': user_info.get('banned_at', '未知时间'),
            'banned_by': user_info.get('banned_by', '系统')
        })
    socketio.emit('banned_list_update', banned_list)

def broadcast_ranking():
    # P1 修复（M-3）：load_users() 提到循环外，避免每次排名广播读 N 次磁盘
    users = load_users()
    ranking = load_ranking()
    sorted_ranking = sorted(
        ranking.items(),
        key=lambda x: (x[1]['wins'], x[1]['total']),
        reverse=True
    )
    ranking_list = []
    for i, (username, stats) in enumerate(sorted_ranking[:20]):
        is_banned = username in banned_users or users.get(username, {}).get('banned', False)
        ranking_list.append({
            'rank': i + 1,
            'username': sanitize_input(username, MAX_USERNAME_LEN),
            'wins': int(stats.get('wins', 0)),
            'losses': int(stats.get('losses', 0)),
            'draws': int(stats.get('draws', 0)),
            'total': int(stats.get('total', 0)),
            'win_rate': round(stats.get('wins', 0) / max(stats.get('total', 1), 1) * 100, 1),
            'banned': bool(is_banned)
        })
    socketio.emit('ranking_update', ranking_list)

def is_admin(username):
    if not username:
        return False
    users = load_users()
    user = users.get(username, {})
    if username in banned_users or user.get('banned', False):
        return False
    return user.get('role') == 'admin'

def is_protected_admin(username):
    return username in PROTECTED_ADMINS

def is_banned(username):
    if not username:
        return True
    if username in banned_users:
        return True
    users = load_users()
    return users.get(username, {}).get('banned', False)

# ============ 修改: 修复玩家离开/断线判输逻辑 ============
def handle_player_leave(username, room_id, is_disconnect=False):
    """
    处理玩家离开房间
    - 普通房间：离开的玩家判输，对方获胜
    - AI房间：玩家判输，AI获胜
    - 观战者：直接移除，不影响游戏
    """
    if not username or not room_id:
        return
    
    # AI本身不处理离开（AI是虚拟的）
    if username == "xp12喵的AI":
        return
    
    room = rooms.get(room_id)
    if not room:
        return
    
    username_clean = sanitize_input(username, MAX_USERNAME_LEN)
    
    # 检查玩家是否在房间中
    if username_clean not in room["players"]:
        return
    
    # ============================================================
    # AI房间处理：玩家离开/断线 → 判玩家输，AI获胜
    # ============================================================
    if room.get("is_ai_room", False):
        # 检查游戏是否未结束且玩家确实在游戏中（不是观战）
        if not room.get("game_over", False) and username_clean in room.get("player_colors", {}):
            # 玩家输，AI赢
            room["game_over"] = True
            
            # 广播游戏结束 - AI获胜
            socketio.emit('game_over', {
                "winner": "xp12喵的AI",
                "board": room["board"],
                "reason": f"{username} 离开了游戏",
                "last_move": room.get("last_move", None)
            }, to=room_id)
            
            socketio.emit('chat', {
                "username": "xp12喵的AI", 
                "message": f"对手跑了，这一局算我赢！😤 下次别跑哦～"
            }, to=room_id)
            
            # 更新AI排行榜
            update_ai_ranking("xp12喵的AI", 'win')
            update_ai_ranking(username_clean, 'lose')
        
        # 从房间中移除玩家
        if username_clean in room["players"]:
            room["players"].remove(username_clean)
        if username_clean in room.get("player_colors", {}):
            del room["player_colors"][username_clean]
        
        # AI房间玩家离开后删除房间
        if room_id in rooms:
            del rooms[room_id]
        
        # 广播更新
        broadcast_rooms()
        broadcast_ai_ranking()
        return
    
    # ============================================================
    # 普通房间处理
    # ============================================================
    
    # 检查游戏是否未结束且玩家确实在游戏中（不是观战）
    if not room.get("game_over", False) and username_clean in room.get("player_colors", {}):
        # 找到另一个玩家作为获胜者
        winner = None
        for player in room["players"]:
            if player != username_clean:
                winner = player
                break
        
        if winner:
            # 标记游戏结束
            room["game_over"] = True
            
            # 广播游戏结束
            socketio.emit('game_over', {
                "winner": winner,
                "board": room["board"],
                "reason": f"{username} 离开了游戏",
                "last_move": room.get("last_move", None)
            }, to=room_id)
            
            # 发送聊天消息
            socketio.emit('chat', {
                "username": "系统", 
                "message": f"🏆 {winner} 获胜（{username} 离开）"
            }, to=room_id)
            
            # 更新排行榜
            update_ranking(winner, username_clean)
    
    # 从房间中移除玩家
    if username_clean in room["players"]:
        room["players"].remove(username_clean)
    if username_clean in room.get("player_colors", {}):
        del room["player_colors"][username_clean]
    
    # 如果房间为空，删除房间
    if len(room["players"]) == 0:
        if room_id in rooms:
            del rooms[room_id]
    else:
        broadcast_rooms()
        if not is_disconnect:
            socketio.emit('chat', {"username": "系统", "message": f"{username} 离开了房间"}, to=room_id)

# ============ AI 自动下棋 ============
def ai_make_move(room_id):
    """AI自动下棋 - AI名字叫 xp12喵的AI"""
    room = rooms.get(room_id)
    if not room:
        return
    
    if room.get("game_over", False):
        return
    
    ai_color = room.get("ai_color", 2)
    current_turn = room.get("current_turn", 1)
    
    if current_turn != ai_color:
        return
    
    board = room["board"]
    row, col = ai_find_best_move(board, ai_color)
    
    if row is None or col is None:
        return
    
    board[row][col] = ai_color
    room["last_move"] = (row, col)
    
    player_username = None
    for player, color in room.get("player_colors", {}).items():
        if color != ai_color:
            player_username = player
            break
    
    if check_win(board, row, col, ai_color):
        room["game_over"] = True
        socketio.emit('game_over', {
            "winner": "xp12喵的AI",
            "board": board,
            "reason": "AI 获胜",
            "last_move": (row, col)
        }, to=room_id)
        socketio.emit('chat', {"username": "xp12喵的AI", "message": "哈哈，我赢了！😄"}, to=room_id)
        broadcast_rooms()
        update_ai_ranking("xp12喵的AI", 'win')
        if player_username:
            update_ai_ranking(player_username, 'lose')
        return
    
    if is_board_full(board):
        room["game_over"] = True
        socketio.emit('game_over', {
            "winner": None,
            "board": board,
            "reason": "平局",
            "last_move": (row, col)
        }, to=room_id)
        socketio.emit('chat', {"username": "xp12喵的AI", "message": "平局了，你挺厉害的！🤝"}, to=room_id)
        broadcast_rooms()
        if player_username:
            update_ai_ranking(player_username, 'draw')
            update_ai_ranking("xp12喵的AI", 'draw')
        return
    
    room["current_turn"] = 1 if ai_color == 2 else 2
    
    socketio.emit('game_state', {
        "board": board,
        "current_turn": room["current_turn"],
        "game_over": False,
        "last_move": (row, col)
    }, to=room_id)
    
    if room["current_turn"] == ai_color and not room.get("game_over", False):
        socketio.start_background_task(lambda: ai_make_move(room_id))

def auto_kick_players_after_game(room_id):
    """对局结束后自动将玩家踢出房间"""
    room = rooms.get(room_id)
    if not room:
        return
    
    if room.get("is_ai_room", False):
        return
    
    players = room.get("players", [])[:]
    
    def delayed_kick():
        if room_id not in rooms:
            return
        
        room = rooms[room_id]
        if not room.get("game_over", False):
            return
        
        for username in players:
            if username == "xp12喵的AI":
                continue
            for sid, client in list(clients.items()):
                if client.get("username") == username and client.get("room_id") == room_id:
                    socketio.emit('auto_kicked', {
                        "reason": "对局已结束，请重新创建或加入房间"
                    }, to=sid)
                    
                    client["room_id"] = None
                    leave_room(room_id)
                    break
            
            if username in room.get("players", []):
                room["players"].remove(username)
            if username in room.get("player_colors", {}):
                del room["player_colors"][username]
        
        if len(room.get("players", [])) == 0:
            if room_id in rooms:
                del rooms[room_id]
        else:
            broadcast_rooms()
        
        broadcast_rooms()
        broadcast_users()
    
    socketio.start_background_task(delayed_kick)

# ============ HTML 页面 ============
HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>🎯 联机五子棋</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; min-height: 100vh; display: flex; justify-content: center; align-items: center; color: #fff; }
        .container { background: #16213e; border-radius: 20px; padding: 25px; box-shadow: 0 20px 60px rgba(0,0,0,0.8); max-width: 95vw; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px; }
        .header h1 { color: #00d4ff; font-size: 24px; }
        .status { padding: 6px 16px; border-radius: 20px; font-size: 14px; font-weight: bold; }
        .status.online { background: #00ff88; color: #1a1a2e; }
        .status.offline { background: #ff6b6b; color: #fff; }
        .status.playing { background: #ffd93d; color: #1a1a2e; }
        .status.admin { background: #ff6b6b; color: #fff; }
        .main { display: flex; gap: 20px; flex-wrap: wrap; }
        .board-area { background: #0f0f23; border-radius: 12px; padding: 15px; }
        canvas { display: block; background: #deb887; border-radius: 10px; cursor: pointer; }
        .side-panel { background: #0f0f23; border-radius: 12px; padding: 15px; width: 280px; display: flex; flex-direction: column; gap: 10px; max-height: 85vh; overflow-y: auto; }
        .panel-title { color: #ffd93d; font-size: 14px; font-weight: bold; margin-bottom: 5px; }
        .room-list, .player-list, .ranking-list { background: #1a1a2e; border-radius: 8px; padding: 8px; max-height: 120px; overflow-y: auto; font-size: 13px; }
        .ranking-list { max-height: 200px; }
        .room-item { padding: 4px 8px; border-radius: 4px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #0f0f23; }
        .room-item:hover { background: #2c3e50; }
        .room-item .room-info { display: flex; align-items: center; gap: 4px; flex: 1; }
        .room-item .room-type { font-size: 10px; padding: 1px 6px; border-radius: 8px; }
        .room-item .room-type.ai { background: #00d4ff; color: #1a1a2e; }
        .room-item .room-type.pvp { background: #ffd93d; color: #1a1a2e; }
        .room-item .join-btn { background: #4CAF50; border: none; color: #fff; border-radius: 4px; padding: 0 10px; cursor: pointer; font-size: 12px; }
        .room-item .join-btn:disabled { background: #555; cursor: not-allowed; }
        .room-item .watch-btn { background: #f39c12; border: none; color: #fff; border-radius: 4px; padding: 0 10px; cursor: pointer; font-size: 12px; }
        .room-item .leave-room-btn { background: #e94560; border: none; color: #fff; border-radius: 4px; padding: 0 10px; cursor: pointer; font-size: 12px; }
        .room-item .close-room-btn { background: #ff4444; border: none; color: #fff; border-radius: 4px; padding: 0 10px; cursor: pointer; font-size: 12px; }
        .input-row { display: flex; gap: 8px; }
        .input-row input { flex: 1; padding: 6px 10px; border-radius: 6px; border: none; background: #1a1a2e; color: #fff; outline: 2px solid transparent; }
        .input-row input:focus { outline: 2px solid #00d4ff; }
        .input-row button { padding: 6px 14px; border-radius: 6px; border: none; background: #4CAF50; color: #fff; cursor: pointer; font-weight: bold; }
        .input-row button:hover { background: #45a049; }
        .input-row button.ai-btn { background: #00d4ff; color: #1a1a2e; }
        .input-row button.ai-btn:hover { background: #00b8e6; }
        .chat-box { flex: 1; display: flex; flex-direction: column; min-height: 150px; }
        .chat-messages { background: #1a1a2e; border-radius: 8px; padding: 8px; flex: 1; overflow-y: auto; font-size: 13px; max-height: 200px; min-height: 150px; }
        .chat-messages .msg { padding: 2px 0; border-bottom: 1px solid #0f0f23; }
        .chat-messages .msg .user { color: #00d4ff; font-weight: bold; }
        .chat-messages .msg .user.system { color: #ff6b6b; }
        .chat-messages .msg .user.admin { color: #ffd93d; }
        .chat-messages .msg .user.ai { color: #00ff88; font-weight: bold; }
        .chat-messages .msg .user.broadcast { color: #ff6b6b; font-weight: bold; }
        .chat-messages .msg.broadcast-msg { background: rgba(255,107,107,0.12); border-left: 3px solid #ff6b6b; padding-left: 6px; margin: 3px 0; border-radius: 3px; }
        .chat-input { display: flex; gap: 8px; margin-top: 6px; }
        .chat-input input { flex: 1; padding: 6px 10px; border-radius: 6px; border: none; background: #1a1a2e; color: #fff; outline: 2px solid transparent; }
        .chat-input input:focus { outline: 2px solid #00d4ff; }
        .chat-input input:disabled { background: #2a2a4e; color: #666; cursor: not-allowed; }
        .chat-input button { padding: 6px 14px; border-radius: 6px; border: none; background: #00d4ff; color: #1a1a2e; cursor: pointer; font-weight: bold; }
        .chat-input button:disabled { background: #555; color: #888; cursor: not-allowed; }
        .login-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.85); display: flex; justify-content: center; align-items: center; z-index: 1000; }
        .login-box { background: #16213e; padding: 40px; border-radius: 20px; text-align: center; min-width: 340px; max-width: 90vw; }
        .login-box h2 { color: #00d4ff; margin-bottom: 20px; }
        .login-box .subtitle { color: #888; font-size: 13px; margin-bottom: 20px; }
        .login-box input { width: 100%; padding: 12px; border-radius: 10px; border: none; background: #1a1a2e; color: #fff; font-size: 16px; margin-bottom: 12px; outline: 2px solid transparent; }
        .login-box input:focus { outline: 2px solid #00d4ff; }
        .login-box button { width: 100%; padding: 12px; border-radius: 10px; border: none; background: #4CAF50; color: #fff; font-size: 18px; font-weight: bold; cursor: pointer; }
        .login-box button:hover { background: #45a049; }
        .login-box button.secondary { background: #00d4ff; color: #1a1a2e; }
        .login-box button.secondary:hover { background: #00b8e6; }
        .login-box .error { color: #ff6b6b; font-size: 14px; margin-top: 10px; min-height: 20px; }
        .login-box .toggle-link { color: #00d4ff; cursor: pointer; margin-top: 12px; display: inline-block; font-size: 14px; }
        .login-box .toggle-link:hover { text-decoration: underline; }
        .btn-group { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
        .btn-group button { padding: 5px 14px; border-radius: 6px; border: none; cursor: pointer; font-size: 12px; font-weight: bold; }
        .btn-leave { background: #e94560; color: #fff; }
        .btn-resign { background: #ff6b6b; color: #fff; }
        .btn-draw { background: #ffd93d; color: #1a1a2e; }
        .btn-leave:hover, .btn-resign:hover { opacity: 0.8; }
        .admin-actions { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
        .admin-actions button { font-size: 11px; padding: 2px 8px; border-radius: 4px; border: none; cursor: pointer; }
        .admin-actions .ban-btn { background: #e94560; color: #fff; }
        .admin-actions .mute-btn { background: #f39c12; color: #fff; }
        .admin-actions .kick-btn { background: #ff6b6b; color: #fff; }
        .admin-actions .admin-btn { background: #00d4ff; color: #1a1a2e; }
        .admin-actions .admin-remove-btn { background: #ff4444; color: #fff; }
        .admin-actions .protected-badge { background: #ffd93d; color: #1a1a2e; font-size: 9px; padding: 1px 6px; border-radius: 8px; margin-left: 4px; }
        .hidden { display: none !important; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: #00d4ff; border-radius: 4px; }
        .player-item { display: flex; justify-content: space-between; align-items: center; padding: 2px 6px; border-radius: 4px; font-size: 13px; }
        .player-item .badge { font-size: 10px; padding: 1px 6px; border-radius: 10px; margin-left: 4px; }
        .badge.admin { background: #ff6b6b; color: #fff; }
        .badge.banned { background: #e94560; color: #fff; }
        .badge.muted { background: #f39c12; color: #fff; }
        .badge.you { background: #00d4ff; color: #1a1a2e; }
        .badge.playing { background: #4CAF50; color: #fff; }
        .badge.protected { background: #ffd93d; color: #1a1a2e; }
        .badge.ai { background: #00ff88; color: #1a1a2e; }
        .ranking-item { display: flex; justify-content: space-between; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
        .ranking-item .rank { color: #ffd93d; font-weight: bold; margin-right: 8px; }
        .ranking-item .name { flex: 1; }
        .ranking-item .stats { color: #888; font-size: 11px; }
        .ranking-item.top1 { background: rgba(255, 215, 0, 0.15); }
        .ranking-item.top2 { background: rgba(192, 192, 192, 0.1); }
        .ranking-item.top3 { background: rgba(205, 127, 50, 0.1); }
        .admin-panel { background: #0f0f23; border-radius: 8px; padding: 8px; margin-top: 4px; border: 1px solid #ffd93d33; }
        .admin-panel .title { color: #ffd93d; font-size: 12px; margin-bottom: 4px; }
        .admin-panel .admin-list { max-height: 80px; overflow-y: auto; font-size: 12px; }
        .admin-panel .admin-item { display: flex; justify-content: space-between; align-items: center; padding: 2px 4px; border-bottom: 1px solid #1a1a2e; }
        .admin-panel .admin-item .name { color: #ff6b6b; }
        .admin-panel .admin-item .protected-tag { color: #ffd93d; font-size: 9px; margin-left: 4px; }
        .admin-panel .admin-item button { font-size: 10px; padding: 1px 6px; border-radius: 3px; border: none; cursor: pointer; background: #ff4444; color: #fff; }
        .admin-panel .admin-item button:disabled { background: #555; cursor: not-allowed; opacity: 0.5; }
        .admin-panel .admin-item button:hover:not(:disabled) { opacity: 0.8; }
        .muted-banner { background: #f39c12; color: #1a1a2e; padding: 4px 8px; border-radius: 4px; font-size: 12px; text-align: center; margin-bottom: 4px; }
        .auto-kick-notice { background: #ff6b6b33; border: 1px solid #ff6b6b; color: #ff6b6b; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; font-size: 13px; text-align: center; }
        .room-owner-badge { background: #00d4ff; color: #1a1a2e; font-size: 9px; padding: 1px 6px; border-radius: 8px; margin-left: 4px; }
        .create-row { display: flex; gap: 6px; flex-wrap: wrap; }
        .create-row input { flex: 1; padding: 6px 10px; border-radius: 6px; border: none; background: #1a1a2e; color: #fff; outline: 2px solid transparent; min-width: 80px; }
        .create-row input:focus { outline: 2px solid #00d4ff; }
        .create-row button { padding: 6px 14px; border-radius: 6px; border: none; color: #fff; cursor: pointer; font-weight: bold; }
        .create-row .pvp-btn { background: #4CAF50; }
        .create-row .pvp-btn:hover { background: #45a049; }
        .create-row .ai-btn { background: #00d4ff; color: #1a1a2e; }
        .create-row .ai-btn:hover { background: #00b8e6; }
        .ranking-tabs { display: flex; gap: 8px; margin-bottom: 4px; flex-wrap: wrap; }
        .ranking-tabs button { padding: 3px 12px; border-radius: 4px; border: none; cursor: pointer; font-size: 12px; background: #1a1a2e; color: #888; }
        .ranking-tabs button.active { background: #ffd93d; color: #1a1a2e; }
        .ranking-tabs button:hover:not(.active) { background: #2c3e50; }
        .last-move-indicator { position: relative; }
        .banned-list { background: #1a1a2e; border-radius: 8px; padding: 8px; max-height: 100px; overflow-y: auto; font-size: 12px; margin-top: 4px; }
        .banned-list .banned-item { display: flex; justify-content: space-between; padding: 2px 4px; border-bottom: 1px solid #0f0f23; color: #ff6b6b; }
        .banned-list .banned-item .unban-btn { background: #4CAF50; border: none; color: #fff; border-radius: 3px; padding: 1px 8px; cursor: pointer; font-size: 11px; }
        .banned-list .banned-item .unban-btn:hover { background: #45a049; }
        .banned-list .empty { color: #666; text-align: center; padding: 10px 0; }
        .broadcast-input-row { display: flex; gap: 4px; margin-top: 4px; }
        .broadcast-input-row input { flex: 1; padding: 3px 6px; border-radius: 4px; border: none; background: #1a1a2e; color: #fff; font-size: 12px; outline: 2px solid transparent; }
        .broadcast-input-row input:focus { outline: 2px solid #ff6b6b; }
        .broadcast-input-row button { padding: 3px 12px; border-radius: 4px; border: none; background: #ff6b6b; color: #fff; cursor: pointer; font-size: 12px; font-weight: bold; }
        .broadcast-input-row button:hover { background: #e94560; }
        .chat-help { font-size: 10px; color: #666; margin-top: 2px; }
        .chat-help .cmd { color: #ffd93d; background: #1a1a2e; padding: 0 4px; border-radius: 2px; }
    </style>
</head>
<body>

<div class="login-overlay" id="loginOverlay">
    <div class="login-box">
        <h2 id="loginTitle">🎯 联机五子棋</h2>
        <div class="subtitle" id="loginSubtitle">登录你的账号</div>
        <input type="text" id="usernameInput" placeholder="用户名..." maxlength="20">
        <input type="password" id="passwordInput" placeholder="密码..." maxlength="30">
        <div id="confirmPasswordGroup" class="hidden">
            <input type="password" id="confirmPasswordInput" placeholder="确认密码..." maxlength="30">
        </div>
        <button id="loginBtn">登录</button>
        <div class="error" id="loginError"></div>
        <span class="toggle-link" id="toggleAuthLink">还没有账号？去注册</span>
    </div>
</div>

<div class="container" id="mainApp">
    <div class="header">
        <h1>♟ 五子棋</h1>
        <div>
            <span id="statusBadge" class="status online">在线</span>
            <span id="userDisplay" style="margin-left:10px;color:#aaa;">游客</span>
            <span id="roleBadge" class="hidden" style="margin-left:6px;font-size:11px;padding:2px 8px;border-radius:10px;background:#ff6b6b;color:#fff;">管理员</span>
        </div>
    </div>
    <div class="main">
        <div class="board-area">
            <canvas id="boardCanvas" width="540" height="540"></canvas>
            <div style="margin-top:8px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
                <span id="gameInfo" style="color:#aaa;font-size:14px;">💡 创建房间开始游戏</span>
                <div class="btn-group">
                    <button class="btn-leave" id="leaveBtn" disabled>离开</button>
                    <button class="btn-resign" id="resignBtn" disabled>认输</button>
                </div>
            </div>
        </div>
        <div class="side-panel">
            <div>
                <div class="panel-title">🏠 创建房间</div>
                <div class="create-row" style="margin-bottom:6px;">
                    <input type="text" id="roomNameInput" placeholder="房间名..." maxlength="20">
                    <button class="pvp-btn" id="createPvpBtn">👥 真人</button>
                    <button class="ai-btn" id="createAiBtn">🤖 AI</button>
                </div>
                <div class="panel-title" style="margin-top:6px;">📋 房间列表</div>
                <div class="room-list" id="roomList"><div style="color:#666;text-align:center;padding:20px 0;">暂无房间</div></div>
            </div>
            <div>
                <div class="panel-title">👥 在线玩家 <span id="playerCount" style="color:#888;font-size:12px;font-weight:normal;"></span></div>
                <div class="player-list" id="playerList"><div style="color:#666;text-align:center;padding:10px 0;">暂无玩家</div></div>
            </div>
            <div>
                <div class="ranking-tabs">
                    <button class="active" id="pvpRankingTab">🏆 真人对战</button>
                    <button id="aiRankingTab">🤖 AI练手</button>
                </div>
                <div class="ranking-list" id="rankingList"><div style="color:#666;text-align:center;padding:10px 0;">暂无数据</div></div>
            </div>
            <div id="adminPanel" class="admin-panel hidden">
                <div class="title">👑 管理员管理</div>
                <div class="admin-list" id="adminList">
                    <div style="color:#666;text-align:center;padding:4px 0;">加载中...</div>
                </div>
                <div style="margin-top:4px;display:flex;gap:4px;">
                    <input type="text" id="newAdminInput" placeholder="用户名..." style="flex:1;padding:3px 6px;border-radius:4px;border:none;background:#1a1a2e;color:#fff;font-size:12px;">
                    <button id="addAdminBtn" style="padding:3px 10px;border-radius:4px;border:none;background:#4CAF50;color:#fff;cursor:pointer;font-size:12px;">设为管理员</button>
                </div>
                <div class="title" style="margin-top:8px;">📢 系统广播</div>
                <div class="broadcast-input-row">
                    <input type="text" id="broadcastInput" placeholder="输入广播消息..." maxlength="200">
                    <button id="broadcastBtn">📢 发送</button>
                </div>
                <div class="title" style="margin-top:8px;">🚫 封禁列表</div>
                <div class="banned-list" id="bannedList">
                    <div class="empty">暂无封禁用户</div>
                </div>
            </div>
            <div class="chat-box">
                <div class="panel-title">💬 聊天</div>
                <div class="chat-messages" id="chatMessages"></div>
                <div class="chat-input">
                    <input type="text" id="chatInput" placeholder="说点什么..." maxlength="200">
                    <button id="sendBtn">发送</button>
                </div>
                <div class="chat-help">💡 管理员可用 <span class="cmd">/broadcast 消息</span> 或 <span class="cmd">/广播 消息</span> 发送全服公告</div>
            </div>
        </div>
    </div>
</div>

<script>
const socket = io();

// ===== H2 修复：所有上行事件统一经 sEmit 发送，自动附带会话 token =====
// 服务端校验 payload._token 与登录时签发的 token 一致，防止跨连接身份冒充
function sEmit(event, data) {
    if (state.token) {
        if (data === undefined || data === null) {
            data = { _token: state.token };
        } else if (typeof data === 'object' && !Array.isArray(data)) {
            if (!('_token' in data)) data._token = state.token;
        } else {
            // 非对象载荷（字符串/数字），包装为 {data: 原始值, _token}
            data = { data: data, _token: state.token };
        }
    }
    socket.emit(event, data);
}

const state = {
    token: '',
    username: '',
    roomId: null,
    color: null,
    board: null,
    currentTurn: 1,
    gameOver: false,
    isWatcher: false,
    pendingMove: null,
    myTurn: false,
    isAdmin: false,
    isMuted: false,
    isRoomOwner: false,
    isAiRoom: false,
    showAIRanking: false,
    lastMove: null
};

const canvas = document.getElementById('boardCanvas');
const ctx = canvas.getContext('2d');
const CELL = 540 / 16;
const OFFSET = CELL;

const loginOverlay = document.getElementById('loginOverlay');
const usernameInput = document.getElementById('usernameInput');
const passwordInput = document.getElementById('passwordInput');
const confirmPasswordInput = document.getElementById('confirmPasswordInput');
const confirmPasswordGroup = document.getElementById('confirmPasswordGroup');
const loginBtn = document.getElementById('loginBtn');
const loginError = document.getElementById('loginError');
const toggleAuthLink = document.getElementById('toggleAuthLink');
const loginTitle = document.getElementById('loginTitle');
const loginSubtitle = document.getElementById('loginSubtitle');

let isLoginMode = true;

const statusBadge = document.getElementById('statusBadge');
const userDisplay = document.getElementById('userDisplay');
const roleBadge = document.getElementById('roleBadge');
const gameInfo = document.getElementById('gameInfo');
const roomList = document.getElementById('roomList');
const playerList = document.getElementById('playerList');
const playerCount = document.getElementById('playerCount');
const rankingList = document.getElementById('rankingList');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const roomNameInput = document.getElementById('roomNameInput');
const createPvpBtn = document.getElementById('createPvpBtn');
const createAiBtn = document.getElementById('createAiBtn');
const leaveBtn = document.getElementById('leaveBtn');
const resignBtn = document.getElementById('resignBtn');
const adminPanel = document.getElementById('adminPanel');
const adminList = document.getElementById('adminList');
const newAdminInput = document.getElementById('newAdminInput');
const addAdminBtn = document.getElementById('addAdminBtn');
const pvpRankingTab = document.getElementById('pvpRankingTab');
const aiRankingTab = document.getElementById('aiRankingTab');
const bannedList = document.getElementById('bannedList');
const broadcastInput = document.getElementById('broadcastInput');
const broadcastBtn = document.getElementById('broadcastBtn');

function updateChatInputState() {
    if (state.isMuted) {
        chatInput.disabled = true;
        sendBtn.disabled = true;
        chatInput.placeholder = '🔇 你已被禁言';
        if (!document.querySelector('.muted-banner')) {
            const banner = document.createElement('div');
            banner.className = 'muted-banner';
            banner.textContent = '🔇 你已被禁言，无法发送消息';
            chatMessages.parentNode.insertBefore(banner, chatMessages);
        }
    } else {
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.placeholder = '说点什么...';
        const banner = document.querySelector('.muted-banner');
        if (banner) banner.remove();
    }
}

pvpRankingTab.onclick = () => {
    state.showAIRanking = false;
    pvpRankingTab.classList.add('active');
    aiRankingTab.classList.remove('active');
    sEmit('get_ranking');
};

aiRankingTab.onclick = () => {
    state.showAIRanking = true;
    aiRankingTab.classList.add('active');
    pvpRankingTab.classList.remove('active');
    sEmit('get_ai_ranking');
};

toggleAuthLink.onclick = () => {
    isLoginMode = !isLoginMode;
    if (isLoginMode) {
        loginTitle.textContent = '🎯 联机五子棋';
        loginSubtitle.textContent = '登录你的账号';
        loginBtn.textContent = '登录';
        toggleAuthLink.textContent = '还没有账号？去注册';
        confirmPasswordGroup.classList.add('hidden');
        passwordInput.placeholder = '密码...';
    } else {
        loginTitle.textContent = '📝 注册账号';
        loginSubtitle.textContent = '创建新账号';
        loginBtn.textContent = '注册';
        toggleAuthLink.textContent = '已有账号？去登录';
        confirmPasswordGroup.classList.remove('hidden');
        passwordInput.placeholder = '密码...';
    }
    loginError.textContent = '';
};

loginBtn.onclick = () => {
    const username = usernameInput.value.trim();
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;
    
    if (!username || username.length < 2) {
        loginError.textContent = '用户名至少2个字符';
        return;
    }
    if (!password || password.length < 4) {
        loginError.textContent = '密码至少4个字符';
        return;
    }
    if (!isLoginMode && password !== confirmPassword) {
        loginError.textContent = '两次密码输入不一致';
        return;
    }
    
    if (isLoginMode) {
        sEmit('login', { username, password });
    } else {
        sEmit('register', { username, password });
    }
    loginError.textContent = '⏳ 处理中...';
};

usernameInput.onkeydown = (e) => { if (e.key === 'Enter') loginBtn.click(); };
passwordInput.onkeydown = (e) => { if (e.key === 'Enter') loginBtn.click(); };
confirmPasswordInput.onkeydown = (e) => { if (e.key === 'Enter') loginBtn.click(); };

socket.on('login_success', (data) => {
    loginOverlay.classList.add('hidden');
    state.username = data.username;
    state.isAdmin = data.is_admin || false;
    state.token = data.token || '';   // ===== H2 补丁 =====
    userDisplay.textContent = state.username;
    statusBadge.textContent = '在线';
    statusBadge.className = 'status online';
    if (state.isAdmin) {
        roleBadge.classList.remove('hidden');
        roleBadge.textContent = '👑 管理员';
        adminPanel.classList.remove('hidden');
        sEmit('get_admins');
        sEmit('get_banned_list');
    }
    addChat('系统', `欢迎 ${state.username}！`);
    sEmit('get_ranking');
});

socket.on('register_success', (data) => {
    loginError.textContent = '';
    isLoginMode = true;
    loginTitle.textContent = '🎯 联机五子棋';
    loginSubtitle.textContent = '登录你的账号';
    loginBtn.textContent = '登录';
    toggleAuthLink.textContent = '还没有账号？去注册';
    confirmPasswordGroup.classList.add('hidden');
    passwordInput.placeholder = '密码...';
    passwordInput.value = '';
    confirmPasswordInput.value = '';
    loginError.textContent = '✅ 注册成功！请登录';
    loginError.style.color = '#00ff88';
    setTimeout(() => {
        loginError.style.color = '#ff6b6b';
    }, 2000);
});

socket.on('login_fail', (msg) => {
    loginError.textContent = msg;
});

socket.on('user_info', (data) => {
    state.isMuted = data.is_muted || false;
    updateChatInputState();
    if (data.is_banned) {
        alert('⚠️ 你的账号已被封禁！');
        location.reload();
    }
    if (state.isMuted) {
        addChat('系统', '🔇 你已被禁言');
    } else {
        addChat('系统', '✅ 禁言已解除');
    }
});

socket.on('banned_list_update', (bannedUsers) => {
    if (!bannedUsers || bannedUsers.length === 0) {
        bannedList.innerHTML = '<div class="empty">暂无封禁用户</div>';
        return;
    }
    bannedList.innerHTML = '';
    bannedUsers.forEach(item => {
        const div = document.createElement('div');
        div.className = 'banned-item';
        const nameSpan = document.createElement('span');
        nameSpan.textContent = `🚫 ${item.username}`;
        if (item.banned_by) {
            nameSpan.textContent += ` (由 ${item.banned_by} 封禁)`;
        }
        div.appendChild(nameSpan);
        
        const unbanBtn = document.createElement('button');
        unbanBtn.className = 'unban-btn';
        unbanBtn.textContent = '解封';
        unbanBtn.onclick = () => {
            if (confirm(`确定要解封 ${item.username} 吗？`)) {
                sEmit('admin_unban', { username: item.username });
            }
        };
        div.appendChild(unbanBtn);
        bannedList.appendChild(div);
    });
});

socket.on('room_list', (rooms) => {
    if (!rooms || rooms.length === 0) {
        roomList.innerHTML = '<div style="color:#666;text-align:center;padding:20px 0;">暂无房间</div>';
        return;
    }
    roomList.innerHTML = '';
    rooms.forEach(r => {
        const div = document.createElement('div');
        div.className = 'room-item';
        
        const info = document.createElement('span');
        info.className = 'room-info';
        const status = r.game_over ? '🏁' : '▶️';
        const typeLabel = r.is_ai_room ? '🤖AI' : '👥真人';
        const typeClass = r.is_ai_room ? 'ai' : 'pvp';
        const playerNames = r.players.join(', ');
        // P0 修复（H-1 存储型 XSS 注入点 A/B）：
        //   旧代码用 info.innerHTML = `${status} ${r.name} <span ...>${typeLabel}</span> ...`
        //   拼接，而 r.name（房间名）与 playerNames（用户名）都来自其他用户，
        //   `room_list` 又是广播事件 -> 任何在线用户都会被注入执行。
        //   这里改为 append() 文本节点 + createElement()，字符串不会被当作 HTML 解析。
        const typeEl = document.createElement('span');
        typeEl.className = `room-type ${typeClass}`;
        typeEl.textContent = typeLabel;
        info.append(`${status} ${r.name} `);
        info.appendChild(typeEl);
        info.append(` (${r.players.length}/2) - ${playerNames}`);
        div.appendChild(info);
        
        const actions = document.createElement('span');
        
        const isInRoom = r.players.includes(state.username);
        
        if (isInRoom) {
            const leaveRoomBtn = document.createElement('button');
            leaveRoomBtn.className = 'leave-room-btn';
            leaveRoomBtn.textContent = '离开';
            leaveRoomBtn.onclick = (e) => { 
                e.stopPropagation(); 
                if (confirm('确定要离开房间吗？')) {
                    sEmit('leave_room', r.id);
                }
            };
            actions.appendChild(leaveRoomBtn);
        } else {
            const watchBtn = document.createElement('button');
            watchBtn.className = 'watch-btn';
            watchBtn.textContent = '观战';
            watchBtn.onclick = (e) => { e.stopPropagation(); sEmit('watch_room', r.id); };
            actions.appendChild(watchBtn);
            
            if (!r.is_ai_room) {
                const joinBtn = document.createElement('button');
                joinBtn.className = 'join-btn';
                joinBtn.textContent = r.players.length >= 2 ? '满' : '加入';
                joinBtn.disabled = r.players.length >= 2 || r.game_over;
                joinBtn.onclick = (e) => { e.stopPropagation(); if (!joinBtn.disabled) sEmit('join_room', r.id); };
                actions.appendChild(joinBtn);
            }
        }
        
        if (state.isAdmin && !isInRoom) {
            const closeBtn = document.createElement('button');
            closeBtn.className = 'close-room-btn';
            closeBtn.textContent = '🗑️关闭';
            closeBtn.onclick = (e) => {
                e.stopPropagation();
                if (confirm(`确定要关闭房间 "${r.name}" 吗？所有玩家将被踢出。`)) {
                    sEmit('admin_close_room', r.id);
                }
            };
            actions.appendChild(closeBtn);
        }
        
        div.appendChild(actions);
        roomList.appendChild(div);
    });
});

socket.on('user_list', (users) => {
    if (!users || users.length === 0) {
        playerList.innerHTML = '<div style="color:#666;text-align:center;padding:10px 0;">暂无玩家</div>';
        playerCount.textContent = '';
        return;
    }
    playerList.innerHTML = '';
    playerCount.textContent = `(${users.length}人)`;
    users.forEach(u => {
        const div = document.createElement('div');
        div.className = 'player-item';
        const nameSpan = document.createElement('span');
        nameSpan.textContent = u.username;
        if (u.username === 'xp12喵的AI') {
            const badge = document.createElement('span');
            badge.className = 'badge ai';
            badge.textContent = '🤖';
            nameSpan.appendChild(badge);
        }
        if (u.sid === socket.id) {
            const badge = document.createElement('span');
            badge.className = 'badge you';
            badge.textContent = '我';
            nameSpan.appendChild(badge);
        }
        if (u.banned) {
            const badge = document.createElement('span');
            badge.className = 'badge banned';
            badge.textContent = '🚫';
            nameSpan.appendChild(badge);
        }
        if (u.role === 'admin') {
            const badge = document.createElement('span');
            badge.className = 'badge admin';
            badge.textContent = '👑';
            nameSpan.appendChild(badge);
        }
        div.appendChild(nameSpan);
        
        if (state.isAdmin && u.username !== state.username && u.username !== 'xp12喵的AI') {
            const actions = document.createElement('div');
            actions.className = 'admin-actions';
            
            const banBtn = document.createElement('button');
            banBtn.className = 'ban-btn';
            banBtn.textContent = u.banned ? '解封' : '封禁';
            banBtn.onclick = () => {
                if (u.banned) {
                    if (confirm(`确定要解封 ${u.username} 吗？`)) {
                        sEmit('admin_unban', { username: u.username });
                    }
                } else {
                    if (confirm(`确定要封禁 ${u.username} 吗？`)) {
                        sEmit('admin_ban', { username: u.username });
                    }
                }
            };
            actions.appendChild(banBtn);
            
            const muteBtn = document.createElement('button');
            muteBtn.className = 'mute-btn';
            muteBtn.textContent = '禁言';
            muteBtn.onclick = () => {
                sEmit('admin_mute', { username: u.username });
            };
            actions.appendChild(muteBtn);
            
            const kickBtn = document.createElement('button');
            kickBtn.className = 'kick-btn';
            kickBtn.textContent = '踢出';
            kickBtn.onclick = () => {
                if (confirm(`确定要踢出 ${u.username} 吗？`)) {
                    sEmit('admin_kick', { username: u.username });
                }
            };
            actions.appendChild(kickBtn);
            
            div.appendChild(actions);
        }
        playerList.appendChild(div);
    });
});

socket.on('ranking_update', (ranking) => {
    if (state.showAIRanking) return;
    if (!ranking || ranking.length === 0) {
        rankingList.innerHTML = '<div style="color:#666;text-align:center;padding:10px 0;">暂无数据</div>';
        return;
    }
    rankingList.innerHTML = '';
    ranking.forEach(item => {
        const div = document.createElement('div');
        div.className = 'ranking-item';
        if (item.rank === 1) div.classList.add('top1');
        else if (item.rank === 2) div.classList.add('top2');
        else if (item.rank === 3) div.classList.add('top3');
        
        const rankSpan = document.createElement('span');
        rankSpan.className = 'rank';
        const medals = ['🥇', '🥈', '🥉'];
        rankSpan.textContent = item.rank <= 3 ? medals[item.rank-1] : `#${item.rank}`;
        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'name';
        nameSpan.textContent = item.username + (item.banned ? ' 🚫' : '');
        
        const statsSpan = document.createElement('span');
        statsSpan.className = 'stats';
        statsSpan.textContent = `🏆${item.wins} 败${item.losses} 平${item.draws} (${item.win_rate}%)`;
        
        div.appendChild(rankSpan);
        div.appendChild(nameSpan);
        div.appendChild(statsSpan);
        rankingList.appendChild(div);
    });
});

socket.on('ai_ranking_update', (ranking) => {
    if (!state.showAIRanking) return;
    if (!ranking || ranking.length === 0) {
        rankingList.innerHTML = '<div style="color:#666;text-align:center;padding:10px 0;">暂无数据</div>';
        return;
    }
    rankingList.innerHTML = '';
    ranking.forEach(item => {
        const div = document.createElement('div');
        div.className = 'ranking-item';
        if (item.rank === 1) div.classList.add('top1');
        else if (item.rank === 2) div.classList.add('top2');
        else if (item.rank === 3) div.classList.add('top3');
        
        const rankSpan = document.createElement('span');
        rankSpan.className = 'rank';
        const medals = ['🥇', '🥈', '🥉'];
        rankSpan.textContent = item.rank <= 3 ? medals[item.rank-1] : `#${item.rank}`;
        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'name';
        nameSpan.textContent = item.username;
        
        const statsSpan = document.createElement('span');
        statsSpan.className = 'stats';
        statsSpan.textContent = `🏆${item.wins} 败${item.losses} 平${item.draws} (${item.win_rate}%)`;
        
        div.appendChild(rankSpan);
        div.appendChild(nameSpan);
        div.appendChild(statsSpan);
        rankingList.appendChild(div);
    });
});

socket.on('admin_list', (admins) => {
    if (!admins || admins.length === 0) {
        adminList.innerHTML = '<div style="color:#666;text-align:center;padding:4px 0;">暂无管理员</div>';
        return;
    }
    adminList.innerHTML = '';
    admins.forEach(admin => {
        const item = document.createElement('div');
        item.className = 'admin-item';
        const nameSpan = document.createElement('span');
        nameSpan.className = 'name';
        nameSpan.textContent = admin.username + (admin.username === state.username ? ' (我)' : '');
        if (admin.protected) {
            const tag = document.createElement('span');
            tag.className = 'protected-tag';
            tag.textContent = '🔒 受保护';
            nameSpan.appendChild(tag);
        }
        item.appendChild(nameSpan);
        
        if (admin.username !== state.username) {
            const removeBtn = document.createElement('button');
            removeBtn.textContent = '移除';
            removeBtn.disabled = admin.protected || false;
            removeBtn.title = admin.protected ? '受保护的管理员不能移除' : '';
            removeBtn.onclick = () => {
                if (confirm(`确定要移除 ${admin.username} 的管理员权限吗？`)) {
                    sEmit('admin_remove_admin', { username: admin.username });
                }
            };
            item.appendChild(removeBtn);
        }
        adminList.appendChild(item);
    });
});

socket.on('room_joined', (data) => {
    state.roomId = data.room_id;
    state.color = data.color;
    state.board = data.board;
    state.currentTurn = data.current_turn;
    state.gameOver = false;
    state.isWatcher = data.is_watcher || false;
    state.pendingMove = null;
    state.isRoomOwner = data.is_owner || false;
    state.isAiRoom = data.is_ai_room || false;
    state.lastMove = null;
    
    const colorName = state.color === 1 ? '黑⚫' : state.color === 2 ? '白⚪' : '观战';
    const turnName = state.currentTurn === 1 ? '黑' : '白';
    const roomType = state.isAiRoom ? '🤖 AI练习' : '👥 真人';
    gameInfo.textContent = state.isWatcher ? `🔭 观战 (${roomType})` : `🎮 ${colorName} | 轮到 ${turnName}子 (${roomType})`;
    leaveBtn.disabled = false;
    resignBtn.disabled = state.isWatcher;
    
    addChat('系统', state.isWatcher ? `🔭 你正在观战 (${roomType})` : `你执 ${colorName}，${turnName}子先手 (${roomType})`);
    if (state.isAiRoom && !state.isWatcher && state.color === 1) {
        addChat('系统', '🤖 你执黑先手，xp12喵的AI执白后手');
    }
    drawBoard();
    sEmit('get_room_list');
});

socket.on('game_state', (data) => {
    state.board = data.board;
    state.currentTurn = data.current_turn;
    state.gameOver = data.game_over || false;
    state.lastMove = data.last_move || null;
    state.pendingMove = null;
    
    if (!state.gameOver) {
        const turnName = state.currentTurn === 1 ? '黑' : '白';
        if (state.isWatcher) {
            gameInfo.textContent = `🔭 观战 | 轮到 ${turnName}子`;
        } else {
            gameInfo.textContent = `🎮 轮到 ${turnName}子`;
            state.myTurn = state.color === state.currentTurn;
            if (state.isAiRoom && state.color === 2 && state.currentTurn === 2) {
                addChat('系统', '🤖 xp12喵的AI 正在思考...');
            }
        }
    } else {
        gameInfo.textContent = '🏁 游戏已结束';
        resignBtn.disabled = true;
    }
    drawBoard();
});

socket.on('game_over', (data) => {
    state.gameOver = true;
    state.board = data.board;
    state.lastMove = data.last_move || null;
    const winner = data.winner;
    const reason = data.reason || '';
    
    if (winner) {
        if (winner === 'xp12喵的AI') {
            gameInfo.textContent = '🤖 xp12喵的AI 获胜！';
            addChat('系统', '🤖 xp12喵的AI 赢了！再练练吧！');
        } else {
            gameInfo.textContent = `🏆 ${winner} 获胜！`;
            addChat('系统', `🎉 ${winner} 赢了！`);
        }
    } else {
        gameInfo.textContent = '🤝 平局！';
        addChat('系统', '🤝 平局！');
    }
    resignBtn.disabled = true;
    drawBoard();
    sEmit('get_ranking');
});

socket.on('auto_kicked', (data) => {
    const notice = document.createElement('div');
    notice.className = 'auto-kick-notice';
    notice.textContent = '🚪 ' + (data.reason || '对局已结束，请重新创建或加入房间');
    chatMessages.parentNode.insertBefore(notice, chatMessages);
    
    addChat('系统', '🚪 ' + (data.reason || '对局已结束，你已被自动踢出房间'));
    
    state.roomId = null;
    state.color = null;
    state.board = null;
    state.gameOver = false;
    state.isWatcher = false;
    state.pendingMove = null;
    state.isRoomOwner = false;
    state.isAiRoom = false;
    state.lastMove = null;
    leaveBtn.disabled = true;
    resignBtn.disabled = true;
    gameInfo.textContent = '💡 创建或加入房间开始游戏';
    drawBoard();
    sEmit('get_room_list');
    
    setTimeout(() => {
        if (notice.parentNode) notice.remove();
    }, 5000);
});

socket.on('room_closed', (data) => {
    addChat('系统', `🗑️ 房间 "${data.room_name}" 已被管理员关闭`);
    if (state.roomId === data.room_id) {
        state.roomId = null;
        state.color = null;
        state.board = null;
        state.gameOver = false;
        state.isWatcher = false;
        state.pendingMove = null;
        state.isRoomOwner = false;
        state.isAiRoom = false;
        state.lastMove = null;
        leaveBtn.disabled = true;
        resignBtn.disabled = true;
        gameInfo.textContent = '💡 创建或加入房间开始游戏';
        drawBoard();
        sEmit('get_room_list');
    }
});

// ========== 广播消息特殊处理 ==========
socket.on('chat', (data) => {
    // 检测是否为广播消息
    if (data.username === '📢 系统公告') {
        addBroadcast(data.username, data.message);
    } else {
        addChat(data.username, data.message);
    }
});

socket.on('error', (msg) => {
    addChat('系统', `❌ ${msg}`);
});

socket.on('admin_notification', (msg) => {
    addChat('系统', `🔔 ${msg}`);
});

socket.on('kicked', () => {
    state.token = '';   // ===== H2 补丁 =====
    addChat('系统', '❌ 你已被管理员踢出');
    resetGameState();
});

socket.on('forced_logout', (data) => {
    alert('⚠️ ' + data.reason);
    
    state.token = '';        // ===== H2 补丁 =====
    state.username = '';
    state.roomId = null;
    state.color = null;
    state.board = null;
    state.gameOver = false;
    state.isWatcher = false;
    state.pendingMove = null;
    state.isRoomOwner = false;
    state.isAiRoom = false;
    state.lastMove = null;
    state.isAdmin = false;
    state.isMuted = false;
    
    document.getElementById('mainApp').style.display = 'none';
    loginOverlay.classList.remove('hidden');
    userDisplay.textContent = '游客';
    statusBadge.textContent = '离线';
    statusBadge.className = 'status offline';
    roleBadge.classList.add('hidden');
    adminPanel.classList.add('hidden');
    leaveBtn.disabled = true;
    resignBtn.disabled = true;
    gameInfo.textContent = '💡 创建或加入房间开始游戏';
    
    chatMessages.innerHTML = '';
    drawBoard();
    
    usernameInput.value = '';
    passwordInput.value = '';
    confirmPasswordInput.value = '';
    
    loginError.textContent = '⚠️ ' + data.reason;
    loginError.style.color = '#ff6b6b';
    
    isLoginMode = true;
    loginTitle.textContent = '🎯 联机五子棋';
    loginSubtitle.textContent = '登录你的账号';
    loginBtn.textContent = '登录';
    toggleAuthLink.textContent = '还没有账号？去注册';
    confirmPasswordGroup.classList.add('hidden');
    passwordInput.placeholder = '密码...';
    
    setTimeout(() => {
        usernameInput.focus();
    }, 100);
});

function resetGameState() {
    state.roomId = null;
    state.color = null;
    state.board = null;
    state.gameOver = false;
    state.isWatcher = false;
    state.pendingMove = null;
    state.isRoomOwner = false;
    state.isAiRoom = false;
    state.lastMove = null;
    leaveBtn.disabled = true;
    resignBtn.disabled = true;
    gameInfo.textContent = '💡 创建或加入房间开始游戏';
    drawBoard();
    sEmit('get_room_list');
}

function addChat(username, message) {
    const div = document.createElement('div');
    div.className = 'msg';
    const isSystem = username === '系统';
    const isAdmin = username === '管理员';
    const isAI = username === 'xp12喵的AI';
    
    const userSpan = document.createElement('span');
    userSpan.className = `user ${isSystem ? 'system' : ''} ${isAdmin ? 'admin' : ''} ${isAI ? 'ai' : ''}`;
    userSpan.textContent = (isAI ? '🤖 ' : '') + username + ': ';
    const msgSpan = document.createElement('span');
    msgSpan.textContent = message;
    div.appendChild(userSpan);
    div.appendChild(msgSpan);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    if (chatMessages.children.length > 200) {
        chatMessages.removeChild(chatMessages.firstChild);
    }
}

// ========== 广播消息显示 ==========
function addBroadcast(username, message) {
    const div = document.createElement('div');
    div.className = 'msg broadcast-msg';
    
    const userSpan = document.createElement('span');
    userSpan.className = 'user broadcast';
    userSpan.textContent = username + ': ';
    const msgSpan = document.createElement('span');
    msgSpan.textContent = message;
    div.appendChild(userSpan);
    div.appendChild(msgSpan);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    if (chatMessages.children.length > 200) {
        chatMessages.removeChild(chatMessages.firstChild);
    }
}

sendBtn.onclick = () => {
    if (state.isMuted) {
        addChat('系统', '🔇 你已被禁言，无法发送消息');
        return;
    }
    const msg = chatInput.value.trim();
    if (!msg) return;
    sEmit('chat', msg);
    chatInput.value = '';
};
chatInput.onkeydown = (e) => { if (e.key === 'Enter') sendBtn.click(); };

// ========== 广播功能 ==========
broadcastBtn.onclick = () => {
    if (!state.isAdmin) {
        addChat('系统', '❌ 权限不足，仅管理员可发送广播');
        return;
    }
    const msg = broadcastInput.value.trim();
    if (!msg) {
        addChat('系统', '❌ 请输入广播消息');
        return;
    }
    if (msg.length > 200) {
        addChat('系统', '❌ 广播消息不能超过200字符');
        return;
    }
    sEmit('chat', `/broadcast ${msg}`);
    broadcastInput.value = '';
    addChat('系统', '✅ 广播已发送');
};

broadcastInput.onkeydown = (e) => {
    if (e.key === 'Enter') {
        broadcastBtn.click();
    }
};

createPvpBtn.onclick = () => {
    const name = roomNameInput.value.trim() || '未命名房间';
    sEmit('create_room', { name: name, is_ai: false });
    roomNameInput.value = '';
};

createAiBtn.onclick = () => {
    const name = roomNameInput.value.trim() || 'AI练习';
    sEmit('create_room', { name: name, is_ai: true });
    roomNameInput.value = '';
};

leaveBtn.onclick = () => {
    if (state.roomId) {
        if (confirm('确定要离开房间吗？')) {
            sEmit('leave_room', state.roomId);
            resetGameState();
        }
    }
};

resignBtn.onclick = () => {
    if (state.roomId && !state.gameOver && !state.isWatcher) {
        if (confirm('确定要认输吗？')) {
            sEmit('resign', state.roomId);
        }
    }
};

addAdminBtn.onclick = () => {
    const username = newAdminInput.value.trim();
    if (!username) {
        addChat('系统', '❌ 请输入用户名');
        return;
    }
    if (username === state.username) {
        addChat('系统', '❌ 不能给自己设置管理员');
        return;
    }
    sEmit('admin_add_admin', { username: username });
    newAdminInput.value = '';
};

newAdminInput.onkeydown = (e) => { if (e.key === 'Enter') addAdminBtn.click(); };

// ========== 绘制棋盘（已移除红晕效果） ==========
function drawBoard() {
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#d4a76a';
    ctx.fillRect(0, 0, w, h);
    
    ctx.strokeStyle = '#5a3e1b';
    ctx.lineWidth = 1;
    for (let i = 0; i < 15; i++) {
        const p = OFFSET + i * CELL;
        ctx.beginPath(); ctx.moveTo(OFFSET, p); ctx.lineTo(OFFSET + 14*CELL, p); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(p, OFFSET); ctx.lineTo(p, OFFSET + 14*CELL); ctx.stroke();
    }
    [[3,3],[3,11],[11,3],[11,11],[7,7]].forEach(([r,c]) => {
        ctx.fillStyle = '#5a3e1b';
        ctx.beginPath();
        ctx.arc(OFFSET + c*CELL, OFFSET + r*CELL, 5, 0, 2*Math.PI);
        ctx.fill();
    });
    
    if (!state.board) return;
    for (let r = 0; r < 15; r++) {
        for (let c = 0; c < 15; c++) {
            const val = state.board[r][c];
            if (val === 0) continue;
            const x = OFFSET + c*CELL, y = OFFSET + r*CELL;
            const radius = CELL * 0.42;
            // 移除阴影效果，不再有红晕
            const grad = ctx.createRadialGradient(x-radius*0.3, y-radius*0.3, radius*0.1, x, y, radius);
            if (val === 1) {
                grad.addColorStop(0, '#444');
                grad.addColorStop(0.7, '#222');
                grad.addColorStop(1, '#000');
            } else {
                grad.addColorStop(0, '#fff');
                grad.addColorStop(0.6, '#f0f0f0');
                grad.addColorStop(1, '#ccc');
            }
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, 2*Math.PI);
            ctx.fillStyle = grad;
            ctx.fill();
            // 移除白棋高光
        }
    }
    
    // 最后落子标记（保留红圈，移除发光效果）
    if (state.lastMove) {
        const row = state.lastMove[0];
        const col = state.lastMove[1];
        const x = OFFSET + col * CELL;
        const y = OFFSET + row * CELL;
        
        // 外圈红圈 - 保留
        ctx.strokeStyle = '#ff1744';
        ctx.lineWidth = 3.5;
        ctx.beginPath();
        ctx.arc(x, y, CELL * 0.48, 0, 2 * Math.PI);
        ctx.stroke();
        
        // 内圈 - 保留
        ctx.strokeStyle = 'rgba(255, 23, 68, 0.8)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, CELL * 0.35, 0, 2 * Math.PI);
        ctx.stroke();
        
        // 移除光晕效果（红晕的核心来源）
        ctx.shadowBlur = 0;
    }
}

canvas.onclick = (e) => {
    if (state.isWatcher || state.gameOver || !state.board || state.color !== state.currentTurn) {
        if (state.isWatcher) addChat('系统', '观战中不能下棋');
        return;
    }
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const mx = (e.clientX - rect.left) * scaleX;
    const my = (e.clientY - rect.top) * scaleY;
    
    let minDist = CELL * 0.5;
    let target = null;
    for (let r = 0; r < 15; r++) {
        for (let c = 0; c < 15; c++) {
            const x = OFFSET + c*CELL, y = OFFSET + r*CELL;
            const d = Math.hypot(mx - x, my - y);
            if (d < minDist) { minDist = d; target = {row: r, col: c}; }
        }
    }
    if (!target) return;
    if (state.board[target.row][target.col] !== 0) {
        state.pendingMove = null;
        drawBoard();
        return;
    }
    
    if (!state.pendingMove) {
        state.pendingMove = target;
        drawBoard();
        const x = OFFSET + target.col*CELL, y = OFFSET + target.row*CELL;
        ctx.strokeStyle = '#ff0000';
        ctx.lineWidth = 3;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.arc(x, y, CELL*0.45, 0, 2*Math.PI);
        ctx.stroke();
        ctx.setLineDash([]);
        addChat('系统', `已选 (${target.row+1}, ${target.col+1})，再次点击确认`);
        return;
    }
    
    if (state.pendingMove.row === target.row && state.pendingMove.col === target.col) {
        sEmit('place_piece', { room_id: state.roomId, row: target.row, col: target.col });
        state.pendingMove = null;
    } else {
        state.pendingMove = target;
        addChat('系统', `已换选 (${target.row+1}, ${target.col+1})，再次点击确认`);
        drawBoard();
        const x = OFFSET + target.col*CELL, y = OFFSET + target.row*CELL;
        ctx.strokeStyle = '#ff0000';
        ctx.lineWidth = 3;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.arc(x, y, CELL*0.45, 0, 2*Math.PI);
        ctx.stroke();
        ctx.setLineDash([]);
    }
};

window.onbeforeunload = () => {
    if (state.roomId) sEmit('leave_room', state.roomId);
};

document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !loginOverlay.classList.contains('hidden')) {
        loginBtn.click();
    }
});

console.log('🎯 五子棋联机版已加载 - AI对手: xp12喵的AI');
console.log('📢 管理员可使用 /broadcast 消息 发送全服广播');
</script>
</body>
</html>
'''

@app.route('/')
def index():
    # P0 修复（H-1 纵深防御）：给页面自身的内联 <script> 打上本次请求的 CSP
    #   nonce。CSP 的 script-src 里有 'nonce-xxx' 但没有 'unsafe-inline'，
    #   因此只有带正确 nonce 的内联脚本才会执行；攻击者注入的
    #   <svg onload=...> / <img onerror=...> 拿不到 nonce，无法运行。
    nonce = getattr(g, 'csp_nonce', '')
    page = HTML_PAGE.replace('<script>', '<script nonce="%s">' % nonce, 1)
    return page

# ============ Socket 事件 ============
@socketio.on('connect')
def handle_connect(auth=None):
    clients[request.sid] = {"username": None, "room_id": None}
    invalidate_auth(request.sid)  # H2：新连接无身份
    # P2 修复（L-2）：新连接先加入 'anon' 房间。
    #   广播时按房间区分内容：匿名只收到机器人占位，已认证才收到完整名单。
    #   旧代码对所有新连接无条件下发完整在线用户名与 role（admin/user）。
    join_room('anon')
    broadcast_users()
    broadcast_ranking()
    broadcast_ai_ranking()
    # 使用 list() 快照：broadcast_* 期间可能有新连接插入/移除 clients
    for sid, client in list(clients.items()):
        if is_admin(client.get("username")):
            broadcast_banned_list()
            break

# ============ 修改: 修复断开连接判输逻辑 ============
@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接 - 判离开者输"""
    sid = request.sid
    client = clients.get(sid)
    
    if not client:
        return
    
    username = client.get("username")
    room_id = client.get("room_id")
    
    # 关键修复：断开连接时正确处理判输逻辑
    if username and room_id and room_id in rooms:
        handle_player_leave(username, room_id, is_disconnect=True)
    
    # 发送离线消息
    if username:
        socketio.emit('chat', {"username": "系统", "message": f"👋 {username} 已离线"})
    
    # 清理客户端记录
    if sid in clients:
        del clients[sid]
    invalidate_auth(sid)  # H2：断开时清除 token 缓存
    
    # 广播更新
    broadcast_users()
    broadcast_rooms()
    broadcast_ranking()
    broadcast_ai_ranking()

@socketio.on('register')
def handle_register(data):
    ip = request.environ.get('REMOTE_ADDR', '')
    # P1 修复（M-2）：注册限速真正生效。
    #   旧代码读的是 _login_ip_attempts，而该字典只在登录失败时递增，
    #   注册路径自身从不计数 -> 实测 8 次连发全部成功（无限注册）。
    if not register_rate_ok(ip):
        emit('login_fail', '操作过于频繁，请稍后再试')
        return

    if not isinstance(data, dict):
        emit('login_fail', '参数格式错误')
        return

    username = sanitize_input(data.get('username'), MAX_USERNAME_LEN)
    password = data.get('password', '')
    if isinstance(password, str):
        password = password[:MAX_PASSWORD_LEN]
    else:
        password = ''
    
    if not username or len(username) < 2:
        emit('login_fail', '用户名至少2个字符')
        return
    
    if not password or len(password) < 4:
        emit('login_fail', '密码至少4个字符')
        return
    
    users = load_users()
    # M1 修复：统一消息防枚举（合并"已注册"/"已保留"为同一条）
    if username in users or username in PROTECTED_ADMINS or username in RESERVED_NAMES:
        emit('login_fail', '该用户名不可用')
        return

    # P0 修复（H-1 纵深防御）：用户名黑名单校验。
    #   sanitize_input 已经删掉 '<' 和 '>'，这里再拦一次引号/反引号/反斜杠，
    #   避免任何人把这些字符写进 users.json 后，未来某个新增的渲染路径
    #   又用字符串拼接的方式把它们带进 HTML 属性上下文。
    #   采用黑名单而不是严格白名单，是为了不破坏现有的中文/emoji 用户名。
    if re.search(r'[<>"\'`\\]', username):
        emit('login_fail', '用户名包含不允许的字符')
        return

    users[username] = {
        'password': hash_password(password),
        'role': 'user',
        'created_at': datetime.now().isoformat(),
        'banned': False
    }
    save_users(users)
    emit('register_success', {'username': username})

@socketio.on('login')
def handle_login(data):
    sid = request.sid
    ip = request.environ.get('REMOTE_ADDR', '')
    if not isinstance(data, dict):
        emit('login_fail', '参数格式错误')
        return
    username = sanitize_input(data.get('username'), MAX_USERNAME_LEN)
    password = data.get('password', '')
    if isinstance(password, str):
        password = password[:MAX_PASSWORD_LEN]
    else:
        password = ''

    if not username or not password:
        emit('login_fail', '用户名或密码错误')
        return

    # P0 修复（H-2 账号锁定型 DoS）：
    #   真正会阻断请求的只有【来源 IP 级】封锁；账号级失败绝不拒绝请求。
    if _ip_login_blocked(ip):
        emit('login_fail', '该来源尝试过于频繁，请稍后再试')
        return

    users = load_users()

    if username not in users:
        # M1 修复：常量时间——无论用户是否存在都执行一次 PBKDF2 验证
        verify_password(password, '0' * 32 + '$100000$' + '0' * 64)
        _record_login_fail(username, ip)
        # 渐进延迟只惩罚这个 (账号, 来源IP) 组合，不影响他人正常登录。
        # 关键顺序：先 emit 再 sleep。旧顺序会先阻塞工作线程再回复，
        # 客户端 20s 超时被拖垮（登录限速本身反而变成 DoS 放大器）。
        emit('login_fail', '用户名或密码错误')
        _backoff_sleep(_login_delay(username, ip))
        return

    user = users[username]

    # M1 修复：封禁也返回统一错误（防枚举封禁状态）
    if username in banned_users or user.get('banned', False):
        verify_password(password, '0' * 32 + '$100000$' + '0' * 64)
        _record_login_fail(username, ip)
        emit('login_fail', '用户名或密码错误')
        _backoff_sleep(_login_delay(username, ip))
        return

    stored_password = user.get('password', '')
    # H4 修复：仅接受 PBKDF2（salt$iterations$hash）格式，不再兼容裸 SHA-256
    # 遗留裸哈希账号已在 init_admin 启动时重置为临时随机密码
    password_valid = verify_password(password, stored_password)

    if not password_valid:
        _record_login_fail(username, ip)
        # 渐进延迟：只退避这个 (账号, 来源IP) 组合，不影响真实用户从别处登录
        emit('login_fail', '用户名或密码错误')
        _backoff_sleep(_login_delay(username, ip))
        return

    # M1：登录成功，清除失败计数（只清该来源 IP 的记录，账号计数缓慢衰减）
    _clear_login_fail(username, ip)
    
    for cid, client in list(clients.items()):
        if cid != sid and client.get("username") == username:
            socketio.emit('kicked', to=cid)
            clients[cid]["username"] = None
            clients[cid]["room_id"] = None
            invalidate_auth(cid)  # H2：踢出旧连接时作废其 token
            # 被踢下的连接退回匿名状态
            leave_room('auth', sid=cid)
            join_room('anon', sid=cid)

    clients[sid]["username"] = username
    # P2 修复（L-2）：登录成功后把本连接从 'anon' 房间移到 'auth' 房间，
    #   这样后续广播才会把完整在线名单推给它；未登录连接永远留在 'anon'。
    leave_room('anon')
    join_room('auth')
    is_admin_user = is_admin(username)
    
    # ===== H2 补丁：签发会话 token =====
    token = issue_token(sid, username)
    
    emit('login_success', {
        'username': username,
        'is_admin': is_admin_user,
        'token': token
    })
    
    emit('user_info', {
        'is_muted': username in muted_users,
        'is_banned': False
    })
    
    broadcast_users()
    broadcast_rooms()
    broadcast_ranking()
    broadcast_ai_ranking()
    
    if is_admin_user:
        broadcast_banned_list()
    
    socketio.emit('chat', {"username": "系统", "message": f"🎉 {username} 加入了游戏"})
@socketio.on('create_room')
def handle_create_room(data):
    sid = request.sid
    # ===== H2 补丁：校验 token =====
    auth = require_auth(sid, data)
    if not auth:
        return
    username = auth[0]
    
    if is_banned(username):
        emit('error', '账号已被封禁')
        return
    # ... 后面完全不变
    
    if clients[sid].get("room_id"):
        emit('error', '你已在房间中，请先离开')
        return
    
    name = data.get('name', '未命名房间')
    is_ai = data.get('is_ai', False)
    
    clean_name = sanitize_input(name, MAX_ROOM_NAME_LEN)
    if not clean_name:
        clean_name = "未命名房间"
    
    room_id = str(uuid.uuid4())[:8]
    
    if is_ai:
        rooms[room_id] = {
            "name": clean_name + " 🤖",
            "owner": username,
            "players": [username, "xp12喵的AI"],
            "player_colors": {username: 1, "xp12喵的AI": 2},
            "board": create_board(),
            "current_turn": 1,
            "game_over": False,
            "is_ai_room": True,
            "ai_color": 2,
            "last_move": None
        }
    else:
        rooms[room_id] = {
            "name": clean_name,
            "owner": username,
            "players": [username],
            "player_colors": {username: 1},
            "board": create_board(),
            "current_turn": 1,
            "game_over": False,
            "is_ai_room": False,
            "ai_color": None,
            "last_move": None
        }
    
    clients[sid]["room_id"] = room_id
    join_room(room_id)
    emit('room_joined', {
        "room_id": room_id,
        "color": 1,
        "board": rooms[room_id]["board"],
        "current_turn": 1,
        "is_watcher": False,
        "is_owner": True,
        "is_ai_room": is_ai
    })
    broadcast_rooms()
    if is_ai:
        socketio.emit('chat', {"username": "系统", "message": f"🤖 {username} 创建了AI练习房间 '{clean_name}'，你执黑先行，xp12喵的AI执白"}, to=room_id)
    else:
        socketio.emit('chat', {"username": "系统", "message": f"🏠 {username} 创建了房间 '{clean_name}'"}, to=room_id)

@socketio.on('join_room')
def handle_join_room(payload):
    sid = request.sid
    # ===== H2 补丁：校验 token + 取 _data =====
    auth = require_auth(sid, payload)
    if not auth:
        return
    username = auth[0]
    room_id = payload.get('data') if isinstance(payload, dict) else payload
    
    if is_banned(username):
        emit('error', '账号已被封禁')
        return
    # ... 后面完全不变（room_id 照常用）
    
    if clients[sid].get("room_id"):
        emit('error', '你已在房间中，请先离开')
        return
    
    if not re.match(r'^[a-f0-9]{8}$', room_id):
        emit('error', '无效的房间ID')
        return
    
    room = rooms.get(room_id)
    if not room:
        emit('error', '房间不存在')
        return
    
    if room.get("is_ai_room", False):
        emit('error', 'AI房间不能加入')
        return
    
    if username in room["players"]:
        emit('error', '你已经在房间中')
        return
    
    if len(room["players"]) >= MAX_PLAYERS_PER_ROOM:
        emit('error', '房间已满')
        return
    if room.get("game_over", False):
        emit('error', '游戏已结束')
        return
    
    color = 2
    room["players"].append(username)
    room["player_colors"][username] = color
    clients[sid]["room_id"] = room_id
    join_room(room_id)
    
    emit('room_joined', {
        "room_id": room_id,
        "color": color,
        "board": room["board"],
        "current_turn": room["current_turn"],
        "is_watcher": False,
        "is_owner": False,
        "is_ai_room": False
    })
    
    socketio.emit('game_state', {
        "board": room["board"],
        "current_turn": room["current_turn"],
        "game_over": room["game_over"],
        "last_move": room.get("last_move", None)
    }, to=room_id)
    socketio.emit('chat', {"username": "系统", "message": f"{username} 加入了房间"}, to=room_id)
    broadcast_rooms()

@socketio.on('watch_room')
def handle_watch_room(payload):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, payload)
    if not auth:
        return
    username = auth[0]
    room_id = payload.get('data') if isinstance(payload, dict) else payload
    
    # ... 后面完全不变（room_id 照常用）
    
    if is_banned(username):
        emit('error', '账号已被封禁')
        return
    
    if clients[sid].get("room_id"):
        emit('error', '你已在房间中，请先离开')
        return
    
    if not re.match(r'^[a-f0-9]{8}$', room_id):
        emit('error', '无效的房间ID')
        return
    
    room = rooms.get(room_id)
    if not room:
        emit('error', '房间不存在')
        return
    
    clients[sid]["room_id"] = room_id
    join_room(room_id)
    emit('room_joined', {
        "room_id": room_id,
        "color": None,
        "board": room["board"],
        "current_turn": room["current_turn"],
        "is_watcher": True,
        "is_owner": False,
        "is_ai_room": room.get("is_ai_room", False)
    })
    broadcast_rooms()

@socketio.on('place_piece')
def handle_place_piece(data):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, data)
    if not auth:
        return
    username = auth[0]
    
    room_id = data.get("room_id")
    row = data.get("row")
    col = data.get("col")
    
    if not username or not room_id:
        return
    # ... 后面完全不变
    
    try:
        row = int(row)
        col = int(col)
        if row < 0 or row >= BOARD_SIZE or col < 0 or col >= BOARD_SIZE:
            emit('error', '位置超出棋盘')
            return
    except (ValueError, TypeError):
        emit('error', '无效的位置')
        return
    
    room = rooms.get(room_id)
    if not room or room.get("game_over", False):
        return
    
    color = room["player_colors"].get(username)
    if not color or room["current_turn"] != color:
        emit('error', '还没轮到你')
        return
    
    if room["board"][row][col] != 0:
        emit('error', '这个位置已有棋子')
        return
    
    room["board"][row][col] = color
    room["last_move"] = (row, col)
    
    if check_win(room["board"], row, col, color):
        room["game_over"] = True
        winner_name = username
        loser_name = None
        for player, clr in room["player_colors"].items():
            if player != username and player != "xp12喵的AI":
                loser_name = player
                break
        
        if room.get("is_ai_room", False):
            update_ai_ranking(username, 'win')
            update_ai_ranking("xp12喵的AI", 'lose')
            socketio.emit('chat', {"username": "xp12喵的AI", "message": "你赢了！我下次会更强的！💪"}, to=room_id)
        else:
            update_ranking(winner_name, loser_name)
        
        socketio.emit('game_over', {
            "winner": winner_name,
            "board": room["board"],
            "reason": "五子连珠",
            "last_move": (row, col)
        }, to=room_id)
        socketio.emit('chat', {"username": "系统", "message": f"🎉 {winner_name} 赢了！"}, to=room_id)
        broadcast_rooms()
        if not room.get("is_ai_room", False):
            broadcast_ranking()
        else:
            broadcast_ai_ranking()
        return
    
    if is_board_full(room["board"]):
        room["game_over"] = True
        players = list(room["player_colors"].keys())
        
        if room.get("is_ai_room", False) and len(players) >= 1:
            for p in players:
                if p != "xp12喵的AI":
                    update_ai_ranking(p, 'draw')
                    update_ai_ranking("xp12喵的AI", 'draw')
                    break
            socketio.emit('chat', {"username": "xp12喵的AI", "message": "平局了！你很不错！🤝"}, to=room_id)
        elif len(players) >= 2 and not room.get("is_ai_room", False):
            update_ranking_draw(players[0], players[1])
        
        socketio.emit('game_over', {
            "winner": None,
            "board": room["board"],
            "reason": "平局",
            "last_move": (row, col)
        }, to=room_id)
        socketio.emit('chat', {"username": "系统", "message": "🤝 平局！"}, to=room_id)
        broadcast_rooms()
        if not room.get("is_ai_room", False):
            broadcast_ranking()
        else:
            broadcast_ai_ranking()
        return
    
    room["current_turn"] = 1 if color == 2 else 2
    
    socketio.emit('game_state', {
        "board": room["board"],
        "current_turn": room["current_turn"],
        "game_over": False,
        "last_move": (row, col)
    }, to=room_id)
    
    if room.get("is_ai_room", False) and not room.get("game_over", False):
        ai_color = room.get("ai_color", 2)
        if room["current_turn"] == ai_color:
            socketio.start_background_task(lambda: ai_make_move(room_id))

@socketio.on('leave_room')
def handle_leave_room(payload):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, payload)
    if not auth:
        return
    username = auth[0]
    room_id = payload.get('data') if isinstance(payload, dict) else payload
    
    if username:
        handle_player_leave(username, room_id, is_disconnect=False)
    clients[sid]["room_id"] = None
    leave_room(room_id)
    broadcast_rooms()
    broadcast_ranking()
    broadcast_ai_ranking()
    emit('left_room', {'room_id': room_id})

@socketio.on('resign')
def handle_resign(payload):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, payload)
    if not auth:
        return
    username = auth[0]
    room_id = payload.get('data') if isinstance(payload, dict) else payload
    
    room = rooms.get(room_id)
    # ... 后面完全不变
    if not room or room.get("game_over", False):
        return
    
    if username not in room["player_colors"]:
        emit('error', '你不是游戏玩家')
        return
    
    room["game_over"] = True
    winner = None
    loser = username
    for player, color in room["player_colors"].items():
        if player != username:
            winner = player
            break
    
    if room.get("is_ai_room", False):
        update_ai_ranking("xp12喵的AI", 'win')
        update_ai_ranking(username, 'lose')
        socketio.emit('chat', {"username": "xp12喵的AI", "message": "认输了？下次加油哦！😊"}, to=room_id)
    elif winner:
        update_ranking(winner, loser)
    
    socketio.emit('game_over', {
        "winner": winner or "对方",
        "board": room["board"],
        "reason": f"{username} 认输",
        "last_move": room.get("last_move", None)
    }, to=room_id)
    socketio.emit('chat', {"username": "系统", "message": f"{username} 认输了"}, to=room_id)
    broadcast_rooms()
    if not room.get("is_ai_room", False):
        broadcast_ranking()
    else:
        broadcast_ai_ranking()

# ========== 聊天 + 广播功能 ==========
@socketio.on('chat')
def handle_chat(payload):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, payload)
    if not auth:
        return
    username = auth[0]
    # 取消息内容
    if isinstance(payload, dict):
        message = payload.get('data', '')
    else:
        message = payload
    
    if username in muted_users:
    # ... 后面完全不变（message 来自上面）
        emit('error', '你已被禁言')
        return
    
    if is_banned(username):
        emit('error', '账号已被封禁')
        return

    # P1 修复（M-1）：聊天限速真正生效。
    #   旧代码里 chat_rate_ok() 定义了却从未被调用（死代码），
    #   CHAT_MAX_PER_10S / BROADCAST_MAX_PER_HOUR 两个常量也从未被引用。
    #   实测攻击者 2 秒内连发 40 条，观察者收到 40 条。
    if not chat_rate_ok(username):
        emit('error', '发送过于频繁，请稍后再试')
        return

    # P3 修复（L-5）：广播指令判断移到清洗之前。
    #   旧代码对 clean_message 判断 startswith('/broadcast')，而旧的
    #   sanitize_input() 会删除所有 '/'，导致该分支永远不可达（功能失效）。
    #   新 sanitize_input 已不再删除 '/'，这里仍显式使用原始 message 判断，
    #   语义更清晰。
    raw_message = message if isinstance(message, str) else ''

    clean_message = sanitize_input(message, MAX_CHAT_MSG_LEN)
    if not clean_message:
        return

    # ========== 广播命令：/broadcast 或 /广播 ==========
    if raw_message.startswith('/broadcast') or raw_message.startswith('/广播'):
        # 检查是否为管理员
        if not is_admin(username):
            emit('error', '❌ 权限不足，仅管理员可发送广播')
            return

        # P2 修复：管理广播限速（BROADCAST_MAX_PER_HOUR 此前是死常量）
        if not broadcast_rate_ok(username):
            emit('error', '❌ 广播发送过于频繁，请稍后再试')
            return

        # 提取广播内容
        broadcast_content = clean_message.split(' ', 1)
        if len(broadcast_content) < 2 or not broadcast_content[1].strip():
            emit('error', '❌ 用法: /broadcast 消息内容 或 /广播 消息内容')
            return
        
        broadcast_msg = broadcast_content[1].strip()
        
        # 限制广播消息长度
        if len(broadcast_msg) > 200:
            broadcast_msg = broadcast_msg[:200] + '...'
        
        # 构建广播消息
        broadcast_prefix = "📢 系统广播"
        if username == 'admin':
            broadcast_prefix = "👑 管理员广播"
        elif username in PROTECTED_ADMINS:
            broadcast_prefix = "⭐ 系统管理员广播"
        
        final_message = f"【{broadcast_prefix}】{broadcast_msg}"
        
        # 向所有在线用户发送广播（包括发送者自己）
        socketio.emit('chat', {
            "username": "📢 系统公告", 
            "message": final_message
        })
        
        # 打印广播日志到控制台
        print(f"[广播] {username}: {final_message}")
        return
    
    # ========== 普通聊天 ==========
    room_id = clients[sid].get("room_id")
    if room_id:
        socketio.emit('chat', {"username": username, "message": clean_message}, to=room_id)
    else:
        socketio.emit('chat', {"username": username, "message": clean_message})

@socketio.on('get_ranking')
def handle_get_ranking(payload=None):
    # P2 修复（L-3）：按连接限速，防止匿名连接无限触发全量广播
    if not broadcast_trigger_ok(request.sid):
        return
    broadcast_ranking()

@socketio.on('get_ai_ranking')
def handle_get_ai_ranking(payload=None):
    if not broadcast_trigger_ok(request.sid):
        return
    broadcast_ai_ranking()

@socketio.on('get_banned_list')
def handle_get_banned_list(payload=None):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, payload)
    if not auth:
        return
    username = auth[0]
    if not is_admin(username):
        return
    broadcast_banned_list()

# ============ 管理员功能 ============
@socketio.on('admin_ban')
def handle_admin_ban(data):
    global banned_users
    
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, data)
    if not auth:
        return
    admin_name = auth[0]
    if not is_admin(admin_name):
        emit('error', '权限不足')
        return
    # ... 后面完全不变
    
    target = sanitize_input(data.get('username'), MAX_USERNAME_LEN)
    if not target:
        emit('error', '请指定用户名')
        return
    
    users = load_users()
    if target not in users:
        emit('error', '用户不存在')
        return
    
    if users[target].get('role') == 'admin':
        emit('error', '不能封禁管理员')
        return
    
    banned_users.add(target)
    users[target]['banned'] = True
    users[target]['banned_at'] = datetime.now().isoformat()
    users[target]['banned_by'] = admin_name
    save_users(users)
    save_banned_list(banned_users)
    
    for sid, client in list(clients.items()):
        if client.get("username") == target:
            socketio.emit('kicked', to=sid)
            socketio.emit('user_info', {'is_banned': True, 'is_muted': target in muted_users}, to=sid)
            socketio.emit('error', '账号已被封禁', to=sid)
            room_id = client.get("room_id")
            if room_id and room_id in rooms:
                handle_player_leave(target, room_id, is_disconnect=True)
            client["room_id"] = None
            leave_room(room_id)
    
    broadcast_rooms()
    socketio.emit('admin_notification', f'封禁了用户 {target}')
    broadcast_users()
    broadcast_ranking()
    broadcast_ai_ranking()
    broadcast_banned_list()

@socketio.on('admin_unban')
def handle_admin_unban(data):
    global banned_users
    
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, data)
    if not auth:
        return
    admin_name = auth[0]
    if not is_admin(admin_name):
        emit('error', '权限不足')
        return
    
    target = sanitize_input(data.get('username'), MAX_USERNAME_LEN)
    if not target:
        emit('error', '请指定用户名')
        return
    
    if target not in banned_users:
        emit('error', '该用户未被封禁')
        return
    
    banned_users.remove(target)
    
    users = load_users()
    if target in users:
        users[target]['banned'] = False
        if 'banned_at' in users[target]:
            del users[target]['banned_at']
        if 'banned_by' in users[target]:
            del users[target]['banned_by']
        save_users(users)
    
    save_banned_list(banned_users)
    
    for sid, client in list(clients.items()):
        if client.get("username") == target:
            socketio.emit('user_info', {'is_banned': False, 'is_muted': target in muted_users}, to=sid)
            socketio.emit('admin_notification', '你已被解封，可以正常登录了', to=sid)
    
    socketio.emit('admin_notification', f'解封了用户 {target}')
    broadcast_users()
    broadcast_ranking()
    broadcast_ai_ranking()
    broadcast_banned_list()

@socketio.on('admin_mute')
def handle_admin_mute(data):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, data)
    if not auth:
        return
    admin_name = auth[0]
    if not is_admin(admin_name):
        emit('error', '权限不足')
        return
    
    target = sanitize_input(data.get('username'), MAX_USERNAME_LEN)
    if not target:
        emit('error', '请指定用户名')
        return
    
    if target == admin_name:
        emit('error', '不能禁言自己')
        return
    
    if target not in load_users():
        emit('error', '用户不存在')
        return
    
    is_muted = target not in muted_users
    
    if is_muted:
        muted_users.add(target)
        msg = f'禁言了 {target}'
    else:
        muted_users.remove(target)
        msg = f'解除了 {target} 的禁言'
    
    save_muted(muted_users)
    
    for sid, client in list(clients.items()):
        if client.get("username") == target:
            socketio.emit('user_info', {'is_muted': is_muted, 'is_banned': target in banned_users}, to=sid)
            socketio.emit('admin_notification', f'你已被{"禁言" if is_muted else "解除禁言"}', to=sid)
    
    socketio.emit('admin_notification', msg)
    broadcast_users()

@socketio.on('admin_kick')
def handle_admin_kick(data):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, data)
    if not auth:
        return
    admin_name = auth[0]
    if not is_admin(admin_name):
        emit('error', '权限不足')
        return
    
    target = sanitize_input(data.get('username'), MAX_USERNAME_LEN)
    if not target:
        emit('error', '请指定用户名')
        return
    
    if target == admin_name:
        emit('error', '不能踢出自己')
        return
    
    users = load_users()
    if users.get(target, {}).get('role') == 'admin':
        emit('error', '不能踢出管理员')
        return
    
    kicked_count = 0
    for sid, client in list(clients.items()):
        if client.get("username") == target:
            room_id = client.get("room_id")
            if room_id and room_id in rooms:
                handle_player_leave(target, room_id, is_disconnect=True)
            client["room_id"] = None
            leave_room(room_id)
            
            client["username"] = None
            # P2 修复（L-2）：被踢出的连接退回匿名房间，不再收到完整名单
            leave_room('auth', sid=sid)
            join_room('anon', sid=sid)
            invalidate_auth(sid)
            
            socketio.emit('forced_logout', {
                'reason': f'你已被管理员 {admin_name} 踢出'
            }, to=sid)
            
            kicked_count += 1
    
    if kicked_count == 0:
        emit('error', '用户不在线')
        return
    
    socketio.emit('admin_notification', f'👢 管理员 {admin_name} 踢出了用户 {target}')
    broadcast_rooms()
    broadcast_users()
    broadcast_ranking()
    broadcast_ai_ranking()
    
    emit('admin_notification', f'已踢出用户 {target} ({kicked_count} 个连接)')

@socketio.on('admin_close_room')
def handle_admin_close_room(payload):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, payload)
    if not auth:
        return
    admin_name = auth[0]
    room_id = payload.get('data') if isinstance(payload, dict) else payload
    if not is_admin(admin_name):
        emit('error', '权限不足')
        return
    # ... 后面完全不变
    
    if not re.match(r'^[a-f0-9]{8}$', room_id):
        emit('error', '无效的房间ID')
        return
    
    room = rooms.get(room_id)
    if not room:
        emit('error', '房间不存在')
        return
    
    room_name = room.get("name", "未命名房间")
    
    socketio.emit('room_closed', {
        "room_id": room_id,
        "room_name": room_name,
        "reason": "管理员已关闭房间"
    }, to=room_id)
    
    for sid, client in list(clients.items()):
        if client.get("room_id") == room_id:
            client["room_id"] = None
            leave_room(room_id)
    
    if room_id in rooms:
        del rooms[room_id]
    
    socketio.emit('admin_notification', f'🗑️ 管理员 {admin_name} 关闭了房间 "{room_name}"')
    broadcast_rooms()
    broadcast_users()

def get_all_admins():
    users = load_users()
    admins = []
    for username, info in users.items():
        if info.get('role') == 'admin':
            admins.append({
                'username': sanitize_input(username, MAX_USERNAME_LEN),
                'created_at': info.get('created_at', ''),
                'banned': bool(info.get('banned', False)),
                'protected': is_protected_admin(username)
            })
    return admins

@socketio.on('get_admins')
def handle_get_admins(payload=None):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, payload)
    if not auth:
        return
    admin_name = auth[0]
    if not is_admin(admin_name):
        emit('error', '权限不足')
        return
    emit('admin_list', get_all_admins())

@socketio.on('admin_add_admin')
def handle_add_admin(data):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, data)
    if not auth:
        return
    admin_name = auth[0]
    if not is_admin(admin_name):
        emit('error', '权限不足')
        return
    
    target = sanitize_input(data.get('username'), MAX_USERNAME_LEN)
    if not target:
        emit('error', '请指定用户名')
        return
    
    if target == admin_name:
        emit('error', '不能给自己设置管理员')
        return
    
    users = load_users()
    if target not in users:
        emit('error', '用户不存在')
        return
    
    if users[target].get('role') == 'admin':
        emit('error', '该用户已经是管理员')
        return
    
    users[target]['role'] = 'admin'
    save_users(users)
    
    socketio.emit('admin_notification', f'👑 {admin_name} 将 {target} 设为管理员')
    broadcast_users()
    
    for sid, client in list(clients.items()):
        if is_admin(client.get("username")):
            socketio.emit('admin_list', get_all_admins(), to=sid)

@socketio.on('admin_remove_admin')
def handle_remove_admin(data):
    sid = request.sid
    # ===== H2 补丁 =====
    auth = require_auth(sid, data)
    if not auth:
        return
    admin_name = auth[0]
    if not is_admin(admin_name):
        emit('error', '权限不足')
        return
    
    target = sanitize_input(data.get('username'), MAX_USERNAME_LEN)
    if not target:
        emit('error', '请指定用户名')
        return
    
    if is_protected_admin(target):
        emit('error', f'❌ {target} 是受保护的系统管理员，不能被移除')
        return
    
    if target == admin_name:
        emit('error', '不能移除自己的管理员权限')
        return
    
    users = load_users()
    if target not in users:
        emit('error', '用户不存在')
        return
    
    if users[target].get('role') != 'admin':
        emit('error', '该用户不是管理员')
        return
    
    users[target]['role'] = 'user'
    save_users(users)
    
    socketio.emit('admin_notification', f'{admin_name} 移除了 {target} 的管理员权限')
    broadcast_users()
    
    for sid, client in list(clients.items()):
        if is_admin(client.get("username")):
            socketio.emit('admin_list', get_all_admins(), to=sid)

@socketio.on('get_room_list')
def handle_get_room_list(payload=None):
    # P2 修复（L-3）：按连接限速，防止匿名连接无限触发房间列表全量广播。
    # load_users() 已提到循环外（M-3），这里的限速进一步阻断资源放大。
    if not broadcast_trigger_ok(request.sid):
        return
    broadcast_rooms()

# ============ 启动 ============
if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════╗
    ║   🎯 五子棋联机服务器 (AI练习版)         ║
    ║   访问: 见下方 HOST/PORT                  ║
    ║   管理员: 见启动日志(密码仅显示一次)     ║
    ║   AI对手: xp12喵的AI                    ║
    ║   安全特性:                              ║
    ║   ✅ 管理员口令环境变量化/随机生成       ║
    ║   ✅ 会话Token身份校验 (防冒充)          ║
    ║   ✅ 尖括号剥离 + DOM 渲染 (防XSS)       ║
    ║   ✅ CSP nonce 纵深防御                  ║
    ║   ✅ PBKDF2密码哈希 (无裸SHA-256)        ║
    ║   ✅ 登录限速(IP级) + 渐进延迟 + 统一错误║
    ║   ✅ 注册/聊天/广播限速 (防DoS)          ║
    ╚══════════════════════════════════════════╝
    """)
    print(f"    访问: http://localhost:{SERVER_PORT}")
    print(f"    允许的来源(CORS): {_origins}")
    socketio.run(app, host=SERVER_HOST, port=SERVER_PORT, debug=False,
                 allow_unsafe_werkzeug=True)

import json
import time
import threading
from datetime import datetime

import websocket  # pip install websocket-client

# ================= 配置区 =================
WS_URL = "ws://127.0.0.1:5678"
ACCESS_TOKEN = ""

GROUP_ID = 673733353
USER_ID = 3906199433
DURATION = 86400          # 禁言时长，单位秒，1 天 = 86400
CHECK_INTERVAL = 5        # 检测间隔（秒），稍微调大一点避免触发限制
# ==========================================

_lock = threading.Lock()
_ws = None
_echo_id = 0
_pending = {}


def connect():
    global _ws, _echo_id
    header = [f"Authorization: Bearer {ACCESS_TOKEN}"] if ACCESS_TOKEN else []
    _ws = websocket.create_connection(WS_URL, header=header)
    # 【关键修复】重连时清空旧的请求队列，重置 ID，防止拿到过期的返回
    with _lock:
        _pending.clear()
        _echo_id = 0
    threading.Thread(target=_recv_loop, daemon=True).start()
    print(f"{datetime.now():%H:%M:%S} WebSocket 已连接：{WS_URL}")


def _recv_loop():
    """接收消息循环：处理 API 的返回，同时也顺带拦截群禁言事件"""
    while True:
        try:
            raw = _ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            
            # 1. 处理 API 的返回结果
            echo = data.get("echo")
            if echo and echo in _pending:
                _pending[echo] = data
            
            # 2. (可选) 顺带监听群事件，如果是该用户被解除禁言，直接打印出来
            # 这能帮我们判断是 NapCat 没发事件，还是事件发了但列表没更新
            if data.get("post_type") == "notice" and data.get("notice_type") == "group_ban":
                if data.get("user_id") == USER_ID and data.get("group_id") == GROUP_ID:
                    sub_type = data.get("sub_type")
                    if sub_type == "lift_ban":
                        print(f"{datetime.now():%H:%M:%S} [事件通知] 收到 QQ 系统的解除禁言事件！")
                    elif sub_type == "ban":
                        print(f"{datetime.now():%H:%M:%S} [事件通知] 收到 QQ 系统的被禁言事件！")
                        
        except Exception as e:
            print(f"[WS ERROR] 连接断开: {e}")
            time.sleep(3)
            try:
                connect()
            except Exception as e2:
                print(f"[WS RECONNECT FAIL] {e2}")
            break


def call(action: str, params: dict, timeout=10):
    global _echo_id
    with _lock:
        _echo_id += 1
        echo = str(_echo_id)
        _pending[echo] = None
        _ws.send(json.dumps({"action": action, "params": params, "echo": echo}))

    start = time.time()
    while time.time() - start < timeout:
        with _lock:
            res = _pending.get(echo)
            if res is not None:
                return _pending.pop(echo)
        time.sleep(0.05)
    
    with _lock:
        _pending.pop(echo, None)
    return None


def set_ban(user_id: int, duration: int) -> bool:
    """禁言，duration 单位秒；duration=0 表示解除"""
    resp = call("set_group_ban", {
        "group_id": GROUP_ID,
        "user_id": user_id,
        "duration": duration,
    })
    ok = bool(resp) and resp.get("status") == "ok" and resp.get("retcode") == 0
    print(f"{datetime.now():%H:%M:%S} -> {'成功' if ok else '失败'} 禁言 {duration}s"
          f"{'' if ok else '  ' + str(resp)}")
    return ok


def get_shut_list():
    """获取当前群禁言列表"""
    resp = call("get_group_shut_list", {"group_id": GROUP_ID})
    if resp and resp.get("status") == "ok" and resp.get("retcode") == 0:
        return resp["data"]
    print(f"[FAIL] 获取禁言列表失败：{resp}")
    return None


def get_remain_seconds(shut_list) -> int:
    """
    返回该用户的剩余禁言秒数；没被禁返回 0。
    """
    if not shut_list:
        return 0
    now = time.time()
    for item in shut_list:
        # 兼容 user_id 是字符串或整数的情况
        if int(item.get("user_id", 0)) == USER_ID:
            expire_ts = item.get("shut_up_time") or 0
            remain = int(expire_ts - now)
            
            # 【关键调试日志】把拿到的底层数据打印出来！
            dt_str = datetime.fromtimestamp(expire_ts).strftime('%Y-%m-%d %H:%M:%S') if expire_ts else "无"
            print(f"{datetime.now():%H:%M:%S} [DEBUG] 拿到该用户的到期时间戳: {expire_ts} ({dt_str})")
            
            return max(remain, 0)
    
    print(f"{datetime.now():%H:%M:%S} [DEBUG] 禁言列表中【没有找到】该用户")
    return 0


def main():
    connect()
    fail_count = 0
    while True:
        try:
            shut_list = get_shut_list()
            if shut_list is None:
                fail_count += 1
            else:
                remain = get_remain_seconds(shut_list)
                if remain > 0:
                    print(f"{datetime.now():%H:%M:%S} 用户 {USER_ID} 禁言中，剩余 {remain}s")
                    fail_count = 0
                else:
                    print(f"{datetime.now():%H:%M:%S} 用户 {USER_ID} 未被禁言，正在续上...")
                    if set_ban(USER_ID, DURATION):
                        fail_count = 0
                    else:
                        fail_count += 1
        except Exception as e:
            print(f"[LOOP ERROR] {e}")
            try:
                connect()
            except Exception as e2:
                print(f"[RECONNECT FAIL] {e2}")
            fail_count += 1

        wait = min(CHECK_INTERVAL + fail_count * 15, 300)
        time.sleep(wait)


if __name__ == "__main__":
    main()

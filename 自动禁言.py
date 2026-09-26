import json
import time
import threading
from datetime import datetime

import websocket  # pip install websocket-client

WS_URL = "ws://127.0.0.1:8765"
ACCESS_TOKEN = ""

GROUP_ID = 1031177320
USER_ID = 1562389003
DURATION = 100          # 禁言时长，单位秒，1 天 = 86400
CHECK_INTERVAL = 9       # 检测间隔（秒）

_lock = threading.Lock()
_ws = None
_echo_id = 0
_pending = {}


def connect():
    global _ws
    header = [f"Authorization: Bearer {ACCESS_TOKEN}"] if ACCESS_TOKEN else []
    _ws = websocket.create_connection(WS_URL, header=header)
    threading.Thread(target=_recv_loop, daemon=True).start()
    print(f"{datetime.now():%H:%M:%S} WebSocket 已连接：{WS_URL}")


def _recv_loop():
    while True:
        try:
            raw = _ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            echo = data.get("echo")
            if echo and echo in _pending:
                _pending[echo] = data
        except Exception as e:
            print(f"[WS ERROR] {e}")
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
        if _pending.get(echo) is not None:
            return _pending.pop(echo)
        time.sleep(0.05)
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


def is_banned(shut_list) -> int:
    """
    返回该用户的剩余禁言秒数；没被禁返回 0。
    不同 OneBot 实现字段名可能不同，这里做兼容处理。
    """
    if not shut_list:
        return 0
    for item in shut_list:
        if item.get("user_id") == USER_ID:
            # NapCat / Lagrange 常见字段：shut_up_time / duration
            remain = item.get("shut_up_time") or item.get("duration") or 0
            return int(remain)
    return 0


def main():
    connect()
    fail_count = 0
    while True:
        try:
            shut_list = get_shut_list()
            remain = is_banned(shut_list) if shut_list is not None else -1

            if remain == 0:
                print(f"{datetime.now():%H:%M:%S} 用户 {USER_ID} 未被禁言，正在续上...")
                if set_ban(USER_ID, DURATION):
                    fail_count = 0
                else:
                    fail_count += 1
            elif remain > 0:
                print(f"{datetime.now():%H:%M:%S} 用户 {USER_ID} 禁言中，剩余 {remain}s")
                fail_count = 0
            else:
                # 获取失败，等下一轮
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

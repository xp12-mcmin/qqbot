import json
import time
import threading
from datetime import datetime

WS_URL = "ws://127.0.0.1:5678"
ACCESS_TOKEN = ""

GROUP_ID = 1108938540
TARGET_NAME = "服务器共享群2(冷知识jie是萝莉控也是gay)"
INTERVAL = 2

import websocket  # pip install websocket-client

_ws = None
_lock = threading.Lock()
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
    """发送 API 请求并等待响应"""
    global _echo_id
    with _lock:
        _echo_id += 1
        echo = str(_echo_id)
        _pending[echo] = None
        payload = {"action": action, "params": params, "echo": echo}
        _ws.send(json.dumps(payload))

    start = time.time()
    while time.time() - start < timeout:
        if _pending.get(echo) is not None:
            resp = _pending.pop(echo)
            return resp
        time.sleep(0.05)
    _pending.pop(echo, None)
    return None


def get_group_name(group_id: int):
    resp = call("get_group_info", {"group_id": group_id, "no_cache": True})
    if resp and resp.get("status") == "ok" and resp.get("retcode") == 0:
        return resp["data"].get("group_name")
    print(f"[FAIL] 获取群名失败：{resp}")
    return None


def set_group_name(group_id: int, group_name: str) -> bool:
    resp = call("set_group_name", {"group_id": group_id, "group_name": group_name})
    ok = bool(resp) and resp.get("status") == "ok" and resp.get("retcode") == 0
    print(f"{datetime.now():%H:%M:%S} -> {'成功' if ok else '失败'}：{group_name}"
          f"{'' if ok else '  ' + str(resp)}")
    return ok


def main():
    connect()
    fail_count = 0
    while True:
        try:
            current = get_group_name(GROUP_ID)
            if current is not None:
                if current != TARGET_NAME:
                    print(f"{datetime.now():%H:%M:%S} 检测到群名被改为「{current}」，正在还原...")
                    if set_group_name(GROUP_ID, TARGET_NAME):
                        fail_count = 0
                    else:
                        fail_count += 1
                else:
                    print(f"{datetime.now():%H:%M:%S} 群名正常：{current}")
                    fail_count = 0
        except Exception as e:
            print(f"[LOOP ERROR] {e}")
            try:
                connect()
            except Exception as e2:
                print(f"[RECONNECT FAIL] {e2}")
        wait = min(INTERVAL + fail_count * 30, 300)
        time.sleep(wait)


if __name__ == "__main__":
    main()

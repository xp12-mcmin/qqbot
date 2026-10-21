from flask import Flask, request
import json
import logging

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 内存缓存：{ message_id: "消息的文本表示" }
message_cache = {}

def render_message_for_cache(message_array):
    """把消息段数组转成一个方便打印的字符串，图片保留链接"""
    parts = []
    for seg in message_array:
        seg_type = seg.get("type")
        data = seg.get("data", {})
        if seg_type == "text":
            parts.append(data.get("text", ""))
        elif seg_type == "image":
            url = data.get("url") or data.get("file") or "未知图片"
            parts.append(f"[图片] {url}")
        elif seg_type == "face":
            parts.append("[表情]")
        elif seg_type == "at":
            parts.append(f"@{data.get('qq')}")
        # 其他类型可以按需加，暂时忽略或标个[类型]
        else:
            parts.append(f"[{seg_type}]")
    return "".join(parts)

@app.route("/", methods=["POST"])
def handle_onebot_event():
    try:
        data = request.get_json(force=True)
    except Exception:
        return "", 400

    post_type = data.get("post_type")

    # 1. 缓存普通消息（只缓存，不打印，保持日志干净）
    if post_type == "message":
        msg_id = data.get("message_id")
        if msg_id:
            message_cache[msg_id] = render_message_for_cache(data.get("message", []))
        return "", 204

    # 2. 心跳忽略
    if post_type == "meta_event":
        return "", 204

    # 3. 处理撤回
    if post_type == "notice":
        notice_type = data.get("notice_type")
        if notice_type in ("group_recall", "friend_recall"):
            msg_id = data.get("message_id")
            recalled_content = message_cache.get(msg_id, "（缓存中未找到，可能 bot 启动前发的）")

            if notice_type == "group_recall":
                logging.warning(
                    f"🚨 [群撤回] 群:{data.get('group_id')} 用户:{data.get('user_id')} "
                    f"消息ID:{msg_id} 内容: {recalled_content}"
                )
            else:
                logging.warning(
                    f"🚨 [私聊撤回] 用户:{data.get('user_id')} "
                    f"消息ID:{msg_id} 内容: {recalled_content}"
                )

            # 撤回后从缓存删掉，避免越积越多
            message_cache.pop(msg_id, None)

    return "", 204

if __name__ == "__main__":
    logging.info("=== 反撤回监听（含图片缓存）已启动，端口 5700 ===")
    app.run(host="127.0.0.1", port=5700, debug=False)

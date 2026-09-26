import socket

s = socket.socket()
s.connect(("192.168.1.8", 9999))

while True:
    cmd = input(">>> ").strip()
    if not cmd:
        continue
    # 关键：末尾加换行符，匹配服务端的按行分割逻辑
    s.send((cmd + "\n").encode("utf-8"))

    if cmd.lower() == "exit":
        break

    # 循环接收直到收到以 \n 结尾的完整结果
    buffer = b""
    while not buffer.endswith(b"\n"):
        data = s.recv(4096)
        if not data:
            print("[连接已断开]")
            s.close()
            raise SystemExit
        buffer += data

    result = buffer.decode("utf-8", errors="ignore").rstrip("\n")
    print(result)

s.close()

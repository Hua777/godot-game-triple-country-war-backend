import socket

# 定义Telnet服务器的地址和端口
server_address = ('127.0.0.1', 8090)

# 创建Socket对象
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    # 连接到Telnet服务器
    sock.connect(server_address)
    print("Connected to server.")

    while True:
        # 发送数据给服务器
        message = input("Enter message to send (or 'q' to quit): ")
        if message == 'q':
            break
        sock.sendall(message.encode())
        response = sock.recv(1024)
        print("Received response:", response.decode())
finally:
    # 关闭Socket连接
    sock.close()
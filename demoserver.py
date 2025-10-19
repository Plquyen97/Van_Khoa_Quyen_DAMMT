import socket
import threading

# --- Cấu hình Server ---
HOST = '192.168.100.44'
PORT = 56666

clients = []
nicknames = []
lock = threading.Lock()


# --- GỬI DANH SÁCH NGƯỜI DÙNG ---
def send_user_list():
    """Gửi danh sách người dùng online cho tất cả client."""
    with lock:
        user_string = ",".join(nicknames)
        for client in clients:
            try:
                client.send(f"#USERS:{user_string}".encode('utf-8'))
            except:
                remove_client(client)


# --- PHÁT TIN NHẮN ---
def broadcast(message, sender_client=None):
    """Gửi tin nhắn đến tất cả client (trừ người gửi nếu cần)."""
    with lock:
        for client in clients:
            if client != sender_client:
                try:
                    client.send(message.encode('utf-8'))
                except:
                    remove_client(client)


# --- GỬI TIN NHẮN RIÊNG ---
def send_private_message(sender, recipient_name, message):
    """Gửi tin nhắn riêng đến một người cụ thể."""
    with lock:
        if recipient_name in nicknames:
            index = nicknames.index(recipient_name)
            recipient_client = clients[index]
            try:
                recipient_client.send(f"#PRIVATE:{sender}:{message}".encode('utf-8'))
                print(f"[PM] {sender} → {recipient_name}: {message}")
            except:
                remove_client(recipient_client)
        else:
            # Nếu người nhận không tồn tại, báo lỗi cho người gửi
            index = nicknames.index(sender)
            sender_client = clients[index]
            sender_client.send(f"SERVER: Người dùng '{recipient_name}' không tồn tại.".encode('utf-8'))


# --- XÓA CLIENT ---
def remove_client(client):
    """Xóa client khỏi danh sách và thông báo."""
    with lock:
        if client in clients:
            index = clients.index(client)
            nickname = nicknames[index]
            clients.pop(index)
            nicknames.pop(index)
            client.close()
            print(f"[{nickname}] đã ngắt kết nối.")
            broadcast(f"SERVER: {nickname} đã rời khỏi phòng chat!")
            send_user_list()  # Cập nhật danh sách cho mọi người


# --- XỬ LÝ MỖI CLIENT ---
def handle_client(client):
    try:
        # 1. Nhận tên
        client.send("NICK".encode('utf-8'))
        nickname = client.recv(1024).decode('utf-8')

        with lock:
            nicknames.append(nickname)
            clients.append(client)

        print(f"[{nickname}] đã kết nối.")
        broadcast(f"SERVER: {nickname} đã tham gia phòng chat!")
        send_user_list()

        # 2. Nhận tin nhắn
        while True:
            message = client.recv(1024).decode('utf-8')
            if not message:
                break

            if message == "!DISCONNECT":
                break

            # Kiểm tra tin nhắn riêng
            if message.startswith("@"):
                try:
                    recipient_name, private_msg = message[1:].split(" ", 1)
                    send_private_message(nickname, recipient_name, private_msg)
                except ValueError:
                    client.send("SERVER: Cú pháp tin nhắn riêng không hợp lệ. Dùng: @tên nội_dung".encode('utf-8'))
            else:
                broadcast(f"{nickname}: {message}", sender_client=client)

    except ConnectionResetError:
        print(f"Lỗi: {nickname} bị ngắt kết nối đột ngột.")
    except Exception as e:
        print(f"Lỗi từ {nickname}: {e}")
    finally:
        remove_client(client)


# --- CHẠY SERVER ---
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"✅ Server đang lắng nghe trên {HOST}:{PORT}...")

    while True:
        client, address = server.accept()
        print(f"🔗 Kết nối từ {address}")
        thread = threading.Thread(target=handle_client, args=(client,))
        thread.start()


if __name__ == "__main__":
    start_server()

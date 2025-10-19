import customtkinter as ctk
import socket
import threading
from tkinter import simpledialog, messagebox

# --- Cấu hình Mạng ---
HOST = '192.168.100.44'  # IP của Server
PORT = 56666     # Port của Server
client_socket = None
nickname = None

# --- Khởi tạo GUI ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
app = ctk.CTk()
app.title("Ứng Dụng Chat Đa Người Dùng")
app.geometry("500x500")

# --- Khung Hiển Thị Người Dùng ---
users_frame = ctk.CTkFrame(app, width=100)
users_frame.pack(side="right", fill="y", padx=5, pady=5)
users_label = ctk.CTkLabel(users_frame, text="Người Dùng Trực Tuyến:")
users_label.pack(pady=5)
user_list = ctk.CTkTextbox(users_frame, width=100, height=350, state="disabled")
user_list.pack(padx=5, pady=5)

# --- Khung Chat ---
chat_box = ctk.CTkTextbox(app, width=380, height=350, state="disabled")
chat_box.pack(pady=10, side="top", fill="x", padx=10) # Điều chỉnh layout để nằm trên

# --- Khung Nhập Liệu ---
entry = ctk.CTkEntry(app, width=300, placeholder_text="Nhập tin nhắn (Riêng tư: @tên ...)")
entry.pack(side="left", padx=10, pady=5)

# --- Các Hàm Xử Lý GUI và Mạng ---

def update_user_list(users_string):
    """Cập nhật danh sách người dùng vào khung user_list."""
    user_list.configure(state="normal")
    user_list.delete('1.0', 'end') # Xóa nội dung cũ
    
    users = users_string.split(',')
    for user in users:
        user_list.insert('end', f"{user}\n")
        
    user_list.configure(state="disabled")

def update_chat_box(message):
    """Cập nhật nội dung vào khung chat (an toàn cho GUI)."""
    chat_box.configure(state="normal")
    chat_box.insert("end", f"{message}\n")
    chat_box.see("end") # Cuộn xuống cuối
    chat_box.configure(state="disabled")

def send_message(event=None):
    """Lấy tin nhắn từ entry và gửi đến Server."""
    global client_socket
    msg = entry.get()
    entry.delete(0, 'end')
    
    if not msg or client_socket is None:
        return

    try:
        client_socket.send(msg.encode('utf-8'))
    except:
        update_chat_box("LỖI KẾT NỐI: Không thể gửi tin nhắn.")
        if client_socket:
            client_socket.close()
        app.quit()

def receive_messages():
    """Chạy trong luồng riêng, liên tục lắng nghe tin nhắn từ Server."""
    global client_socket, nickname
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            
            if message == 'NICK':
                client_socket.send(nickname.encode('utf-8'))
            
            # XỬ LÝ TIN NHẮN DANH SÁCH NGƯỜI DÙNG (#USERS)
            elif message.startswith("#USERS:"):
                users_string = message[len("#USERS:"):]
                update_user_list(users_string)
            
            else:
                update_chat_box(message)
                
        except ConnectionAbortedError:
            break
        except:
            update_chat_box("--- ĐÃ MẤT KẾT NỐI VỚI MÁY CHỦ ---")
            if client_socket:
                client_socket.close()
            break

def connect_to_server():
    """Xử lý việc kết nối đến Server và nhập nickname."""
    global client_socket, nickname
    
    # 1. Nhập Nickname
    nickname = simpledialog.askstring("Tên Người Dùng", "Vui lòng nhập tên của bạn:", parent=app)
    if not nickname or nickname.strip() == "":
        app.quit()
        return

    # 2. Tạo và Kết nối Socket
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((HOST, PORT))
    except Exception:
        messagebox.showerror("LỖI KẾT NỐI", f"Không thể kết nối đến Máy Chủ tại {HOST}:{PORT}. Vui lòng kiểm tra Server đã chạy chưa.")
        app.quit()
        return

    # 3. Khởi động luồng nhận tin nhắn
    receive_thread = threading.Thread(target=receive_messages)
    receive_thread.daemon = True
    receive_thread.start()

# --- Giao Diện (Tie-up) ---

send_btn = ctk.CTkButton(app, text="Gửi", command=send_message)
send_btn.pack(side="right", padx=10, pady=5)

# Cho phép nhấn Enter để gửi tin nhắn
entry.bind("<Return>", send_message)

# Kết nối Server ngay khi ứng dụng khởi động
app.after(100, connect_to_server)

# Hàm đóng socket khi ứng dụng đóng
def on_closing():
    if client_socket:
        try:
            client_socket.close()
        except:
            pass # Socket đã đóng rồi
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing) 
app.mainloop()

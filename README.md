import customtkinter as ctk
import socket
import threading
from tkinter import simpledialog, messagebox
import time

# --- Cấu hình Mạng ---
HOST = 'localhost'  # IP của Server
PORT = 56666        # Port của Server
client_socket = None
nickname = None

# --- Khởi tạo GUI ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
app = ctk.CTk()
app.title("Ứng Dụng Chat Đa Người Dùng")
app.geometry("500x500")
app.minsize(420, 320)

# --- Status bar (kết nối) ---
status_frame = ctk.CTkFrame(app, height=28)
status_frame.pack(side="top", fill="x", padx=8, pady=(8, 0))
status_label = ctk.CTkLabel(status_frame, text="Trạng thái: Chưa kết nối", anchor="w", font=("Helvetica", 11))
status_label.pack(side="left")

# --- Khung Hiển Thị Người Dùng (CTkScrollableFrame + CTkButton per user) ---
users_frame = ctk.CTkFrame(app, width=140)
users_frame.pack(side="right", fill="y", padx=5, pady=5)
users_label = ctk.CTkLabel(users_frame, text="Người Dùng Trực Tuyến:", font=("Helvetica", 11))
users_label.pack(pady=5)

# Scrollable frame (giữ style customtkinter)
users_scrollable = ctk.CTkScrollableFrame(users_frame, width=140, height=350)
users_scrollable.pack(fill="both", expand=True, padx=5, pady=5)

# Mapping tên -> button widget để dễ highlight / giữ selection
user_buttons = {}
selected_user = None

# Style colors (dễ chỉnh ở 1 chỗ)
SELECTED_BG = "#1F6AA5"
SELECTED_TEXT = "white"
UNSELECTED_BG = "transparent"  # để dùng màu nền mặc định của theme
UNSELECTED_TEXT = None         # để dùng màu chữ mặc định

# --- Khung Chat ---
chat_box = ctk.CTkTextbox(app, width=320, height=350, state="disabled", font=("Helvetica", 11))
chat_box.pack(pady=10, side="top", fill="both", expand=True, padx=10)

# --- Khung Nhập Liệu ---
input_frame = ctk.CTkFrame(app)
input_frame.pack(side="bottom", fill="x", padx=10, pady=5)

msg_var = ctk.StringVar()
entry = ctk.CTkEntry(input_frame, placeholder_text="Nhập tin nhắn (Riêng tư: @tên ...)", textvariable=msg_var)
entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

send_btn = ctk.CTkButton(
    input_frame,
    text="Gửi",
    command=lambda e=None: send_message(),
    width=80,
    height=30,
    corner_radius=6,
    font=("Helvetica", 11)
)
send_btn.pack(side="right", padx=(0, 0), pady=0)
send_btn.configure(state="disabled")

def _on_msg_change(*args):
    text = msg_var.get().strip()
    send_btn.configure(state="normal" if text else "disabled")

msg_var.trace_add("write", _on_msg_change)

# --- Hàm thao tác selection / highlight user (CTkButton) ---
def _make_user_button(name):
    """Tạo một CTkButton cho user (font và kích thước đã trả về cỡ lớn hơn một chút)."""
    btn = ctk.CTkButton(
        users_scrollable,
        text=name,
        width=120,
        height=28,
        corner_radius=5,
        fg_color=UNSELECTED_BG,
        anchor="w",
        command=lambda n=name: select_user(n),
        font=("Helvetica", 11),  # trả lại kích thước chữ cho danh sách user
        hover=False
    )
    return btn

def select_user(name):
    """Gọi khi nhấp vào user: chèn @tên vào entry, focus và highlight."""
    global selected_user
    if not name:
        return
    entry.delete(0, 'end')
    entry.insert(0, f"@{name} ")
    entry.focus()
    highlight_user(name)

def highlight_user(name):
    """Đổi style button tương ứng với user được chọn (tô toàn bộ nền), reset phần còn lại."""
    global selected_user, user_buttons
    # Reset tất cả về trạng thái chưa chọn
    for uname, btn in user_buttons.items():
        try:
            btn.configure(fg_color=UNSELECTED_BG, text_color=UNSELECTED_TEXT, border_width=0)
        except Exception:
            try:
                btn.configure(fg_color=UNSELECTED_BG)
            except:
                pass

    # Áp style cho user được chọn: tô toàn bộ nền
    btn = user_buttons.get(name)
    if btn:
        try:
            btn.configure(fg_color=SELECTED_BG, text_color=SELECTED_TEXT)
        except Exception:
            try:
                btn.configure(fg_color=SELECTED_BG)
            except:
                pass
        selected_user = name
    else:
        selected_user = None

def clear_selection():
    global selected_user
    for btn in user_buttons.values():
        try:
            btn.configure(fg_color=UNSELECTED_BG, text_color=UNSELECTED_TEXT, border_width=0)
        except Exception:
            try:
                btn.configure(fg_color=UNSELECTED_BG)
            except:
                pass
    selected_user = None

# --- Các Hàm Xử Lý GUI và MẠNG ---

def update_user_list(users):
    """Cập nhật danh sách người dùng vào users_scrollable.
    Tham số users có thể là list[str] hoặc string (dấu phẩy phân tách)."""
    global user_buttons, selected_user
    # Chuẩn hoá input về list
    if isinstance(users, str):
        users_string = users.strip()
        if users_string == "":
            users_list_local = []
        else:
            users_list_local = [u.strip() for u in users_string.split(',') if u.strip()]
    elif isinstance(users, list):
        users_list_local = [u.strip() for u in users if u and u.strip()]
    else:
        users_list_local = []

    # Xoá tất cả widget cũ trong scrollable
    for child in users_scrollable.winfo_children():
        child.destroy()
    user_buttons = {}

    # Tạo button cho từng user (với khoảng cách nhỏ để gọn)
    for u in users_list_local:
        btn = _make_user_button(u)
        btn.pack(fill="x", padx=4, pady=3)
        user_buttons[u] = btn

    # Nếu đang chọn user và vẫn tồn tại, giữ highlight
    if selected_user and selected_user in users_list_local:
        highlight_user(selected_user)
    else:
        clear_selection()

def clear_user_list():
    """Xoá danh sách người dùng (ví dụ khi mất kết nối)."""
    for child in users_scrollable.winfo_children():
        child.destroy()
    user_buttons.clear()
    clear_selection()

def update_chat_box(message, with_timestamp=True):
    """Cập nhật nội dung vào khung chat (an toàn cho GUI)."""
    ts = time.strftime("%H:%M") if with_timestamp else ""
    chat_box.configure(state="normal")
    if with_timestamp:
        chat_box.insert("end", f"[{ts}] {message}\n")
    else:
        chat_box.insert("end", f"{message}\n")
    chat_box.see("end")
    chat_box.configure(state="disabled")

def send_message(event=None):
    """Lấy tin nhắn từ entry và gửi đến Server."""
    global client_socket, nickname
    msg = msg_var.get().strip()
    entry.delete(0, 'end')

    if not msg or client_socket is None:
        return

    try:
        client_socket.send(msg.encode('utf-8'))

        # Hiển thị local echo khi gửi thành công
        sender = nickname if nickname else "Bạn"
        if msg.startswith("@"):
            parts = msg.split(' ', 1)
            recipient_token = parts[0]
            content = parts[1] if len(parts) > 1 else ""
            recipient = recipient_token[1:] if len(recipient_token) > 1 else ""
            if content:
                update_chat_box(f"(Bạn ➜ {recipient}) {sender}: {content}")
            else:
                update_chat_box(f"(Bạn ➜ {recipient}) {sender}: {recipient_token}")
        else:
            update_chat_box(f"{sender}: {msg}")

    except Exception:
        update_chat_box("LỖI KẾT NỐI: Không thể gửi tin nhắn.")
        if client_socket:
            try:
                client_socket.close()
            except:
                pass
        app.quit()

def receive_messages():
    """Chạy trong luồng riêng, liên tục lắng nghe tin nhắn từ Server."""
    global client_socket, nickname
    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                update_chat_box("--- MẤT KẾT NỐI VỚI MÁY CHỦ (server đóng kết nối) ---")
                clear_user_list()
                # Chỉ hiển thị "Đã mất kết nối"
                status_label.configure(text="Trạng thái: Đã mất kết nối")
                if client_socket:
                    try:
                        client_socket.close()
                    except:
                        pass
                break

            message = data.decode('utf-8')

            if message == 'NICK':
                client_socket.send(nickname.encode('utf-8'))

            elif message.startswith("#USERS:"):
                users_string = message[len("#USERS:"):].strip()
                update_user_list(users_string)

            elif message.startswith("#JOIN:"):
                joined = message[len("#JOIN:"):].strip()
                update_chat_box(f"--- {joined} đã tham gia ---")
            elif message.startswith("#LEFT:"):
                left = message[len("#LEFT:"):].strip()
                update_chat_box(f"--- {left} đã rời ---")
            else:
                update_chat_box(message)

        except ConnectionAbortedError:
            break
        except Exception:
            update_chat_box("--- ĐÃ MẤT KẾT NỐI VỚI MÁY CHỦ (lỗi) ---")
            clear_user_list()
            status_label.configure(text="Trạng thái: Đã mất kết nối")
            if client_socket:
                try:
                    client_socket.close()
                except:
                    pass
            break

def connect_to_server():
    """Xử Lý kết nối đến Server và nhập nickname."""
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
        # Chỉ hiển thị "Đã kết nối" (kèm label)
        status_label.configure(text="Trạng thái: Đã kết nối")
    except Exception:
        messagebox.showerror("LỖI KẾT NỐI", f"Không thể kết nối đến Máy Chủ tại {HOST}:{PORT}. Vui lòng kiểm tra Server đã chạy chưa.")
        app.quit()
        return

    # 3. Khởi động luồng nhận tin nhắn
    receive_thread = threading.Thread(target=receive_messages)
    receive_thread.daemon = True
    receive_thread.start()

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
            pass
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()

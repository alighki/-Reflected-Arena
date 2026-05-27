import socket
import threading
import pickle
import time

HOST = '0.0.0.0'  # دریافت اتصال از همه IP ها
PORT = 9999

# راه‌اندازی سرور
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(10)
print(f"[!] Server is running and listening on Port {PORT}...")

clients = {}      # آدرس کلاینت -> سوکت
game_state = {}   # آدرس کلاینت -> اطلاعات بازی (موقعیت، رنگ و...)

def handle_client(conn, addr):
    print(f"[+] Player connected from {addr}")
    clients[addr] = conn
    
    # مقادیر پیش‌فرض برای بازیکن جدید
    game_state[addr] = {
        'name': 'Unknown',
        'pos': (0, 10, 0),
        'rot_y': 0,
        'color': (1, 1, 1, 1),
        'alive': True
    }

    while True:
        try:
            # دریافت اطلاعات از کلاینت
            data = conn.recv(4096)
            if not data:
                break
                
            player_update = pickle.loads(data)
            game_state[addr].update(player_update)
            
            # ارسال اطلاعات تمام بازیکنان دیگر به این کلاینت
            # ما آدرس کلاینت را به عنوان ID او می‌فرستیم تا خودش را دو بار رندر نکند
            package = {
                'my_id': addr,
                'players': game_state
            }
            conn.sendall(pickle.dumps(package))
            
        except Exception as e:
            # اگر خطایی رخ داد (مثل قطع شدن ناگهانی) از حلقه خارج شو
            break

    print(f"[-] Player disconnected: {addr}")
    if addr in clients: del clients[addr]
    if addr in game_state: del game_state[addr]
    conn.close()

# حلقه اصلی سرور برای پذیرش بازیکنان جدید
while True:
    conn, addr = server.accept()
    threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

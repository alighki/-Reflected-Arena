import socket
import threading
import pickle
import time
import random
import math

HOST = '0.0.0.0'  # روی تمام اینترفیس‌ها
PORT = 9999

clients = []
player_data = {}  # {player_id: {'pos':(x,y,z), 'color':(r,g,b), 'alive':True, 'speed':5, 'is_ai':False}}

lock = threading.Lock()
arena_size = 40
cube_size = 1.5
boost_duration = 3.0
player_base_speed = 5

def distance(a,b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)

def is_hit_from_back(attacker_pos, target_pos, target_forward):
    # target_forward: Vec3 direction
    dx = attacker_pos[0]-target_pos[0]
    dz = attacker_pos[2]-target_pos[2]
    forward = target_forward
    dot = forward[0]*dx + forward[2]*dz
    return dot < -0.5

def handle_client(conn, addr, player_id):
    global player_data
    print(f"[NEW CONNECTION] {addr} as Player {player_id}")
    with lock:
        # Spawn اولیه در Lobby
        player_data[player_id] = {'pos':(0,0.75,0), 'color':(random.random(),random.random(),random.random()),
                                  'alive':True, 'speed':player_base_speed, 'is_ai':False, 'forward':(0,0,1)}
    while True:
        try:
            data = conn.recv(4096)
            if not data:
                break
            pdata = pickle.loads(data)
            with lock:
                if player_id in player_data:
                    player_data[player_id].update(pdata)
        except:
            break
    with lock:
        if player_id in player_data:
            del player_data[player_id]
    conn.close()
    clients.remove(conn)
    print(f"[DISCONNECTED] Player {player_id}")

def broadcast():
    global player_data
    while True:
        with lock:
            # اضافه کردن AI جایگزین اگر پلیر کمتر باشد
            real_players = [p for p in player_data.values() if not p['is_ai']]
            while len(real_players)<2:  # حداقل 2 در Arena
                ai_id = f"AI_{random.randint(1000,9999)}"
                if ai_id not in player_data:
                    player_data[ai_id] = {'pos':(random.uniform(-arena_size/4,arena_size/4),0.75,
                                                 random.uniform(-arena_size/4,arena_size/4)),
                                          'color':(0,0,1),'alive':True,'speed':player_base_speed*0.8,'is_ai':True,'forward':(0,0,1)}
                    real_players.append(player_data[ai_id])

            # برخوردها و Boost
            ids = list(player_data.keys())
            for i in range(len(ids)):
                for j in range(len(ids)):
                    if i==j: continue
                    attacker = player_data[ids[i]]
                    target = player_data[ids[j]]
                    if not attacker['alive'] or not target['alive']: continue
                    dist = distance(attacker['pos'], target['pos'])
                    if dist<cube_size*1.2 and is_hit_from_back(attacker['pos'], target['pos'], target['forward']):
                        target['alive']=False
                        attacker['speed']=player_base_speed*1.6
                        # Reset speed بعد از چند ثانیه
                        threading.Timer(boost_duration, lambda a=attacker: a.update({'speed':player_base_speed})).start()

            data = pickle.dumps(player_data)
        for c in clients:
            try:
                c.sendall(data)
            except:
                pass
        time.sleep(1/30)

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER RUNNING] Listening on {HOST}:{PORT}")

    threading.Thread(target=broadcast, daemon=True).start()

    player_id_counter = 1
    while True:
        conn, addr = server.accept()
        clients.append(conn)
        threading.Thread(target=handle_client, args=(conn,addr,player_id_counter), daemon=True).start()
        player_id_counter += 1

if __name__=="__main__":
    main()

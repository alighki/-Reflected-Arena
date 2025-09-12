from ursina import *
import socket
import threading
import pickle
import time

HOST = '127.0.0.1'  # IP سرور واقعی
PORT = 9999

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

player_id = None
player_info = {'pos':(0,0.75,0), 'color':(1,0,0), 'alive':True, 'speed':5, 'forward':(0,0,1)}
all_players = {}

def send_to_server():
    while True:
        try:
            client.sendall(pickle.dumps(player_info))
        except:
            break
        time.sleep(1/30)

def receive_from_server():
    global all_players
    while True:
        try:
            data = client.recv(4096)
            if data:
                all_players = pickle.loads(data)
        except:
            break

threading.Thread(target=send_to_server, daemon=True).start()
threading.Thread(target=receive_from_server, daemon=True).start()

app = Ursina(fullscreen=True)
window.title = "Reflected Cube Arena - Online PVP"

# Arena ساده
arena_size = 40
cube_size = 1.5
floor = Entity(model='cube', scale=(arena_size,0.5,arena_size), color=color.black, collider='box', position=(0,-0.25,0))

# پلیر خودی
player = Entity(model='cube', color=color.red, scale=cube_size, position=(0,0.75,0), collider='box')
y_velocity = 0
gravity = 9.8

# HUD ساده
hud = Text('Online PVP', position=Vec2(-0.85,0.45))

# دوربین
camera_pivot = Entity()
camera.parent = camera_pivot
camera.position = Vec3(0,6,-12)
camera.rotation_x = 20
camera.fov = 120
mouse_sensitivity = 40

# Top-View امن
camera_pivot = Entity()
camera.parent = camera_pivot
camera.position = Vec3(0,6,-12)
camera.rotation_x = 20
camera.fov = 120
mouse_sensitivity = 40

arena_started = False
lobby_time = 10
start_time = time.time()

def update():
    global y_velocity, player_info
    # حرکت پلیر local
    move = Vec3(held_keys['d']-held_keys['a'],0,held_keys['w']-held_keys['s'])
    player.position += move*player_info['speed']*time.dt

    # gravity
    y_velocity -= gravity*time.dt
    player.y += y_velocity*time.dt
    if player.y<0.75:
        player.y=0.75
        y_velocity=0

    # forward برای تشخیص برخورد از پشت
    if move.length() > 0:
        player_info['forward'] = (move.normalized().x,0,move.normalized().z)

    # ارسال موقعیت
    player_info['pos'] = (player.x, player.y, player.z)
    player_info['alive'] = True

    # نمایش سایر پلیرها و AI
    for pid, pdata in all_players.items():
        if pid==player_id: continue
        if 'entity' not in pdata:
            pdata['entity'] = Entity(model='cube', color=rgb(*pdata['color']), scale=cube_size)
        pdata['entity'].position = Vec3(*pdata['pos'])
        pdata['entity'].enabled = pdata['alive']

    # دوربین Mouse Look
    camera_pivot.rotation_y += mouse.velocity[0]*mouse_sensitivity

# Jump input
def input(key):
    global y_velocity
    if key=='space' and player.y<=0.75+0.01:
        y_velocity=5

app.run()

from ursina import *
import random, time

app = Ursina(fullscreen=True)
window.title = "Reflected Cube Arena - Stage 8"
window.color = color.rgb(10,10,10)

# Arena
arena_size = 40
arena_height = 10
arena_wall_thickness = 1

floor = Entity(model='cube', scale=(arena_size,0.5,arena_size), color=color.black, collider='box', position=(0,-0.25,0))
walls = [
    Entity(model='cube', scale=(arena_wall_thickness,arena_height,arena_size), color=color.white, collider='box', position=(-arena_size/2,arena_height/2,0)),
    Entity(model='cube', scale=(arena_wall_thickness,arena_height,arena_size), color=color.white, collider='box', position=(arena_size/2,arena_height/2,0)),
    Entity(model='cube', scale=(arena_size,arena_height,arena_wall_thickness), color=color.white, collider='box', position=(0,arena_height/2,-arena_size/2)),
    Entity(model='cube', scale=(arena_size,arena_height,arena_wall_thickness), color=color.white, collider='box', position=(0,arena_height/2,arena_size/2)),
]

# Lobby بالا
lobby_height = 15
lobby_size = 30
lobby_floor = Entity(model='cube', scale=(lobby_size,0.5,lobby_size), color=color.rgb(20,20,20), collider='box', position=(0,lobby_height,0))
def random_lobby_spawn():
    return Vec3(random.uniform(-lobby_size/2+1,lobby_size/2-1),
                lobby_height + 0.75,
                random.uniform(-lobby_size/2+1,lobby_size/2-1))

# پارامترها
cube_size = 1.5
player_base_speed = 5
jump_strength = 5
gravity = 9.8
boost_duration = 3.0
max_players = 4

colors = [color.red,color.green,color.blue,color.yellow]
color_names = {color.red:"Red", color.green:"Green", color.blue:"Blue", color.yellow:"Yellow"}

player_controls = [
    {'up':'w','down':'s','left':'a','right':'d','jump':'space'},
    {'up':'i','down':'k','left':'j','right':'l','jump':'u'},
    {'up':'t','down':'g','left':'f','right':'h','jump':'y'},
    {'up':'up arrow','down':'down arrow','left':'left arrow','right':'right arrow','jump':'right shift'},
]

players = []
for i in range(max_players):
    control = player_controls[i]
    e = Entity(model='cube', color=colors[i], scale=cube_size, position=random_lobby_spawn(), collider='box')
    players.append({
        'entity':e,
        'control':control,
        'is_ai':False,
        'speed':player_base_speed,
        'y_velocity':0,
        'color_name':color_names[colors[i]]
    })

# HUD برای رنگ پلیرها
hud_texts = []
for i,p in enumerate(players):
    t = Text(f'Player {i+1}: {p["color_name"]}', position=Vec2(-0.85,0.4-0.05*i), scale=1, color=p['entity'].color)
    hud_texts.append(t)

# دوربین سوم شخص با Mouse Look
camera_pivot = Entity()
camera.parent = camera_pivot
camera.position = Vec3(0,6,-12)
camera.rotation_x = 20
camera.fov = 120
mouse_sensitivity = 40

arena_started = False
lobby_time = 10
start_time = time.time()

# برخورد از پشت
def is_hit_from_back(attacker,target):
    forward = target['entity'].forward
    dir_vec = (attacker['entity'].position - target['entity'].position).normalized()
    return forward.dot(dir_vec) < -0.5

# Speed boost
def give_speed_boost(p):
    p['speed'] = player_base_speed*1.6
    invoke(reset_speed, p, delay=boost_duration)
def reset_speed(p):
    p['speed'] = player_base_speed

# حرکت پلیرها
def player_movement(p):
    if not p['is_ai'] and p['control']:
        move = Vec3(
            held_keys.get(p['control']['right'],0)-held_keys.get(p['control']['left'],0),
            0,
            held_keys.get(p['control']['up'],0)-held_keys.get(p['control']['down'],0)
        ).normalized()
        p['entity'].position += move*p['speed']*time.dt

    # gravity
    if p['entity'].y>cube_size/2 or p['y_velocity']!=0:
        p['y_velocity'] -= gravity*time.dt
    p['entity'].y += p['y_velocity']*time.dt
    if p['entity'].y<cube_size/2:
        p['entity'].y = cube_size/2
        p['y_velocity']=0

# Update اصلی
def update():
    global arena_started
    # Lobby timer
    if not arena_started and time.time()-start_time > lobby_time:
        for p in players:
            x = random.uniform(-arena_size/4,arena_size/4)
            z = random.uniform(-arena_size/4,arena_size/4)
            p['entity'].position = Vec3(x,cube_size/2,z)
        arena_started = True

    # حرکت هر پلیر
    for p in players:
        player_movement(p)
        # Jump input مستقل
        if not p['is_ai'] and p['control'].get('jump') and held_keys.get(p['control']['jump']):
            if p['entity'].y <= cube_size/2 + 0.01:
                p['y_velocity'] = jump_strength

    # برخوردها
    for attacker in players:
        for target in players:
            if attacker==target: continue
            if attacker['entity'].intersects(target['entity']).hit and is_hit_from_back(attacker,target):
                target['entity'].disable()
                give_speed_boost(attacker)

    # دوربین Mouse Look
    camera_pivot.rotation_y += mouse.delta[0]*mouse_sensitivity*time.dt
    camera.rotation_x -= mouse.delta[1]*mouse_sensitivity*time.dt
    camera.rotation_x = clamp(camera.rotation_x, -80, 80)
p['entity'].x = clamp(p['entity'].x, -arena_size/2 + cube_size/2, arena_size/2 - cube_size/2)
p['entity'].z = clamp(p['entity'].z, -arena_size/2 + cube_size/2, arena_size/2 - cube_size/2)

app.run()

from ursina import *
from ursina.prefabs.health_bar import HealthBar
import random
import math

app = Ursina(fullscreen=False)
window.title = "Reflected Cube Arena - Ultimate Edition"
window.color = color.rgb(15, 15, 20)
window.exit_button.visible = False
window.fps_counter.enabled = True

# ==========================================
# تنظیمات کلی و متغیرهای سراسری (Globals)
# ==========================================
ARENA_SIZE = 50
ARENA_WALL_HEIGHT = 6
ARENA_WALL_THICKNESS = 2
LOBBY_HEIGHT = 25
WINNING_SCORE = 10

# رنگ‌ها و استایل‌ها
COLORS = [color.rgb(255,50,50), color.rgb(50,255,50), color.rgb(50,200,255), color.rgb(255,200,50)]
NAMES = ["Red Reaper", "Green Giant", "Cyan Cyborg", "Yellow Yakuza"]

# ==========================================
# جلوه‌های ویژه (VFX)
# ==========================================
class CameraShake:
    """سیستم لرزش دوربین هنگام انفجار یا ضربات سنگین"""
    def __init__(self):
        self.original_pos = camera.position
        self.shake_amount = 0
        self.shake_duration = 0

    def start_shake(self, amount, duration):
        self.shake_amount = amount
        self.shake_duration = duration

    def update(self):
        if self.shake_duration > 0:
            self.shake_duration -= time.dt
            offset_x = random.uniform(-self.shake_amount, self.shake_amount)
            offset_y = random.uniform(-self.shake_amount, self.shake_amount)
            camera.position = self.original_pos + Vec3(offset_x, offset_y, 0)
        else:
            camera.position = lerp(camera.position, self.original_pos, time.dt * 5)

cam_shake = CameraShake()

class ParticleExplosion(Entity):
    """ذرات معلق هنگام کشته شدن یا انفجار"""
    def __init__(self, position, p_color):
        super().__init__(position=position)
        for _ in range(20):
            p = Entity(parent=self, model='cube', color=p_color, scale=random.uniform(0.2, 0.6))
            direction = Vec3(random.uniform(-1, 1), random.uniform(0.5, 2), random.uniform(-1, 1)).normalized()
            speed = random.uniform(5, 15)
            p.animate_position(p.position + direction * speed, duration=1, curve=curve.out_expo)
            p.animate_scale(0, duration=1, curve=curve.in_expo)
            destroy(p, delay=1.1)
        destroy(self, delay=1.5)

class DashTrail(Entity):
    """رد محو شونده هنگام دش کردن"""
    def __init__(self, target):
        super().__init__(model='cube', color=target.color, scale=target.scale, position=target.position, rotation=target.rotation)
        self.animate_color(color.rgba(self.color.r, self.color.g, self.color.b, 0), duration=0.3)
        self.animate_scale(0, duration=0.3)
        destroy(self, delay=0.3)

# ==========================================
# سیستم سلاح و پرتابه‌ها (Projectiles)
# ==========================================
class Bullet(Entity):
    def __init__(self, position, forward_dir, owner, is_rapid=False):
        super().__init__(
            model='sphere',
            color=color.yellow if is_rapid else color.cyan,
            scale=0.5 if is_rapid else 0.8,
            position=position + forward_dir * 1.5,
            collider='sphere'
        )
        self.forward_dir = forward_dir
        self.speed = 40 if is_rapid else 30
        self.owner = owner
        self.damage = 15 if is_rapid else 25
        self.lifetime = 2.0
        
        # نور گلوله
        PointLight(parent=self, color=self.color, range=5)

    def update(self):
        self.position += self.forward_dir * self.speed * time.dt
        self.lifetime -= time.dt
        if self.lifetime <= 0:
            destroy(self)
            return

        # بررسی برخورد با دیوارها
        if abs(self.x) > ARENA_SIZE/2 or abs(self.z) > ARENA_SIZE/2:
            self.explode()
            return

        # بررسی برخورد با بازیکنان
        for p in game_manager.players:
            if p == self.owner or p.is_dead: continue
            if distance(self.position, p.position) < (p.scale_x/2 + self.scale_x/2 + 0.5):
                p.take_damage(self.damage, self.owner)
                self.explode()
                return

    def explode(self):
        ParticleExplosion(self.position, self.color)
        destroy(self)

# ==========================================
# آیتم‌های قدرتی (Power-ups)
# ==========================================
class PowerUp(Entity):
    def __init__(self, position, p_type):
        colors = {'heal': color.green, 'speed': color.yellow, 'rapid': color.magenta}
        super().__init__(
            model='diamond',
            color=colors[p_type],
            scale=1.2,
            position=position,
            collider='box'
        )
        self.p_type = p_type
        self.bob_offset = random.uniform(0, 10)

    def update(self):
        # انیمیشن چرخش و بالا پایین رفتن
        self.rotation_y += 100 * time.dt
        self.y = 1 + math.sin(time.time() * 3 + self.bob_offset) * 0.5
        
        # برخورد با بازیکن
        for p in game_manager.players:
            if not p.is_dead and distance(self.position, p.position) < 2:
                self.apply_effect(p)
                ParticleExplosion(self.position, self.color)
                destroy(self)
                break

    def apply_effect(self, player):
        if self.p_type == 'heal':
            player.heal(50)
        elif self.p_type == 'speed':
            player.apply_buff('speed', 5.0)
        elif self.p_type == 'rapid':
            player.apply_buff('rapid', 5.0)

# ==========================================
# تله‌ها و محیط داینامیک (Traps & Environment)
# ==========================================
class JumpPad(Entity):
    def __init__(self, position):
        super().__init__(model='cylinder', color=color.orange, scale=(3, 0.2, 3), position=position)
        
    def update(self):
        for p in game_manager.players:
            if not p.is_dead and distance((self.x, 0, self.z), (p.x, 0, p.z)) < 1.5 and p.y < 2:
                p.y_velocity = 30 # پرتاب شدید به بالا
                p.y += 0.5

# ==========================================
# کلاس پایه بازیکن (شامل انسان و هوش مصنوعی)
# ==========================================
class PlayerBase(Entity):
    def __init__(self, index, p_color, name, start_pos):
        super().__init__(
            model='cube', color=p_color, scale=1.5, position=start_pos, collider='box'
        )
        self.index = index
        self.p_name = name
        
        # سیستم وضعیت (Stats)
        self.max_hp = 100
        self.hp = self.max_hp
        self.max_stamina = 100
        self.stamina = self.max_stamina
        
        self.base_speed = 12
        self.speed = self.base_speed
        self.jump_strength = 18
        self.gravity = 45
        self.y_velocity = 0
        
        # متغیرهای گیم‌پلی
        self.score = 0
        self.is_dead = False
        self.is_dashing = False
        self.shoot_cooldown = 0
        self.buffs = {'speed': 0, 'rapid': 0}
        
        # رابط کاربری بالای سر بازیکن
        self.hp_bar_bg = Entity(parent=self, model='quad', scale=(1.5, 0.2), y=1.2, color=color.black, billboard=True)
        self.hp_bar = Entity(parent=self.hp_bar_bg, model='quad', scale=(1, 1), x=0, color=color.green, origin=(-0.5,0))
        self.hp_bar.x = -0.5

        # هاله قدرت
        self.aura = Entity(parent=self, model='cube', color=color.rgba(255,255,255,100), scale=1.3, enabled=False)

    def update_base(self):
        if self.is_dead: return
        
        self.handle_gravity()
        self.handle_buffs()
        self.check_backstab()
        
        # بازسازی استقامت
        if not self.is_dashing and self.stamina < self.max_stamina:
            self.stamina += 20 * time.dt
            
        # کاهش کول‌دان شلیک
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= time.dt
            
        # آپدیت نوار جان
        health_pct = self.hp / self.max_hp
        self.hp_bar.scale_x = health_pct
        self.hp_bar.color = color.green if health_pct > 0.5 else (color.orange if health_pct > 0.2 else color.red)
        
        # سقوط مرگبار
        if self.y < -15:
            self.take_damage(9999, None)

    def handle_gravity(self):
        ground_hit = raycast(self.position, (0, -1, 0), ignore=(self,), distance=self.scale_y/2 + 0.2)
        if ground_hit.hit:
            self.y = ground_hit.world_point.y + self.scale_y/2
            self.y_velocity = 0
        else:
            self.y_velocity -= self.gravity * time.dt
            self.y += self.y_velocity * time.dt

    def handle_buffs(self):
        # مدیریت زمان باف‌ها
        has_buff = False
        if self.buffs['speed'] > 0:
            self.buffs['speed'] -= time.dt
            self.speed = self.base_speed * 1.8
            has_buff = True
        else:
            self.speed = self.base_speed

        if self.buffs['rapid'] > 0:
            self.buffs['rapid'] -= time.dt
            has_buff = True
            
        self.aura.enabled = has_buff

    def apply_buff(self, b_type, duration):
        self.buffs[b_type] = duration

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)
        self.scale = 1.8 # بزرگ شدن موقت
        self.animate_scale(1.5, duration=0.5)

    def shoot(self):
        if self.shoot_cooldown <= 0:
            is_rapid = self.buffs['rapid'] > 0
            Bullet(self.position, self.forward, self, is_rapid)
            self.shoot_cooldown = 0.15 if is_rapid else 0.6
            # لگد اسلحه (Recoil)
            self.position -= self.forward * 0.5

    def dash(self):
        if self.stamina >= 30 and not self.is_dashing:
            self.stamina -= 30
            self.is_dashing = True
            old_speed = self.speed
            self.speed = self.base_speed * 4
            
            # افکت ردِ حرکت
            for i in range(5):
                invoke(DashTrail, self, delay=i*0.05)
                
            invoke(self.end_dash, old_speed, delay=0.2)

    def end_dash(self, old_speed):
        self.speed = old_speed
        self.is_dashing = False

    def check_backstab(self):
        # سیستم خنجر از پشت و برخورد فیزیکی
        for other in game_manager.players:
            if other == self or other.is_dead: continue
            
            if distance(self.position, other.position) < 1.8:
                dir_to_other = (other.position - self.position).normalized()
                dot_prod = other.forward.dot(dir_to_other)
                
                # اگر کاملا پشت حریف بود
                if dot_prod > 0.6 and self.is_dashing:
                    other.take_damage(100, self) # مرگ قطعی
                    self.heal(25)
                    self.apply_buff('speed', 2.0)
                    
                    # افکت متنی
                    Text("BACKSTAB!", position=other.position, color=color.red, scale=2).animate_y(other.y+3, duration=1)

    def take_damage(self, amount, attacker):
        if self.is_dead: return
        self.hp -= amount
        self.blink(color.red, duration=0.2)
        
        if self.hp <= 0:
            self.die(attacker)

    def die(self, killer):
        self.is_dead = True
        self.visible = False
        self.hp_bar_bg.enabled = False
        cam_shake.start_shake(0.5, 0.3)
        ParticleExplosion(self.position, self.color)
        
        if killer and killer != self:
            killer.score += 1
            ui_manager.update_score()
            ui_manager.show_killfeed(f"{killer.p_name} Eliminated {self.p_name}")
            
            if killer.score >= WINNING_SCORE:
                game_manager.end_game(killer)
                return
        else:
            ui_manager.show_killfeed(f"{self.p_name} Fell to their doom")

        if game_manager.state == 'playing':
            invoke(self.respawn, delay=3)

    def respawn(self):
        if game_manager.state != 'playing': return
        self.is_dead = False
        self.visible = True
        self.hp_bar_bg.enabled = True
        self.hp = self.max_hp
        self.stamina = self.max_stamina
        self.y_velocity = 0
        self.buffs = {'speed': 0, 'rapid': 0}
        self.position = Vec3(random.uniform(-ARENA_SIZE/2.5, ARENA_SIZE/2.5), 15, random.uniform(-ARENA_SIZE/2.5, ARENA_SIZE/2.5))
        
        # محافظت هنگام ریسپاون
        self.apply_buff('speed', 1.5)

# ==========================================
# بازیکن انسانی (Human Player)
# ==========================================
class HumanPlayer(PlayerBase):
    def __init__(self, index, controls, p_color, name, start_pos):
        super().__init__(index, p_color, name, start_pos)
        self.controls = controls

    def update(self):
        self.update_base()
        if self.is_dead or game_manager.state != 'playing': return
        
        # حرکت
        move_dir = Vec3(0, 0, 0)
        if held_keys.get(self.controls['right']): move_dir.x += 1
        if held_keys.get(self.controls['left']):  move_dir.x -= 1
        if held_keys.get(self.controls['up']):    move_dir.z += 1
        if held_keys.get(self.controls['down']):  move_dir.z -= 1
        
        if move_dir.length() > 0:
            move_dir = move_dir.normalized()
            self.position += move_dir * self.speed * time.dt
            self.look_at(self.position + move_dir)
            
        # پرش
        ground_hit = raycast(self.position, (0, -1, 0), ignore=(self,), distance=self.scale_y/2 + 0.2)
        if ground_hit.hit and held_keys.get(self.controls['jump']):
            self.y_velocity = self.jump_strength
            
        # شلیک
        if held_keys.get(self.controls['shoot']):
            self.shoot()
            
        # دش
        if held_keys.get(self.controls['dash']):
            self.dash()

# ==========================================
# هوش مصنوعی (Bot Player)
# ==========================================
class BotPlayer(PlayerBase):
    def __init__(self, index, p_color, name, start_pos):
        super().__init__(index, p_color, name, start_pos)
        self.target = None
        self.state = 'chase' # chase, flee, wander
        self.change_state_timer = 0
        self.action_timer = 0

    def update(self):
        self.update_base()
        if self.is_dead or game_manager.state != 'playing': return
        
        self.change_state_timer -= time.dt
        self.action_timer -= time.dt
        
        self.find_target()
        
        if not self.target:
            self.wander()
            return
            
        distance_to_target = distance(self.position, self.target.position)
        
        # تصمیم‌گیری ساده هوش مصنوعی
        if self.hp < 30 and self.target.hp > 30:
            self.state = 'flee'
        elif distance_to_target > 20:
            self.state = 'chase'
        else:
            self.state = 'attack'
            
        # اجرای اکشن بر اساس وضعیت
        if self.state == 'chase':
            self.move_towards(self.target.position)
        elif self.state == 'flee':
            self.move_towards(self.position + (self.position - self.target.position))
            if self.action_timer <= 0:
                self.dash()
                self.action_timer = random.uniform(2, 4)
        elif self.state == 'attack':
            self.move_towards(self.target.position, stop_dist=10)
            self.look_at(self.target.position)
            if self.action_timer <= 0:
                self.shoot()
                self.action_timer = random.uniform(0.2, 0.8)
                
            # احتمال Dash برای خنجر از پشت
            if distance_to_target < 8 and random.random() < 0.05:
                self.dash()

    def find_target(self):
        closest_dist = 9999
        self.target = None
        for p in game_manager.players:
            if p == self or p.is_dead: continue
            dist = distance(self.position, p.position)
            if dist < closest_dist:
                closest_dist = dist
                self.target = p

    def move_towards(self, pos, stop_dist=0):
        dir_vec = (Vec3(pos.x, 0, pos.z) - Vec3(self.x, 0, self.z))
        if dir_vec.length() > stop_dist:
            dir_vec = dir_vec.normalized()
            # جلوگیری از افتادن ساده (اگر جلوتر خالی بود نرو)
            forward_ray = raycast(self.position + Vec3(0,1,0), dir_vec, distance=3)
            down_ray = raycast(self.position + dir_vec*2 + Vec3(0,1,0), (0,-1,0), distance=5)
            
            if not down_ray.hit or (forward_ray.hit and forward_ray.entity in walls):
                # تغییر مسیر تصادفی در صورت بن‌بست
                dir_vec = Vec3(random.uniform(-1,1), 0, random.uniform(-1,1)).normalized()

            self.position += dir_vec * self.speed * time.dt
            self.look_at(self.position + dir_vec)

    def wander(self):
        if self.action_timer <= 0:
            self.target_pos = self.position + Vec3(random.uniform(-10,10), 0, random.uniform(-10,10))
            self.action_timer = random.uniform(1, 3)
        self.move_towards(self.target_pos)

# ==========================================
# سیستم مدیریت رابط کاربری (UI Manager)
# ==========================================
class UIManager(Entity):
    def __init__(self):
        super().__init__()
        self.menus = {}
        self.score_texts = []
        self.killfeed_texts = []
        
        self.setup_main_menu()
        self.setup_hud()
        
    def setup_main_menu(self):
        self.main_menu = Entity(parent=camera.ui)
        Entity(parent=self.main_menu, model='quad', scale=(2,2), color=color.rgba(0,0,0,200))
        Text(parent=self.main_menu, text="REFLECTED CUBE ARENA\nPRO MAX EDITION", scale=3, origin=(0,0), y=0.3, color=color.azure)
        
        Button(parent=self.main_menu, text="PLAY (4 Humans)", scale=(0.4, 0.08), y=0.1, color=color.azure, on_click=lambda: game_manager.start_match(0))
        Button(parent=self.main_menu, text="PLAY (1 Human vs 3 Bots)", scale=(0.4, 0.08), y=0, color=color.orange, on_click=lambda: game_manager.start_match(3))
        Button(parent=self.main_menu, text="AI SPECTATE (4 Bots)", scale=(0.4, 0.08), y=-0.1, color=color.green, on_click=lambda: game_manager.start_match(4))
        Button(parent=self.main_menu, text="QUIT", scale=(0.4, 0.08), y=-0.2, color=color.red, on_click=application.quit)

    def setup_hud(self):
        self.hud = Entity(parent=camera.ui, enabled=False)
        self.center_msg = Text(parent=self.hud, text="", scale=3, origin=(0,0), y=0.2, color=color.white)
        self.center_msg.create_background(color=color.rgba(0,0,0,150))
        
        for i in range(4):
            ui_x = -0.85 if i % 2 == 0 else 0.65
            ui_y = 0.45 - (i // 2) * 0.1
            t = Text(parent=self.hud, text=f"{NAMES[i]}: 0", position=(ui_x, ui_y), scale=1.5, color=COLORS[i])
            self.score_texts.append(t)
            
    def show_menu(self):
        self.main_menu.enabled = True
        self.hud.enabled = False
        
    def hide_menu(self):
        self.main_menu.enabled = False
        self.hud.enabled = True
        
    def update_score(self):
        for i, p in enumerate(game_manager.players):
            self.score_texts[i].text = f"{p.p_name}: {p.score}"
            
    def show_killfeed(self, msg):
        # حرکت متون قبلی به پایین
        for k in self.killfeed_texts:
            k.y -= 0.05
            if k.y < -0.4:
                k.enabled = False
                
        t = Text(parent=self.hud, text=msg, position=(-0.85, -0.2), scale=1.2, color=color.white)
        self.killfeed_texts.append(t)
        destroy(t, delay=4)

# ==========================================
# سیستم مدیریت کل بازی (Game Manager)
# ==========================================
class GameManager(Entity):
    def __init__(self):
        super().__init__()
        self.state = 'menu' # menu, countdown, playing, game_over
        self.players = []
        self.powerup_timer = 0
        
        # ایجاد محیط
        self.build_arena()
        
        # دوربین اصلی
        camera.position = (0, 45, -45)
        camera.look_at((0, 0, 0))
        camera.fov = 65

    def build_arena(self):
        self.arena = Entity()
        Entity(parent=self.arena, model='cube', scale=(ARENA_SIZE, 1, ARENA_SIZE), color=color.dark_gray, 
               texture='white_cube', texture_scale=(ARENA_SIZE/2, ARENA_SIZE/2), collider='box', position=(0, -0.5, 0))
               
        # دیوارهای شیشه‌ای/نئونی
        global walls
        walls = [
            Entity(parent=self.arena, model='cube', scale=(ARENA_WALL_THICKNESS, ARENA_WALL_HEIGHT, ARENA_SIZE), color=color.rgba(0,150,255,150), collider='box', position=(-ARENA_SIZE/2, ARENA_WALL_HEIGHT/2, 0)),
            Entity(parent=self.arena, model='cube', scale=(ARENA_WALL_THICKNESS, ARENA_WALL_HEIGHT, ARENA_SIZE), color=color.rgba(0,150,255,150), collider='box', position=(ARENA_SIZE/2, ARENA_WALL_HEIGHT/2, 0)),
            Entity(parent=self.arena, model='cube', scale=(ARENA_SIZE, ARENA_WALL_HEIGHT, ARENA_WALL_THICKNESS), color=color.rgba(0,150,255,150), collider='box', position=(0, ARENA_WALL_HEIGHT/2, -ARENA_SIZE/2)),
            Entity(parent=self.arena, model='cube', scale=(ARENA_SIZE, ARENA_WALL_HEIGHT, ARENA_WALL_THICKNESS), color=color.rgba(0,150,255,150), collider='box', position=(0, ARENA_WALL_HEIGHT/2, ARENA_SIZE/2)),
        ]
        
        # تله‌ها (Jump Pads)
        JumpPad((10, 0, 10))
        JumpPad((-10, 0, -10))
        JumpPad((10, 0, -10))
        JumpPad((-10, 0, 10))

    def start_match(self, num_bots):
        ui_manager.hide_menu()
        self.state = 'countdown'
        self.timer = 5.0
        
        # کنترل‌های انسان‌ها
        controls = [
            {'up':'w', 'down':'s', 'left':'a', 'right':'d', 'jump':'space', 'dash':'q', 'shoot':'e'},
            {'up':'i', 'down':'k', 'left':'j', 'right':'l', 'jump':'u', 'dash':'o', 'shoot':'p'},
            {'up':'up arrow', 'down':'down arrow', 'left':'left arrow', 'right':'right arrow', 'jump':'right shift', 'dash':'right control', 'shoot':'enter'},
            {'up':'t', 'down':'g', 'left':'f', 'right':'h', 'jump':'y', 'dash':'r', 'shoot':'5'}
        ]
        
        # پاک کردن پلیرهای قبلی
        for p in self.players: destroy(p)
        self.players.clear()
        
        num_humans = 4 - num_bots
        
        for i in range(4):
            start_pos = Vec3(random.uniform(-10,10), 10, random.uniform(-10,10))
            if i < num_humans:
                p = HumanPlayer(i, controls[i], COLORS[i], NAMES[i], start_pos)
            else:
                p = BotPlayer(i, COLORS[i], NAMES[i]+"[BOT]", start_pos)
            self.players.append(p)
            
        ui_manager.update_score()

    def update(self):
        cam_shake.update() # آپدیت لرزش دوربین
        
        if self.state == 'countdown':
            self.timer -= time.dt
            ui_manager.center_msg.enabled = True
            ui_manager.center_msg.text = f"STARTING IN: {math.ceil(self.timer)}"
            
            # در طول شمارش معکوس پلیرها معلق هستند
            for p in self.players:
                p.y_velocity = 0
                p.y = 10
                
            if self.timer <= 0:
                self.state = 'playing'
                ui_manager.center_msg.text = "FIGHT!"
                ui_manager.center_msg.color = color.red
                invoke(self.hide_msg, delay=1.5)
                
        elif self.state == 'playing':
            # تولید شانسی آیتم‌های قدرتی (Powerups)
            self.powerup_timer -= time.dt
            if self.powerup_timer <= 0:
                self.powerup_timer = random.uniform(5, 10)
                p_type = random.choice(['heal', 'speed', 'rapid'])
                spawn_pos = Vec3(random.uniform(-ARENA_SIZE/2.5, ARENA_SIZE/2.5), 1, random.uniform(-ARENA_SIZE/2.5, ARENA_SIZE/2.5))
                PowerUp(spawn_pos, p_type)

    def hide_msg(self):
        ui_manager.center_msg.enabled = False

    def end_game(self, winner):
        self.state = 'game_over'
        ui_manager.center_msg.enabled = True
        ui_manager.center_msg.text = f"{winner.p_name} WINS THE MATCH!"
        ui_manager.center_msg.color = winner.color
        
        for p in self.players:
            p.is_dead = True
            p.visible = False
            
        invoke(self.return_to_menu, delay=5)
        
    def return_to_menu(self):
        self.state = 'menu'
        ui_manager.show_menu()

# ==========================================
# راه‌اندازی و اجرا
# ==========================================
ui_manager = UIManager()
game_manager = GameManager()

app.run()

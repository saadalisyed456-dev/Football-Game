#!/usr/bin/env python3
"""
Football (Local multiplayer) with Shop & Customization
- Supports 2..4 players (Human or CPU)
- Shop: buy Speed / Kick upgrades and color unlocks using in-game coins
- Customize: per-player stickman look (color, head radius, thickness, name)
- Saves configuration to fm_config.json
"""

import pygame, sys, math, json, os, time
from pygame.math import Vector2

# -----------------------
# Config / persistence
# -----------------------
CFG_FILE = "fm_config.json"
DEFAULT_STORE = {
    "coins": 300,
    "players": [
        {"name": "P1", "color": [200, 40, 40], "head": 10, "thickness": 3, "speed": 260, "kick": 700},
        {"name": "P2", "color": [50,100,220], "head": 10, "thickness": 3, "speed": 260, "kick": 700},
        {"name": "P3", "color": [200,200,60], "head": 10, "thickness": 3, "speed": 260, "kick": 700},
        {"name": "P4", "color": [160,80,200], "head": 10, "thickness": 3, "speed": 260, "kick": 700}
    ],
    "unlocked_colors": [[200,40,40],[50,100,220],[200,200,60],[160,80,200]],
}
def load_cfg():
    if os.path.exists(CFG_FILE):
        try:
            with open(CFG_FILE,"r") as f: return json.load(f)
        except: pass
    return DEFAULT_STORE.copy()
def save_cfg(cfg):
    with open(CFG_FILE,"w") as f: json.dump(cfg,f,indent=2)

cfg = load_cfg()

# -----------------------
# Pygame init + globals
# -----------------------
pygame.init()
WIDTH, HEIGHT = 1200, 700
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Football — Local Multiplayer, Shop & Customize")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("Consolas", 18)
BIG = pygame.font.SysFont("Consolas", 28)

# Field config
PITCH_MARGIN = 60
GOAL_WIDTH = 200
GOAL_DEPTH = 20

# Controls per player (up to 4)
INPUT_SETS = [
    {'up':pygame.K_w,'down':pygame.K_s,'left':pygame.K_a,'right':pygame.K_d,'kick':pygame.K_LSHIFT},
    {'up':pygame.K_UP,'down':pygame.K_DOWN,'left':pygame.K_LEFT,'right':pygame.K_RIGHT,'kick':pygame.K_RSHIFT},
    {'up':pygame.K_i,'down':pygame.K_k,'left':pygame.K_j,'right':pygame.K_l,'kick':pygame.K_RCTRL},
    {'up':pygame.K_t,'down':pygame.K_g,'left':pygame.K_f,'right':pygame.K_h,'kick':pygame.K_LCTRL},
]

# -----------------------
# UI Widgets (simple)
# -----------------------
class Button:
    def __init__(self, rect, txt):
        self.rect = pygame.Rect(rect)
        self.txt = txt
    def draw(self, surf, color=(40,40,40), textc=(240,240,240)):
        pygame.draw.rect(surf, color, self.rect)
        pygame.draw.rect(surf, (200,200,200), self.rect, 2)
        surf.blit(FONT.render(self.txt, True, textc), (self.rect.x+8, self.rect.y+6))
    def is_clicked(self, pos): return self.rect.collidepoint(pos)

class Toggle:
    def __init__(self, rect, state=False, on_txt="ON", off_txt="OFF"):
        self.rect=pygame.Rect(rect); self.state=state; self.on_txt=on_txt; self.off_txt=off_txt
    def draw(self,surf):
        c = (34,180,100) if self.state else (150,50,50)
        pygame.draw.rect(surf,c,self.rect)
        txt = self.on_txt if self.state else self.off_txt
        surf.blit(FONT.render(txt, True, (10,10,10)), (self.rect.x+6,self.rect.y+6))
    def click(self,pos):
        if self.rect.collidepoint(pos): self.state = not self.state; return True
        return False

# -----------------------
# Game objects & logic
# -----------------------
def draw_pitch(s):
    GREEN=(12,150,45); LINE=(255,255,255)
    s.fill(GREEN)
    pygame.draw.rect(s, LINE, (PITCH_MARGIN,PITCH_MARGIN,WIDTH-2*PITCH_MARGIN,HEIGHT-2*PITCH_MARGIN), 6)
    pygame.draw.line(s, LINE, (WIDTH/2,PITCH_MARGIN),(WIDTH/2,HEIGHT-PITCH_MARGIN),4)
    pygame.draw.circle(s, LINE, (int(WIDTH/2),int(HEIGHT/2)), 90, 3)
    top=HEIGHT/2 - GOAL_WIDTH/2; bottom=HEIGHT/2 + GOAL_WIDTH/2
    pygame.draw.rect(s, (180,180,180), (PITCH_MARGIN-GOAL_DEPTH, top, GOAL_DEPTH, GOAL_WIDTH))
    pygame.draw.rect(s, (180,180,180), (WIDTH-PITCH_MARGIN, top, GOAL_DEPTH, GOAL_WIDTH))
    pygame.draw.circle(s, LINE, (int(WIDTH/2),int(HEIGHT/2)), 4)

class Ball:
    def __init__(self):
        self.pos = Vector2(WIDTH/2, HEIGHT/2)
        self.vel = Vector2(0,0)
        self.radius = 12
        self.friction = 0.995
        self.max_speed = 1200
    def update(self,dt):
        self.pos += self.vel * dt
        self.vel *= self.friction**(dt*FPS)
        if self.vel.length() > self.max_speed: self.vel.scale_to_length(self.max_speed)
        left, right, top, bottom = PITCH_MARGIN, WIDTH-PITCH_MARGIN, PITCH_MARGIN, HEIGHT-PITCH_MARGIN
        if self.pos.y - self.radius < top: self.pos.y = top + self.radius; self.vel.y *= -0.6
        if self.pos.y + self.radius > bottom: self.pos.y = bottom - self.radius; self.vel.y *= -0.6
        # no left/right bounce since goals
        if self.vel.length() < 6: self.vel = Vector2(0,0)
    def draw(self,s): pygame.draw.circle(s, (245,245,100), (int(self.pos.x),int(self.pos.y)), self.radius)

class Player:
    def __init__(self, idx, human=True, cfg_data=None):
        self.idx = idx
        self.human = human
        self.pos = Vector2(WIDTH*(0.2+0.2*idx), HEIGHT/2 + (idx%2)*60 - 30)
        self.vel = Vector2(0,0)
        self.radius = 18
        self.base_speed = cfg_data['speed'] if cfg_data else 260
        self.kick_power = cfg_data['kick'] if cfg_data else 700
        self.charge = 0.0
        self.k_charging = False
        self.cfg = cfg_data
        self.name = cfg_data['name'] if cfg_data else f"P{idx+1}"
        self.color = tuple(cfg_data['color']) if cfg_data else (200,40,40)
        self.head = cfg_data['head'] if cfg_data else 10
        self.thickness = cfg_data['thickness'] if cfg_data else 3
        self.score = 0
    def handle_input(self, pressed, dt):
        if not self.human: return
        keys = INPUT_SETS[self.idx]
        move = Vector2(0,0)
        if pressed[keys['left']]: move.x -= 1
        if pressed[keys['right']]: move.x += 1
        if pressed[keys['up']]: move.y -= 1
        if pressed[keys['down']]: move.y += 1
        if move.length_squared() > 0:
            move = move.normalize()
            self.vel += move * (self.base_speed*3.5) * dt
            if self.vel.length() > self.base_speed: self.vel.scale_to_length(self.base_speed)
        else:
            self.vel -= self.vel * min(1.0, 8.0*dt)
    def start_charge(self): self.k_charging = True; self.charge = 0.0
    def release_kick(self, ball):
        self.k_charging = False
        power = min(1.0, self.charge)
        to_ball = ball.pos - self.pos
        dist = to_ball.length()
        if dist <= self.radius + ball.radius + 8:
            dirn = to_ball.normalize() if dist>0 else Vector2(1,0)
            impulse = self.kick_power * (0.5 + power*1.5)
            ball.vel = dirn * impulse + self.vel*0.5
            return True
        return False
    def update(self, dt):
        if self.k_charging: self.charge = min(1.0, self.charge + dt*0.9)
        self.pos += self.vel * dt
        left, right, top, bottom = PITCH_MARGIN, WIDTH-PITCH_MARGIN, PITCH_MARGIN, HEIGHT-PITCH_MARGIN
        self.pos.x = max(left + self.radius, min(right - self.radius, self.pos.x))
        self.pos.y = max(top + self.radius, min(bottom - self.radius, self.pos.y))
    def draw(self, s):
        # simple stickman: head + body + limbs
        cx, cy = int(self.pos.x), int(self.pos.y)
        head_y = cy - 18
        pygame.draw.circle(s, self.color, (cx, head_y), self.head)
        # body
        body_top = head_y + self.head
        body_bot = body_top + 18
        pygame.draw.line(s, self.color, (cx, body_top), (cx, body_bot), self.thickness)
        # limbs
        pygame.draw.line(s, self.color, (cx, body_top+6), (cx-12, body_top+18), self.thickness) # left arm
        pygame.draw.line(s, self.color, (cx, body_top+6), (cx+12, body_top+18), self.thickness) # right arm
        pygame.draw.line(s, self.color, (cx, body_bot), (cx-12, body_bot+18), self.thickness)
        pygame.draw.line(s, self.color, (cx, body_bot), (cx+12, body_bot+18), self.thickness)
        # name
        s.blit(FONT.render(self.name, True, (240,240,240)), (cx - 18, cy + 28))
        # charge bar
        if self.k_charging:
            w = 36; h = 6; x = cx - w//2; y = cy - 46
            pygame.draw.rect(s, (40,40,40), (x,y,w,h)); pygame.draw.rect(s, (255,200,80), (x,y,int(w*self.charge),h))

# -----------------------
# Simple CPU behavior
# -----------------------
def cpu_behave(player, ball, dt):
    # move toward a point offset from ball (support)
    to_ball = ball.pos - player.pos
    dist = to_ball.length()
    if dist > 35:
        dirn = to_ball.normalize()
        player.vel += dirn * player.base_speed * dt * 2.0
        if player.vel.length() > player.base_speed: player.vel.scale_to_length(player.base_speed)
    else:
        # minor circling
        player.vel *= 0.9
        if dist < player.radius + ball.radius + 10:
            # try a kick
            # small random decision to shoot toward opposite goal
            goal_dir = Vector2(WIDTH - PITCH_MARGIN - player.pos.x, HEIGHT/2 - player.pos.y).normalize()
            ball.vel = goal_dir * (player.kick_power * 0.6 + player.base_speed*0.2)

# -----------------------
# Menu / Shop / Customize Screens
# -----------------------
def main_menu():
    btn_play = Button((WIDTH//2-90, 200, 180, 44), "Play")
    btn_players = Button((WIDTH//2-90, 260, 180, 44), "Players Setup")
    btn_customize = Button((WIDTH//2-90, 320, 180, 44), "Customize Players")
    btn_shop = Button((WIDTH//2-90, 380, 180, 44), "Shop")
    btn_quit = Button((WIDTH//2-90, 440, 180, 44), "Quit")
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: save_cfg(cfg); pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if btn_play.is_clicked(ev.pos): return play_loop()
                if btn_players.is_clicked(ev.pos): players_setup()
                if btn_customize.is_clicked(ev.pos): customize_screen()
                if btn_shop.is_clicked(ev.pos): shop_screen()
                if btn_quit.is_clicked(ev.pos): save_cfg(cfg); pygame.quit(); sys.exit()
        screen.fill((6,12,24))
        screen.blit(BIG.render("Football — Local Multiplayer", True, (240,240,240)), (WIDTH//2-240, 100))
        # coins
        screen.blit(FONT.render(f"Coins: {cfg.get('coins',0)}", True, (240,240,0)), (WIDTH-160, 16))
        for b in (btn_play, btn_players, btn_customize, btn_shop, btn_quit): b.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)

# Player slots setup
player_slots = [True, True, False, False]  # active
slot_is_human = [True, True, False, False] # human vs cpu
def players_setup():
    # toggles: active and human per slot
    toggles = []
    for i in range(4):
        toggles.append({'active':player_slots[i], 'human':slot_is_human[i]})
    def draw_screen():
        screen.fill((18,18,18))
        screen.blit(BIG.render("Players Setup", True, (240,240,240)), (WIDTH//2-120,34))
        screen.blit(FONT.render("Click Active to enable slot; click Human to toggle Human/CPU", True, (200,200,200)), (WIDTH//2-300,80))
        for i in range(4):
            x = 120 + i*260; y = 150
            pygame.draw.rect(screen, (40,40,40), (x,y,220,260))
            pygame.draw.rect(screen, (150,150,150), (x,y,220,260), 2)
            screen.blit(FONT.render(f"Slot {i+1}", True, (240,240,240)), (x+8,y+8))
            scr = cfg['players'][i]
            screen.blit(FONT.render(f"Name: {scr['name']}", True, (240,240,240)), (x+8,y+40))
            col = tuple(scr['color'])
            pygame.draw.rect(screen, col, (x+8,y+70,40,40))
            # active toggle
            act = Toggle((x+8,y+130,80,34), state=toggles[i]['active'], on_txt="Active", off_txt="Off")
            hum = Toggle((x+110,y+130,80,34), state=toggles[i]['human'], on_txt="Human", off_txt="CPU")
            act.draw(screen); hum.draw(screen)
            # store toggles references
            toggles[i]['_act']=act; toggles[i]['_hum']=hum
        # instruction
        screen.blit(FONT.render("Press Save to apply", True, (200,200,200)), (WIDTH//2-80,430))
        save_b = Button((WIDTH//2-90,480,180,44), "Save")
        save_b.draw(screen)
        return save_b
    save_button = None
    while True:
        save_button = draw_screen()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: save_cfg(cfg); pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                pos = ev.pos
                # find toggles clicked
                for i in range(4):
                    if toggles[i]['_act'].click(pos): toggles[i]['active']=toggles[i]['_act'].state
                    elif toggles[i]['_hum'].click(pos): toggles[i]['human']=toggles[i]['_hum'].state
                if save_button.is_clicked(pos):
                    for i in range(4):
                        player_slots[i] = toggles[i]['active']
                        slot_is_human[i] = toggles[i]['human']
                    return
        pygame.display.flip()
        clock.tick(FPS)

# Customization screen for players
COLOR_PALETTE = [(200,40,40),(50,100,220),(200,200,60),(160,80,200),(255,100,40),(40,200,80),(220,20,180)]
def customize_screen():
    sel=0
    def draw_ui():
        screen.fill((20,20,28))
        screen.blit(BIG.render("Customize Players", True, (240,240,240)), (40,18))
        screen.blit(FONT.render("Select slot, change color, head size, thickness and name", True, (200,200,200)), (40,64))
        # slot buttons
        for i in range(4):
            b = Button((40+ i*150,110,120,36), f"Slot {i+1}")
            b.draw(screen, color=(60,60,60))
            if i==sel: pygame.draw.rect(screen, (255,255,255), b.rect, 2)
        # current player preview
        p = cfg['players'][sel]
        # preview rectangle
        pygame.draw.rect(screen, (40,40,40), (420,110,340,260)); pygame.draw.rect(screen,(200,200,200),(420,110,340,260),2)
        # draw stickman preview
        temp = Player(sel, True, p)
        temp.pos = Vector2(590,220)
        temp.draw(screen)
        # color choices (unlocked)
        screen.blit(FONT.render("Colors (click):", True, (220,220,220)), (40,180))
        for i,col in enumerate(cfg.get('unlocked_colors',[])):
            pygame.draw.rect(screen, tuple(col), (40+i*46,210,36,36)); pygame.draw.rect(screen,(255,255,255),(40+i*46,210,36,36),2)
        # sliders for head & thickness
        screen.blit(FONT.render("Head size (5..20):", True, (220,220,220)),(40,280))
        head_surf = FONT.render(str(p['head']), True, (240,240,240))
        screen.blit(head_surf, (220,280))
        screen.blit(FONT.render("Thickness (1..6):", True, (220,220,220)),(40,320))
        th_surf = FONT.render(str(p['thickness']), True, (240,240,240))
        screen.blit(th_surf, (220,320))
        # name field
        screen.blit(FONT.render("Name: ", True, (220,220,220)), (40,360))
        screen.blit(FONT.render(p['name'], True, (240,240,240)), (120,360))
        # Save / Back
        Button((40,420,120,40),"Apply").draw(screen)
        Button((180,420,120,40),"Back").draw(screen)
    name_editing = False
    while True:
        draw_ui()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: save_cfg(cfg); pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                x,y = ev.pos
                # slot selects
                for i in range(4):
                    if pygame.Rect(40+i*150,110,120,36).collidepoint(ev.pos): sel = i
                # color clicks
                for i,col in enumerate(cfg.get('unlocked_colors',[])):
                    if pygame.Rect(40+i*46,210,36,36).collidepoint(ev.pos):
                        cfg['players'][sel]['color'] = list(col)
                # apply/back
                if pygame.Rect(40,420,120,40).collidepoint(ev.pos):
                    save_cfg(cfg); return
                if pygame.Rect(180,420,120,40).collidepoint(ev.pos):
                    return
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_UP:
                    cfg['players'][sel]['head'] = min(20, cfg['players'][sel]['head']+1)
                if ev.key == pygame.K_DOWN:
                    cfg['players'][sel]['head'] = max(5, cfg['players'][sel]['head']-1)
                if ev.key == pygame.K_RIGHT:
                    cfg['players'][sel]['thickness'] = min(6, cfg['players'][sel]['thickness']+1)
                if ev.key == pygame.K_LEFT:
                    cfg['players'][sel]['thickness'] = max(1, cfg['players'][sel]['thickness']-1)
                # name editing letters/backspace
                if ev.key == pygame.K_BACKSPACE:
                    cfg['players'][sel]['name'] = cfg['players'][sel]['name'][:-1]
                elif ev.unicode and len(ev.unicode)==1 and len(cfg['players'][sel]['name'])<10:
                    cfg['players'][sel]['name'] += ev.unicode
        pygame.display.flip()
        clock.tick(FPS)

# Shop screen
SHOP_ITEMS = [
    {"id":"speed","name":"Speed +10","cost":120,"apply": lambda p: p.update({"speed": p['speed']+10})},
    {"id":"kick","name":"Kick +80","cost":160,"apply": lambda p: p.update({"kick": p['kick']+80})},
    {"id":"color_unl","name":"Unlock Color","cost":200,"apply": None},
]
def shop_screen():
    sel = 0
    while True:
        screen.fill((12,12,20))
        screen.blit(BIG.render("Shop", True, (240,240,240)), (40,34))
        screen.blit(FONT.render(f"Coins: {cfg.get('coins',0)}", True, (240,240,0)), (WIDTH-160, 16))
        screen.blit(FONT.render("Select slot then click Buy to apply upgrade to that player", True, (200,200,200)), (40,80))
        # slot buttons
        for i in range(4):
            b = Button((40+i*150,120,120,36), f"Slot {i+1}")
            b.draw(screen, color=(60,60,60))
            if i==sel: pygame.draw.rect(screen,(255,255,255),b.rect,2)
        # list items
        for idx,it in enumerate(SHOP_ITEMS):
            y = 190 + idx*70
            pygame.draw.rect(screen, (40,40,40),(420,y,520,56))
            screen.blit(FONT.render(it['name'], True, (240,240,240)), (440,y+12))
            screen.blit(FONT.render(f"Cost: {it['cost']}", True, (200,200,0)), (820,y+12))
            buyb = Button((960,y,120,36), "Buy")
            buyb.draw(screen)
            if buyb.is_clicked(pygame.mouse.get_pos()) and False: pass  # placeholder
        # Draw 'Buy' click detection loop
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: save_cfg(cfg); pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                pos = ev.pos
                # slot select
                for i in range(4):
                    if pygame.Rect(40+i*150,120,120,36).collidepoint(pos): sel = i
                for idx,it in enumerate(SHOP_ITEMS):
                    y = 190 + idx*70
                    if pygame.Rect(960,y,120,36).collidepoint(pos):
                        # buy attempt
                        if cfg.get('coins',0) < it['cost']:
                            # insufficient
                            pass
                        else:
                            cfg['coins'] -= it['cost']
                            # apply
                            if it['id']=="color_unl":
                                # add a color unlock (random choice for fun)
                                new_col = (255,100,40) if (255,100,40) not in cfg['unlocked_colors'] else (40,200,80)
                                cfg['unlocked_colors'].append(list(new_col))
                            else:
                                # apply to selected player
                                p = cfg['players'][sel]
                                if it['apply']: it['apply'](p)
                            save_cfg(cfg)
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return
        pygame.display.flip()
        clock.tick(FPS)

# -----------------------
# Gameplay / Play loop
# -----------------------
def play_loop():
    # Create players & ball according to slots
    active_indices = [i for i,x in enumerate(player_slots) if x]
    if len(active_indices) < 2:
        # require at least 2
        return
    players = []
    for i in range(4):
        if player_slots[i]:
            pdata = cfg['players'][i]
            p = Player(i, slot_is_human[i], pdata)
            players.append(p)
    ball = Ball()
    score = [0,0]  # p1 & p2 team scores; for simplicity assign first half players to left team, rest to right
    start_time = time.time()
    match_time = 120
    paused_until = None

    # map players to teams: left vs right based on starting x
    while True:
        dt = clock.tick(FPS)/1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: save_cfg(cfg); pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return
                if ev.key == pygame.K_r:
                    # restart
                    for idx,p in enumerate(players): p.pos = Vector2(WIDTH*(0.2+0.2*idx), HEIGHT/2)
                    ball.pos = Vector2(WIDTH/2, HEIGHT/2); ball.vel = Vector2(0,0)
                    continue
                # kick keys start/stop
                for p in players:
                    if p.human:
                        key = INPUT_SETS[p.idx]['kick']
                        if ev.key == key: p.start_charge()
            if ev.type == pygame.KEYUP:
                for p in players:
                    if p.human:
                        key = INPUT_SETS[p.idx]['kick']
                        if ev.key == key: p.release_kick(ball)

        pressed = pygame.key.get_pressed()
        # update players
        for p in players:
            if p.human: p.handle_input(pressed, dt)
            else: cpu_behave(p, ball, dt)
            p.update(dt)
        # collisions player-ball
        for p in players:
            diff = ball.pos - p.pos
            d = diff.length()
            minr = p.radius + ball.radius
            if d < minr and d>0:
                overlap = minr - d
                dirn = diff.normalize()
                ball.pos += dirn * overlap
                # simple momentum
                rel = ball.vel - p.vel
                ball.vel = ball.vel - 2*(rel.dot(dirn))*dirn*0.6 + p.vel*0.2
        ball.update(dt)
        # check goal
        g = check_goal(ball)
        if g:
            # assign coins & score
            if g=="P1": score[0] += 1; cfg['coins'] += 40
            else: score[1] += 1; cfg['coins'] += 40
            save_cfg(cfg)
            # reset briefly
            ball.pos=Vector2(WIDTH/2, HEIGHT/2); ball.vel=Vector2(0,0)
            for i,p in enumerate(players): p.pos = Vector2(WIDTH*(0.2+0.2*i), HEIGHT/2); p.vel=Vector2(0,0)
            paused_until = time.time()+1.2
        if paused_until and time.time() < paused_until:
            pass
        else:
            paused_until = None
        # draw
        draw_pitch(screen)
        ball.draw(screen)
        for p in players: p.draw(screen)
        # HUD: score/time/coins
        time_left = max(0, match_time - (time.time()-start_time))
        screen.blit(FONT.render(f"Score: {score[0]} - {score[1]}", True, (240,240,240)), (WIDTH//2-60, 12))
        mins = int(time_left)//60; secs = int(time_left)%60
        screen.blit(FONT.render(f"{mins:02d}:{secs:02d}", True, (240,240,240)), (WIDTH//2-40, 36))
        screen.blit(FONT.render(f"Coins: {cfg.get('coins',0)}", True, (240,240,0)), (WIDTH-160, 16))
        # match end
        if time_left <= 0:
            winner = "Draw"
            if score[0]>score[1]: winner="Left Team Wins!"
            elif score[1]>score[0]: winner="Right Team Wins!"
            screen.blit(BIG.render(f"Match Over - {winner}", True, (240,240,240)), (WIDTH//2-200, HEIGHT//2-40))
            screen.blit(FONT.render("Press R to restart or ESC to exit to menu", True, (200,200,200)), (WIDTH//2-200, HEIGHT//2+12))
        pygame.display.flip()

def check_goal(ball):
    left_goal_x = PITCH_MARGIN
    right_goal_x = WIDTH - PITCH_MARGIN
    top = HEIGHT/2 - GOAL_WIDTH/2; bottom = HEIGHT/2 + GOAL_WIDTH/2
    if ball.pos.x - ball.radius <= left_goal_x and top <= ball.pos.y <= bottom: return "P2"
    if ball.pos.x + ball.radius >= right_goal_x and top <= ball.pos.y <= bottom: return "P1"
    return None

# -----------------------
# Entry
# -----------------------
if __name__ == "__main__":
    try:
        main_menu()
    except Exception as e:
        print("Error:", e)
    finally:
        save_cfg(cfg)
        pygame.quit()
        sys.exit()
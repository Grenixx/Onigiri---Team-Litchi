import os
import sys
import math
import random
import time
import moderngl
import json

import pygame
from screeninfo import get_monitors

from scripts.utils import load_image, load_images, Animation
from scripts.entities import PhysicsEntity, Player, ClientEnemyManager, RemotePlayerRenderer
from scripts.weapon import Weapon
from scripts.tilemap import Tilemap
from scripts.clouds import Clouds
from scripts.particle import Particle
from scripts.spark import Spark

from scripts.shader_bg import ShaderBackground
from scripts.client_network import ClientNetwork
from scripts.controller import Controller  
from scripts.lighting import LightingSystem
from scripts.shader_effect import ShaderEffect



###
# TIPS POUR MOI MEME pour les bugg lier au mouvement peut etre pour etduidier le gresillement je peux retirer l offset de la camera pour voir si c est la cam 
# le prob ou ma gestion du mouve en elle meme
###

def resource_path(relative_path):
    """Permet de trouver les fichiers quand le script est compilé en exe"""
    import sys
    import os
    try:
        #PyInstaller stocke les fichiers dans _MEIPASS on a besoind d un fonc pour y acceder heheeee
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class Game:
    def __init__(self, max_fps=60, resolution : list = [0, 0], ip="127.0.0.1"):
        self.max_fps = max_fps
        pygame.init()

        self.controls=self.loadcontrols() #chargement des touches du fichier de config user_prefs.json 
        pygame.display.set_caption('ninja game')
        if resolution == [0, 0]:
            monitors = get_monitors()
            for m in monitors:
                if m.is_primary:
                    monitor = m
                    break
            resolution = [monitor.width, monitor.height]
        print(f"Initialising game with width: {resolution[0]} and height: {resolution[1]}")
        self.screen = pygame.display.set_mode(resolution)
        
        self.base_resolution = (320, 180)
        self.zoom = 1.0
        SCALE = self.base_resolution
        
        self.display = pygame.Surface(SCALE, pygame.SRCALPHA)
        self.display_2 = pygame.Surface(SCALE)

        self.clock = pygame.time.Clock()
        
        self.movement = [False, False]
        
        self.assets = {
            'decor': load_images(resource_path('data/images/tiles/decor')),
            'grass': load_images(resource_path('data/images/tiles/grass')),
            'grassSpawner': load_images(resource_path('data/images/grass')),
            'steles': load_images(resource_path('data/images/tuto/steles')),
            'large_decor': load_images(resource_path('data/images/tiles/large_decor')),
            'stone': load_images(resource_path('data/images/tiles/stone')),
            'player': load_image(resource_path('data/images/entities/player.png')),
            'background': load_image(resource_path('data/images/background.png')),
            'clouds': load_images(resource_path('data/images/clouds')),
            'enemy/idle': Animation(load_images(resource_path('data/images/entities/enemy/idle')), img_dur=6),
            'enemy/run': Animation(load_images(resource_path('data/images/entities/enemy/run')), img_dur=4),
            'player/idle': Animation(load_images(resource_path('data/images/entities/player/idle')), img_dur=6),
            'player/run': Animation(load_images(resource_path('data/images/entities/player/run')), img_dur=4),
            'player/attack_front': Animation(load_images(resource_path('data/images/entities/player/attack_front')), img_dur=20, loop=False),
            'player/attack_up': Animation(load_images(resource_path('data/images/entities/player/attack_up')), img_dur=20, loop=False),
            'player/attack_down': Animation(load_images(resource_path('data/images/entities/player/attack_down')), img_dur=20, loop=False),
            'player/jump': Animation(load_images(resource_path('data/images/entities/player/jump'))),
            'player/slide': Animation(load_images(resource_path('data/images/entities/player/slide'))),
            'player/wall_slide': Animation(load_images(resource_path('data/images/entities/player/wall_slide'))),
            'particle/leaf': Animation(load_images(resource_path('data/images/particles/leaf')), img_dur=20, loop=False),
            'particle/particle': Animation(load_images(resource_path('data/images/particles/particle')), img_dur=6, loop=False),
            'gun': load_image(resource_path('data/images/gun.png')),
            'projectile': load_image(resource_path('data/images/projectile.png')),
            'mace': Animation(load_images(resource_path('data/images/entities/weapon/mace'), True), img_dur=5, loop=False),
            'mace1': Animation(load_images(resource_path('data/images/entities/weapon/mace1'), True), img_dur=5, loop=False),
            'slashTriangle': Animation(load_images(resource_path('data/images/entities/weapon/slashTriangle'), True), img_dur=1.5, loop=False),
            'patrol/idle': Animation(load_images(resource_path('data/images/entities/enemy/patrol/idle'), True), img_dur=3, loop=True),
            'patrol/rage': Animation(load_images(resource_path('data/images/entities/enemy/patrol/rage'), True), img_dur=2, loop=True),
            'texte': load_images(resource_path('data/images/tuto/texte')),
            'walking_enemy/idle': Animation(load_images(resource_path('data/images/entities/enemy/patrol/idle'), True), img_dur=3, loop=True),
            'walking_enemy/rage': Animation(load_images(resource_path('data/images/entities/enemy/patrol/rage'), True), img_dur=2, loop=True),
        }

        if 'tuto' in self.assets and len(self.assets['tuto']) >= 4:
            self.assets['tuto'][0] = pygame.transform.scale(self.assets['tuto'][0], (30, 30))
            self.assets['tuto'][1] = pygame.transform.scale(self.assets['tuto'][1], (30, 30))
            self.assets['tuto'][2] = pygame.transform.scale(self.assets['tuto'][2], (64, 64))
            self.assets['tuto'][3] = pygame.transform.scale(self.assets['tuto'][3], (30, 30))
        elif 'tuto' in self.assets:
             print("Attention: Pas assez d'images dans 'tuto' pour appliquer le redimensionnement automatique.")

        self.sfx = {
            'jump': pygame.mixer.Sound(resource_path('data/sfx/jump.wav')),
            'dash': pygame.mixer.Sound(resource_path('data/sfx/dash.wav')),
            'hit': pygame.mixer.Sound(resource_path('data/sfx/hit.wav')),
            'shoot': pygame.mixer.Sound(resource_path('data/sfx/shoot.wav')),
            'ambience': pygame.mixer.Sound(resource_path('data/sfx/ambience.wav')),
        }

        self.MUSIC_Volume = 0  ############# Volume global #############
        self.SFX_Volume = 0  
        self.music_on = False  

        # Ajuster les volumes
        self.sfx['ambience'].set_volume(self.SFX_Volume)
        self.sfx['shoot'].set_volume(self.SFX_Volume)
        self.sfx['hit'].set_volume(self.SFX_Volume)
        self.sfx['dash'].set_volume(self.SFX_Volume)
        self.sfx['jump'].set_volume(self.SFX_Volume)

        
        self.clouds = Clouds(self.assets['clouds'], count=5)
        
        self.player = Player(self, (50, 50), (8, 15))

        self.enemies_renderer = ClientEnemyManager(self)
        self.remote_players_renderer = RemotePlayerRenderer(self)
        
        self.tilemap = Tilemap(self, tile_size=16)
        
        self.level = 0        
        self.load_level(self.level)
        
        self.screenshake = 0

        self.net = ClientNetwork(ip, 5005)
        self.net.connect()
        self.remote_players = {}
        
        self.ctx = moderngl.create_standalone_context()
        self.shader_bg = ShaderBackground(SCALE[0], SCALE[1], "data/shaders/2.9.frag", ctx=self.ctx)
        self.scream_shader = ShaderEffect(SCALE[0], SCALE[1], "data/shaders/4.0.frag", ctx=self.ctx)
        self.transition_shader = ShaderEffect(SCALE[0], SCALE[1], "data/shaders/3.9transi.frag", ctx=self.ctx)
        self.scream_active = False # Désactivé par défaut, on le déclenche sur commande

        self.controller = Controller()

        self.lighting = LightingSystem(self.display.get_size())

        self.weapon_type = 'mace' # On commence avec la masse
        self.weaponDictionary = {1: 'slashTriangle', 2: 'mace1', 3: 'mace'}
        self.currentWeaponIndex = 1

        self.font = pygame.font.SysFont("consolas", 16)
        self.debug = True

    def loadcontrols(self):
        default_keys = {"LEFT": pygame.K_q, "RIGHT": pygame.K_d, "UP": pygame.K_z, "DOWN": pygame.K_s, "JUMP": pygame.K_SPACE, "DASH": pygame.K_LSHIFT, "ATTACK": pygame.K_c, "CHANGE_WEAPON": pygame.K_v}
        try:
            path = resource_path('user_prefs.json')
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    user_keys = data.get('controls', {})
                    # On fusionne avec les défauts pour éviter les clés manquantes
                    return {k: user_keys.get(k, default_keys[k]) for k in default_keys}
            return default_keys
        except Exception as e:
            print(f"Erreur chargement contrôles: {e}")
            return default_keys


    def set_zoom(self, zoom_value):
        self.zoom = max(0.5, min(zoom_value, 2.0))
        
        new_width = int(self.base_resolution[0] / self.zoom)
        new_height = int(self.base_resolution[1] / self.zoom)
        SCALE = (new_width, new_height)
        
        self.display = pygame.Surface(SCALE, pygame.SRCALPHA)
        self.display_2 = pygame.Surface(SCALE)
        
        self.shader_bg.resize(SCALE[0], SCALE[1])
        self.scream_shader.resize(SCALE[0], SCALE[1])
        self.transition_shader.resize(SCALE[0], SCALE[1])

        self.lighting.size = SCALE

    def load_level(self, map_id):
        self.tilemap.load('data/maps/' + str(map_id) + '.json')
        
        self.leaf_spawners = []
        for tree in self.tilemap.extract([('large_decor', 2)], keep=True):
            self.leaf_spawners.append(pygame.Rect(4 + tree['pos'][0], 4 + tree['pos'][1], 23, 13))
            
        #ca les prend puis supr donc on doit rajouter TOUT les spawner pour eviter de les blit comme des decors
        for spawner in self.tilemap.extract([('spawners', i) for i in range(10)]):
            if spawner['variant'] == 0:
                self.player.pos = spawner['pos']
                self.player.air_time = 0
            
        self.projectiles = []
        self.particles = []
        self.sparks = []
        
        self.scroll = [0, 0]
        self.dead = 0
        self.hp=100
        self.invincible_frame_time = 0
        self.transition = -30

        self.invincible_frame_time = 200

        
    def run(self):
        pygame.mixer.music.load(resource_path('data/music/musicDynamiqueLoop.mp3'))
        pygame.mixer.music.set_volume(self.MUSIC_Volume)
        pygame.mixer.music.play(-1)
        
        #self.sfx['ambience'].play(-1)
        
        while True:
            dt = self.clock.tick(self.max_fps) / 1000  # dt en secondes
            
            if self.invincible_frame_time > 0:
                self.invincible_frame_time -= dt * 60

            # --- Check Server Level Change ---
            if self.net.map_change_id is not None:
                new_map_id = self.net.map_change_id
                self.net.map_change_id = None
                self.level = new_map_id
                self.load_level(self.level)
            
            # --- PLAYER UPDATE A ÉTÉ DEPLACÉ PLUS BAS POUR LA CONSOLIDATION DES INPUTS ---

            action_mapping = {
                "idle": 0, "run": 1, "jump": 2, "wall_slide": 3, "slide": 4,
                # Ajout des actions d'attaque
                "attack_front": 5,
                "attack_up": 6,
                "attack_down": 7,
            }

            action_id = action_mapping[self.player.action]
            flip_byte = 1 if self.player.flip else 0
            self.net.send_state(self.player.pos[0], self.player.pos[1], action_id, flip_byte, self.currentWeaponIndex, self.player.velocity[0], self.player.velocity[1])

            self.scroll[0] += (self.player.rect().centerx - self.display.get_width() / 2 - self.scroll[0])  #/5 # smooth cam
            self.scroll[1] += (self.player.rect().centery - self.display.get_height() / 2 - self.scroll[1]) #/5 # smooth cam
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            self.remote_players = self.net.remote_players

            self.display.fill((0, 0, 0, 0))
            self.display_2.fill((0, 0, 0))
            # --- BACKGROUND ---
            shader_surface = self.shader_bg.render(camera=(render_scroll[0] * 0.2, render_scroll[1] * -0.2))
            self.display_2.blit(shader_surface, (0, 0))
            self.clouds.render(self.display_2, offset=render_scroll)


            self.screenshake = max(0, self.screenshake - 1)

            if self.transition < 0:
                if dt < 0.2:  # Pour éviter que ca soit a 0.45 frame 1 car le dt s init a de grande valeur au lancement
                    self.transition += dt * 60 #60 c est la speed
                    if self.transition > 0:
                        self.transition = 0
            
            if self.dead :
                self.dead += dt * 60
                if self.dead >= 10:
                    self.transition = min(30, self.transition + dt * 60)
                if self.dead > 40:
                    self.load_level(self.level)
            
            for rect in self.leaf_spawners:
                if random.random() * 49999 < rect.width * rect.height:
                    pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
                    self.particles.append(Particle(self, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))
            
            # --- TILEMAP / GRASS ---
            self.tilemap.render(self.display, offset=render_scroll)
            self.tilemap.grass_manager.update_render(self.display, 1/10, offset=render_scroll,
                rot_function=lambda x, y: int(math.sin(x / 100 + pygame.time.get_ticks() / 300) * 30) / 10)

            # --- ENEMIES ---
            self.enemies_renderer.update(dt)
            self.enemies_renderer.render(self.display, offset=render_scroll, dt=dt)

            # --- PLAYER RENDER ---
            if not self.dead:
                show_p=True
                if self.invincible_frame_time > 0:
                    if (pygame.time.get_ticks() // 100) % 2 == 0:
                        show_p = False
                if show_p:
                    self.player.render(self.display, offset=render_scroll)
                if self.debug:
                    mask_image = self.player.mask.to_surface(unsetcolor=(0,0,0,0), setcolor=(255,0,0,255))
                    self.display.blit(mask_image, (
                        (self.player.rect().x-3) - render_scroll[0], 
                        (self.player.rect().y-3) - render_scroll[1]
                    ))

            # [[x, y], direction, timer]
            #for projectile in self.projectiles.copy():
            #    projectile[0][0] += projectile[1]
            #    projectile[2] += 1
            #    img = self.assets['projectile']
            #    self.display.blit(img, (projectile[0][0] - img.get_width() / 2 - render_scroll[0], projectile[0][1] - img.get_height() / 2 - render_scroll[1]))
            #    if self.tilemap.solid_check(projectile[0]):
            #        self.projectiles.remove(projectile)
            #    for i in range(4):
            #            self.sparks.append(Spark(projectile[0], random.random() - 0.5 + (math.pi if projectile[1] > 0 else 0), 2 + random.random()))
            #    elif projectile[2] > 360:
            #        self.projectiles.remove(projectile)
            #    elif abs(self.player.dashing) < 50:
            #        if self.player.rect().collidepoint(projectile[0]):
            #            self.projectiles.remove(projectile)
            #            self.dead += dt * 60
            #            self.sfx['hit'].play()
            #            self.screenshake = max(16, self.screenshake)
            #            for i in range(30):
            #                angle = random.random() * math.pi * 2
            #                speed = random.random() * 5
            #                self.sparks.append(Spark(self.player.rect().center, angle, 2 + random.random()))
            #                self.particles.append(Particle(self, 'particle', self.player.rect().center, velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], frame=random.randint(0, 7)))
                        
            # --- REMOTE PLAYERS ---
            self.remote_players_renderer.render(self.display, offset=render_scroll, dt=dt)

            self.display_2.blit(self.display, (0, 0))

            # --- VFX (Drawing on display_2 for additive glow visibility) ---
            for spark in self.sparks.copy():
                kill = spark.update(dt) 
                spark.render(self.display_2, offset=render_scroll)
                if kill:
                    self.sparks.remove(spark)

            for particle in self.particles.copy():
                kill = particle.update()
                particle.render(self.display_2, offset=render_scroll)
                if particle.type == 'leaf':
                    particle.pos[0] += math.sin(pygame.time.get_ticks() * 0.035) * 0.3
                if kill:
                    self.particles.remove(particle)

            for event in pygame.event.get():
                # Si l'utilisateur ferme la fenêtre
                # Si l'utilisateur ferme la fenêtre
                if event.type == pygame.QUIT:
                    self.net.disconnect()
                    # On quitte la boucle de jeu pour revenir au menu
                    return
                # Si une touche est pressée
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        event.type = pygame.QUIT
                    if event.key == pygame.K_F1:
                        self.player.weapon.weapon_equiped.toggle_debug()
                        self.debug = not self.debug
                    if event.key == pygame.K_F2:
                        self.music_on = not self.music_on # Inverse l'état (True devient False et inversement)
                        
                        if self.music_on:
                            self.MUSIC_Volume = 0.5  
                            self.SFX_Volume = 0.5
                            pygame.mixer.music.set_volume(self.MUSIC_Volume)
                            self.sfx['ambience'].set_volume(self.SFX_Volume)
                            self.sfx['shoot'].set_volume(self.SFX_Volume)
                            self.sfx['hit'].set_volume(self.SFX_Volume)
                            self.sfx['dash'].set_volume(self.SFX_Volume)
                            self.sfx['jump'].set_volume(self.SFX_Volume)
                            print("Musique activée")
                        else:
                            self.MUSIC_Volume = 0  
                            self.SFX_Volume = 0
                            pygame.mixer.music.set_volume(self.MUSIC_Volume)
                            self.sfx['ambience'].set_volume(self.SFX_Volume)
                            self.sfx['shoot'].set_volume(self.SFX_Volume)
                            self.sfx['hit'].set_volume(self.SFX_Volume)
                            self.sfx['dash'].set_volume(self.SFX_Volume)
                            self.sfx['jump'].set_volume(self.SFX_Volume)
                            print("Musique coupée")
                    # Mouvement horizontal
                    if event.key == self.controls["LEFT"]:
                        self.movement[0] = True
                    if event.key == self.controls["RIGHT"]:
                        self.movement[1] = True
                    # On vérifie d'abord la touche, PUIS on tente de sauter.
                    if event.key == self.controls["JUMP"]:
                        if self.player.request_jump():
                            self.sfx['jump'].play()
                    if event.key == self.controls["DASH"]:
                        self.player.dash()
                    if event.key == self.controls["CHANGE_WEAPON"]:
                        self.currentWeaponIndex = (self.currentWeaponIndex % len(self.weaponDictionary)) + 1
                        self.weapon_type = self.weaponDictionary[self.currentWeaponIndex]
                        self.player.weapon.set_weapon(self.weapon_type)
                    if event.key == pygame.K_n:
                        self.net.send_map_change_request()
                    if event.key == pygame.K_j:
                        # Déclenche l'effet à la position du joueur
                        # On convertit les coordonnées écran en 0.0-1.0 (UV)
                        p_pos = (self.player.rect().center)
                        uv_x = (p_pos[0] - render_scroll[0]) / self.display.get_width()
                        uv_y = (p_pos[1] - render_scroll[1]) / self.display.get_height()
                        # ModernGL a Y inversé par rapport à Pygame pour les textures
                        self.scream_shader.trigger((uv_x, 1.0 - uv_y))
                        self.scream_active = True

                    # Zoom dezoom :D
                    if event.key == pygame.K_KP_PLUS or event.key == pygame.K_PLUS:
                         self.set_zoom(self.zoom + 0.1)
                    if event.key == pygame.K_KP_MINUS or event.key == pygame.K_MINUS:
                         self.set_zoom(self.zoom - 0.1)
                            
                if event.type == pygame.MOUSEWHEEL:
                    self.set_zoom(self.zoom + event.y * 0.1)

                # Si une touche est relâchée
                if event.type == pygame.KEYUP or event.type == pygame.K_SPACE:
                    if event.key == self.controls["LEFT"]:
                        self.movement[0] = False
                    if event.key == self.controls["RIGHT"]:
                        self.movement[1] = False
                    if event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_d, pygame.K_a, pygame.K_SPACE, pygame.K_s]:
                        pass 
                
                def execute_attack(self):
                    direction = None
                    keys = pygame.key.get_pressed()
                    if keys[self.controls["UP"]]: direction = 'up'
                    elif keys[self.controls["DOWN"]]: direction = 'down'
                    elif keys[self.controls["LEFT"]]: direction = 'left'
                    elif keys[self.controls["RIGHT"]]: direction = 'right'
                    self.player.attack(direction)
                # Si un bouton de la souris est pressé
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Clic gauche
                        execute_attack(self)
                if event.type == pygame.KEYDOWN:
                    if event.key == self.controls["ATTACK"]: # Touche définie pour l'attaque
                        execute_attack(self)

            # --- MISE À JOUR INPUTS MANETTE ---
            self.controller.update()

            # --- CONSOLIDATION DES MOUVEMENTS ET DIRECTIONS (Clavier + Manette) ---
            keys = pygame.key.get_pressed()
            
            # 1. Mouvements Horizontaux
            # Clavier (via events movement[0]/[1])
            kb_left = self.movement[0]
            kb_right = self.movement[1]
            
            # Manette
            ctrl_left = False
            ctrl_right = False
            if self.controller.joystick:
                if self.controller.left_stick_x < -0.4 or self.controller.dpad_left:
                    ctrl_left = True
                elif self.controller.left_stick_x > 0.4 or self.controller.dpad_right:
                    ctrl_right = True
            
            # Fusion : On bouge si l'un OU l'autre est pressé
            final_move_left = kb_left or ctrl_left
            final_move_right = kb_right or ctrl_right
            # On met temporairement les mouvements fusionnés dans movement pour que PhysicsEntity les utilise
            current_frame_movement = (final_move_right - final_move_left, 0)

            # 2. Directions (is_pressed)
            direction = None
            # Clavier
            if keys[self.controls["UP"]]: direction = 'up'
            elif keys[self.controls["DOWN"]]: direction = 'down'
            elif keys[self.controls["LEFT"]]: direction = 'left'
            elif keys[self.controls["RIGHT"]]: direction = 'right'
            
            # Manette (écrase seulement si stick actif)
            if self.controller.joystick:
                ls_x = self.controller.left_stick_x
                ls_y = self.controller.left_stick_y
                if ls_y < -0.5 or self.controller.dpad_up: direction = 'up'
                elif ls_y > 0.5 or self.controller.dpad_down: direction = 'down'
                elif ls_x < -0.5 or self.controller.dpad_left: direction = 'left'
                elif ls_x > 0.5 or self.controller.dpad_right: direction = 'right'
            
            self.player.is_pressed = direction

            # --- PLAYER UPDATE (Après consolidation) ---
            if not self.dead:
                self.player.update(self.tilemap, (final_move_right - final_move_left, 0), dt=dt)

            # --- ACTIONS MANETTE (Actions uniques / Latch) ---
            if self.controller.joystick:
                # Saut
                if self.controller.button_a and not getattr(self, '_ctrl_jump_pressed', False):
                    self._ctrl_jump_pressed = True
                    if self.player.request_jump():
                        self.sfx['jump'].play()
                elif not self.controller.button_a:
                    self._ctrl_jump_pressed = False
                
                # Dash
                dash_input = self.controller.button_b or self.controller.left_trigger > 0.3 or self.controller.right_trigger > 0.3
                if dash_input and not getattr(self, '_ctrl_dash_pressed', False):
                    self._ctrl_dash_pressed = True
                    self.player.dash()
                elif not dash_input:
                    self._ctrl_dash_pressed = False

                # Attaque
                if self.controller.button_x and not getattr(self, '_ctrl_attack_pressed', False):
                    self._ctrl_attack_pressed = True
                    self.player.attack(direction) # Utilise la direction fusionnée
                elif not self.controller.button_x:
                    self._ctrl_attack_pressed = False

                # Arme
                if (self.controller.button_y or self.controller.button_rb) and not getattr(self, '_ctrl_weapon_pressed', False):
                    self._ctrl_weapon_pressed = True
                    self.currentWeaponIndex = (self.currentWeaponIndex % len(self.weaponDictionary)) + 1
                    self.weapon_type = self.weaponDictionary[self.currentWeaponIndex]
                    self.player.weapon.set_weapon(self.weapon_type)
                elif not (self.controller.button_y or self.controller.button_rb):
                    self._ctrl_weapon_pressed = False

                # Start / Back
                if self.controller.button_start and not getattr(self, '_ctrl_start_pressed', False):
                    self._ctrl_start_pressed = True
                    self.net.send_map_change_request()
                elif not self.controller.button_start:
                    self._ctrl_start_pressed = False

                if self.controller.button_back and not getattr(self, '_ctrl_back_pressed', False):
                    self._ctrl_back_pressed = True
                    self.player.weapon.weapon_equiped.toggle_debug()
                    self.debug = not self.debug
                elif not self.controller.button_back:
                    self._ctrl_back_pressed = False

            if self.transition != 0:
                # Calcul du progrès (0.0 fermé, 1.0 ouvert)
                progress = (30 - abs(self.transition)) / 30.0
                
                # Mise à jour des uniformes
                self.transition_shader.prog["u_progress"] = progress
                if "u_camera" in self.transition_shader.prog:
                    # On envoie la position PIXEL EXACTE (juste inversée en Y pour OpenGL)
                    # Le shader se chargera d'appliquer le facteur 0.5 pour le parallax
                    self.transition_shader.prog["u_camera"] = (render_scroll[0], -render_scroll[1])
                
                # Application du shader de transition sur display_2
                trans_surf = self.transition_shader.render(self.display_2)
                self.display_2.blit(trans_surf, (0, 0))

            
            #self.tilemap.grass_manager.update_render(self.display,1/60, offset=self.scroll)
            #gd.grass_manager.update_render(display, 1 / 60, offset=gd.scroll.copy(), rot_function=lambda x, y: int(math.sin(x / 100 + global_time / 40) * 30) / 10)
            self.tilemap.grass_manager.update_render(self.display, 1/10, offset=render_scroll, rot_function=lambda x, y: int(math.sin(x / 100 + pygame.time.get_ticks() / 300) * 30) / 10)

            """
            # --- APPLICATION DE L’ÉCLAIRAGE APRÈS TOUT ---
            light_sources = [
                (self.player.rect().centerx - render_scroll[0],
                self.player.rect().centery - render_scroll[1],
                300, (220, 240, 255))
            ]
            self.lighting.render(self.display_2, light_sources, pygame.time.get_ticks())
            """
            # --- POST-PROCESSING ---
            if self.scream_active:
                scream_surf = self.scream_shader.render(self.display_2)
                self.display_2.blit(scream_surf, (0, 0))
                
                # On désactive l'effet après 1 seconde (durée fixée dans le shader) pour économiser des ressources si non utilisé
                if time.time() - self.scream_shader.start_time - self.scream_shader.trigger_time > 1.2:
                    self.scream_active = False

            # --- AFFICHAGE FINAL ---
            screenshake_offset = (
                random.random() * self.screenshake - self.screenshake / 2,
                random.random() * self.screenshake - self.screenshake / 2
            )
            self.screen.blit(
                pygame.transform.scale(self.display_2, self.screen.get_size()),
                screenshake_offset
            )

            # --- AFFICHAGE DES FPS ---
            if self.debug:
                fps = int(self.clock.get_fps())
                fps_color = (0, 255, 0) if fps >= 55 else (255, 255, 0) if fps >= 30 else (255, 0, 0)
                fps_text = self.font.render(f"FPS: {fps}", True, fps_color)
                self.screen.blit(fps_text, (10, 10))

                ping = int(self.net.ping)
                ping_color = (0, 255, 0) if ping < 80 else (255, 255, 0) if ping < 150 else (255, 0, 0)
                ping_text = self.font.render(f"Ping: {ping} ms", True, ping_color)
                self.screen.blit(ping_text, (10, 30))


            pygame.display.update()

if __name__ == "__main__":
    Game().run()

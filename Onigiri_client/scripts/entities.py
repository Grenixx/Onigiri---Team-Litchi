import pygame
import math
import random
from scripts.particle import Particle
from scripts.spark import Spark
from scripts.weapon import Weapon
from scripts.grass import GrassManager

def draw_cooldown_clock(surf, center, radius, progress, color, bg_color):
        if progress <= 0:
            return
        pygame.draw.circle(surf, bg_color, center, radius, 2)
        points = [center]
        start = -math.pi / 2
        end = start + 2 * math.pi * progress
        for i in range(33):
            a = start + (end - start) * i / 32
            points.append((center[0] + radius * math.cos(a), center[1] + radius * math.sin(a)))
        pygame.draw.polygon(surf, color, points)
class PhysicsEntity:
    def __init__(self, game, e_type, pos, size):
        self.game = game
        self.type = e_type
        self.pos = list(pos)
        self.size = size
        self.velocity = [0, 0]
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}
        
        self.action = ''
        self.anim_offset = (-3, -3)
        self.flip = False
        self.set_action('idle')
        
        self.last_movement = [0, 0]

        self.gravity = 600  # pixels/seconde²
        self.max_fall_speed = 300  # pixels/seconde
        self.run_speed = 120  # pixels/seconde

        # Remove mask usage
    def rect(self):
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])
    
    def set_action(self, action):
        if action != self.action:
            self.action = action
            self.animation = self.game.assets[self.type + '/' + self.action].copy()
        
    def update(self, tilemap, movement=(0, 0), dt=0):
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}
        
        # On applique la gravité avant le calcul du mouvement pour une détection de collision plus stable
        self.velocity[1] = min(self.max_fall_speed, self.velocity[1] + self.gravity * dt)
        
        horizontal_speed = movement[0] * self.run_speed
        
        frame_movement = (
            (horizontal_speed + self.velocity[0]) * dt,
            (movement[1] + self.velocity[1]) * dt
        )
        
        self.pos[0] += frame_movement[0] 
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_around(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[0] > 0:
                    entity_rect.right = rect.left
                    self.collisions['right'] = True
                if frame_movement[0] < 0:
                    entity_rect.left = rect.right
                    self.collisions['left'] = True
                self.pos[0] = entity_rect.x
        
        if self.collisions['right'] or self.collisions['left']:
            self.velocity[0] = 0

        self.pos[1] += frame_movement[1] 
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_around(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[1] > 0:
                    entity_rect.bottom = rect.top
                    self.collisions['down'] = True
                if frame_movement[1] < 0:
                    entity_rect.top = rect.bottom
                    self.collisions['up'] = True
                self.pos[1] = entity_rect.y

        if self.collisions['down'] or self.collisions['up']:
            self.velocity[1] = 0
        
        if movement[0] > 0:
            self.flip = False
        if movement[0] < 0:
            self.flip = True
            
        self.last_movement = movement
        
        self.animation.update(dt)

        current_img = self.animation.img()

        if self.flip:
            current_img = pygame.transform.flip(current_img, True, False)

        self.image = current_img

    def render(self, surf, offset=(0, 0), white=False):
        render_pos = (self.pos[0] - offset[0] + self.anim_offset[0],
                     self.pos[1] - offset[1] + self.anim_offset[1])
        img = pygame.transform.flip(self.animation.img(), self.flip, False)
        if white:
            white_img = pygame.mask.from_surface(img).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
            surf.blit(white_img, render_pos)
        else:
            surf.blit(img, render_pos)

        if getattr(self.game, 'debug', False):
            mask = self.animation.get_pygame_mask(self.flip)
            if mask:
                mask_surf = mask.to_surface(setcolor=(255, 0, 255, 128), unsetcolor=(0, 0, 0, 0)).convert_alpha()
                surf.blit(mask_surf, render_pos)
            else:
                rect = self.rect()
                pygame.draw.rect(surf, (0, 255, 255), (rect.x - offset[0], rect.y - offset[1], rect.width, rect.height), 1)

class Player(PhysicsEntity):
    def __init__(self, game, pos, size):
        super().__init__(game, 'player', pos, size)
        self.air_time = 0
        # 'jumps' : nombre de sauts restants (pour le double saut)
        self.jumps = True
        self.wall_slide = False
        # 'dashing' : timer pour la durée et le cooldown du dash
        self.dashing = 0
        # 'is_pressed' : stocke la dernière touche de direction pressée (utile pour les attaques directionnelles)
        self.is_pressed = None
        # Timer pour le "jump buffer". Si > 0, le joueur a demandé un saut récemment.
        self.jump_buffer_timer = 0
        # On crée une instance de l'arme et on la lie au joueur
        self.weapon = Weapon(self)

        self.jump_force = -250  # pixels/seconde (négatif = vers le haut)
        self.wall_jump_force_x = 210  # pixels/seconde
        self.wall_jump_force_y = -230  # pixels/seconde
        
        # Constantes pour la détection (en secondes, pas en frames)
        self.coyote_time = 0.15  # secondes au lieu de 9 frames
        self.jump_buffer_time = 0.2  # secondes au lieu de 12 frames
        self.wall_slide_speed = 30  # pixels/seconde maximum en glissade

        self.air_resistance = 600  # pixels/seconde²
        self.dash_duration = 0.15  # secondes (Très court)
        self.dash_speed = 330      # Ajusté
        self.dash_cooldown = 0.4   # secondes
        self.dash_invisible_duration = 0.1 
        self.dash_invisible_duration = 0.1 
        self.dash_dir = [0, 0] # Vecteur de direction du dash
        self.dash_cooldown_timer = 0 # Cooldown entre deux dashs
        self.input_axis = [0, 0] # Stockage de l'input [x, y] de game.py
        self.can_dash = True # Celeste-style: un seul dash en l'air, refresh au sol


    def update(self, tilemap, movement=(0, 0), dt=0):
        # Mise à jour des timers de cooldown/buffer
        if self.game.KO_time > 0:
            if self.action != 'idle_KO':
                self.set_action('idle_KO')
        
        self.dash_cooldown_timer = max(0, self.dash_cooldown_timer - dt)
        self.jump_buffer_timer = max(0, self.jump_buffer_timer - dt)
        self.weapon.weapon_equiped.update(dt)

        # Calcul de la vélocité du dash AVANT l'update physique pour éviter la latence d'une frame
        was_dashing = self.dashing != 0
        if self.dashing > 0:
            self.dashing = max(0, self.dashing - dt)
        if self.dashing < 0:
            self.dashing = min(0, self.dashing + dt)
            
        if self.dashing != 0:
            self.velocity[0] = self.dash_dir[0] * self.dash_speed
            self.velocity[1] = self.dash_dir[1] * self.dash_speed
            
        
        # Transition fin de dash (Momentum kill)
        if was_dashing and self.dashing == 0:
            if self.dash_dir[1] < 0: # Dash vers le haut
                self.velocity[1] = -100 # On garde un petit élan vers le haut (Celeste feel)
            elif self.dash_dir[1] > 0: # Dash vers le bas
                self.velocity[1] = 0 # On kill le momentum vertical
            
            if self.dash_dir[0] != 0:
                self.velocity[0] = self.dash_dir[0] * 180 # On garde un peu d'élan horizontal
            
            self.dash_dir = [0, 0]
            self.dash_cooldown_timer = self.dash_cooldown

        
        # Gestion du wall slide speed AVANT l'update pour qu'il soit effectif tout de suite
        if self.wall_slide:
            self.velocity[1] = min(self.velocity[1], self.wall_slide_speed)

        # On ignore le mouvement normal si on est en train de dasher
        actual_movement = (0, 0) if self.dashing != 0 else movement
        
        # Override de la gravité si dashing
        if self.dashing != 0:
            self.velocity[1] = self.dash_dir[1] * self.dash_speed
        
        super().update(tilemap, movement=actual_movement, dt=dt) 
        
        # Post-update fix pour garder la vélocité constante pendant tout le dash (contrecarrer la gravité de PhysicsEntity)
        if self.dashing != 0:
            self.velocity[0] = self.dash_dir[0] * self.dash_speed
            self.velocity[1] = self.dash_dir[1] * self.dash_speed

        # Maintenant que PhysicsEntity a mis à jour les collisions, on traite le reste
        if self.collisions['down']:
            self.air_time = 0
            self.jumps = True
            self.can_dash = True # Refresh dash au sol
            if self.jump_buffer_timer > 0:
                self.jump()
        else:
            self.air_time += dt 

        if self.pos[1] >= self.game.void_y_threshold:
            if not self.game.dead:
                self.game.screenshake = max(16, self.game.screenshake)
            self.game.dead += dt * 60
        
        if self.collisions['right'] or self.collisions['left'] and self.air_time > 0.08:
            self.can_dash = True
            if self.dashing != 0:
                self.dashing = 0
                self.dash_dir = [0, 0]
            if self.air_time > 0.05 and not self.collisions['down']:
                self.wall_slide = True
                self.air_time = 0.08
                if self.collisions['right']:
                    self.flip = False
                else:
                    self.flip = True
                self.set_action('wall_slide')
            else:
                self.wall_slide = False
        else:
            self.wall_slide = False
        
        if not self.wall_slide and not self.action.startswith('attack') and self.game.KO_time <= 0:
            if self.air_time > 0.1:
                self.set_action('jump')
            elif actual_movement[0] != 0:
                self.set_action('run')
            else:
                self.set_action('idle')

        if self.action.startswith('attack') and self.animation.done:
            self.set_action('idle')
            
        if self.dashing != 0:
            dash_progress = abs(self.dashing) / self.dash_duration
            
            # Vitesse du dash
            if self.dash_dir == 'down':
                self.velocity[1] = self.dash_speed
                self.velocity[0] = 0
            elif self.dash_dir == 'up':
                self.velocity[1] = -self.dash_speed
                self.velocity[0] = 0
            else:
                self.velocity[0] = self.dash_speed if self.dashing > 0 else -self.dash_speed
            
            # Fin du dash : On décélère
            if dash_progress < 0.2:
                if self.dash_dir == 'down':
                    self.velocity[1] *= dash_progress * 5
                elif self.dash_dir == 'up':
                    self.velocity[1] *= dash_progress * 5
                else:
                    self.velocity[0] *= dash_progress * 5
        
        # TRANSITION FIN DE DASH (Momentum kill)
        if was_dashing and self.dashing == 0:
            if self.dash_dir == 'down':
                self.velocity[1] *= 1
            elif self.dash_dir == 'up':
                self.velocity[1] *= 1
            else:
                self.velocity[0] *= 1 # On casse l'inertie violemment
            self.dash_dir = None
            self.dash_cooldown_timer = self.dash_cooldown
                
                # Résistance de l'air (décélération horizontale)
        if self.velocity[0] > 0:
            self.velocity[0] = max(self.velocity[0] - self.air_resistance * dt, 0)
        elif self.velocity[0] < 0:
            self.velocity[0] = min(self.velocity[0] + self.air_resistance * dt, 0)
        
        
        #force_pos = self.rect().center  # (x_pixels, y_pixels)
        #self.game.tilemap.grass_manager.update_render(self.game.display,1/60, offset=self.game.scroll)
        # On veut la force au centre des pieds, pas en haut à gauche
        player_height = self.game.player.size[1]  # même taille que le joueur local
        force_pos = (self.pos[0] + self.game.player.size[0] / 2, self.pos[1] + player_height)
        self.game.tilemap.grass_manager.apply_force(force_pos, 4, 8)

    def render(self, surf, offset=(0, 0), white=False):
        super().render(surf, offset=offset, white=white)
        # Puis on dessine l'arme par-dessus pour qu'elle soit devant
        self.weapon.weapon_equiped.render(surf, offset)

        if self.game.cooldown > 0:
            cx = self.pos[0] - offset[0] + self.size[0] // 2
            cy = self.pos[1] - offset[1] - 15
            progress = self.game.cooldown / self.game.cooldown_max
            draw_cooldown_clock(surf, (cx, cy), 6, progress, (255, 200, 0), (40, 40, 40))
            
    def jump(self):
        if self.wall_slide or self.game.KO_time > 0:
            if self.flip and self.last_movement[0] < 0:
                self.velocity[0] = self.wall_jump_force_x
                self.velocity[1] = self.wall_jump_force_y
                self.air_time = 0.08
                self.jumps = False
                return True
            elif not self.flip and self.last_movement[0] > 0:
                self.velocity[0] = self.wall_jump_force_x * -1
                self.velocity[1] = self.wall_jump_force_y
                self.air_time = 0.08
                self.jumps = False
                return True
                
        # Saut normal ou "Coyote Time" : si on a un saut et qu'on est en l'air depuis peu de temps
        elif self.jumps and self.air_time < self.coyote_time:
            # # 9 frames = ~0.15s
            self.velocity[1] = self.jump_force
            self.jumps = False
            self.air_time = 0.08
            self.jump_buffer_timer = 0 # On a sauté, on annule le buffer
            return True
    
        # Si aucune des conditions de saut n'est remplie
        return False

    def dash(self):
        if self.can_dash and self.dash_cooldown_timer <= 0:
            self.can_dash = False # On consomme le dash
            self.game.sfx['dash'].play()
            self.game.invincibility_time = max(self.game.invincibility_time, self.dash_duration) # Immunité pendant la durée du dash
            
            # Burst unique d'étincelles au début
            # Direction par défaut si aucun axe n'est pressé : le regard du joueur
            dash_axis = list(self.input_axis)
            if dash_axis == [0, 0]:
                dash_axis = [-1 if self.flip else 1, 0]
            
            # Normalisation du vecteur pour les diagonales
            mag = math.sqrt(dash_axis[0]**2 + dash_axis[1]**2)
            self.dash_dir = [dash_axis[0]/mag, dash_axis[1]/mag]
            
            # Calcul des étincelles (opposé à la direction du dash)
            spark_angle = math.atan2(self.dash_dir[1], self.dash_dir[0]) + math.pi
            angle_width = 1.0
            offset_x = -5 if self.dash_dir[0] > 0 else 5
            offset_y = -5 if self.dash_dir[1] > 0 else 5
            
            for i in range(15):
                angle = spark_angle + (random.random() - 0.5) * angle_width
                spawn_pos = list(self.rect().center)
                self.game.sparks.append(Spark(spawn_pos, angle, 2 + random.random() * 1.5))

            self.dashing = self.dash_duration
    def request_jump(self):
        # Si on ne peut pas sauter immédiatement (car en l'air), on active le buffer.
        # 12 frames = 0.2s. C'est la fenêtre pendant laquelle le jeu se souviendra de l'appui.
        if not self.jump():
            self.jump_buffer_timer = self.jump_buffer_time
            return False
        return True

    def attack(self, direction):
        # On ne peut pas attaquer si on est déjà en train d'attaquer ou de dasher
        if self.game.cooldown<=0 and((not self.action.startswith('attack') or self.animation.done)and not self.wall_slide):
            attack_direction = 'front' # Direction par défaut

            # Priorité 1 : Attaque vers le haut si la touche 'haut' est pressée.
            if direction == 'up':
                attack_direction = 'up'
            elif direction == 'down':
                if self.air_time > 0.09:
                    attack_direction = 'down'
                else:
                    attack_direction = 'front'

            
            # --- CORRECTION ---
            # On met à jour l'orientation du joueur si l'attaque est latérale
            # Cela garantit que self.flip est correct même si le joueur est immobile.
            if direction == 'left': self.flip = True
            if direction == 'right': self.flip = False

            # Par défaut (aucune touche directionnelle prioritaire), on fait une attaque frontale.
            self.set_action('attack_' + attack_direction)
            # On déclenche l'animation de l'arme (qui a sa propre logique de direction, mais on lui mâche le travail)
            self.weapon.weapon_equiped.swing(attack_direction)



class ClientEnemyManager:
    """Classe gérant les ennemis client"""
    def __init__(self, game):
        self.game = game
        self.size = (18, 25) # (Largeur, Hauteur)
        self.collision_offset = (5, 0) 

        base_anim = self.game.assets.get(f'patrol/idle', self.game.assets['patrol/idle'])
        self.animation = base_anim.copy()
        self.enemy_anims = {}  # eid -> animation
        self.state = 'idle'

    def set_state_for_enemy(self, eid, etype, state):
        if eid not in self.enemy_anims or getattr(self.enemy_anims[eid], 'state', None) != state or getattr(self.enemy_anims[eid], 'etype', None) != etype:
            try:
                base_anim = self.game.assets.get(f'{etype}/{state}')
                if base_anim is None:
                    if etype == "Hand":
                        base_anim = self.game.assets.get(f'Projectile/{state}')
                    elif etype == "HandLeft":
                        base_anim = self.game.assets.get('Boss/left')
                    elif etype == "HandRight":
                        base_anim = self.game.assets.get('Boss/right')
                if base_anim is None:
                    base_anim = self.game.assets.get('patrol/idle')
                self.enemy_anims[eid] = base_anim.copy()
                self.enemy_anims[eid].state = state
                self.enemy_anims[eid].etype = etype
            except:
                print(f'------------------------------ {etype}/{state} not found ------------------------------')
                base_anim = self.game.assets.get(f'{etype}/{state}')
                if base_anim is None:
                    if etype == "Hand":
                        base_anim = self.game.assets.get(f'Projectile/{state}')
                    elif etype == "HandLeft":
                        base_anim = self.game.assets.get('Boss/left')
                    elif etype == "HandRight":
                        base_anim = self.game.assets.get('Boss/right')
                if base_anim is None:
                    base_anim = self.game.assets.get('patrol/idle')
                self.enemy_anims[eid] = base_anim.copy()
                self.enemy_anims[eid].state = state
                self.enemy_anims[eid].etype = etype

    def update(self, dt=1/60):
        """Vérifie les collisions entre joueurs/armes et les ennemis."""
        if not hasattr(self.game, 'hit_visuals'):
            self.game.hit_visuals = []
        self.game.hit_visuals = [] # Reset à chaque frame
        
        player = self.game.player
        current_weapon = player.weapon.weapon_equiped
        weapon_hitbox = current_weapon.current_rect
        is_attacking = current_weapon.attack_timer > 0
        to_damage = []

        # On nettoie les animations des ennemis disparus
        active_eids = set(self.game.net.enemies.keys())
        current_eids = set(self.enemy_anims.keys())
        for eid in current_eids - active_eids:
            del self.enemy_anims[eid]

        # On vide damaging_eid dès que le swing est terminé
        # (indépendamment de la collision résiduelle de l'arme)
        if not is_attacking:
            self.game.net.damaging_eid = []

        for eid, (ex, ey, flip, etype, state, hp) in list(self.game.net.enemies.items()):
            self.set_state_for_enemy(eid, etype, state)
            anim = self.enemy_anims[eid]
            
            # Hitbox basée sur la position serveur (Top-Left)
            if etype == "patrol":
                self.size = (18, 25)
                self.collision_offset = (5, 0)
            elif etype == "Dromp":
                self.size = (64, 64)
                self.collision_offset = (0, 0)
            elif etype == "Landmark":
                self.size = (0, 0)
                self.collision_offset = (0, 0)
            elif etype in ["Hand", "HandLeft", "HandRight"]:
                self.size = (15, 10)
                self.collision_offset = (0, 0)
            enemy_rect = pygame.Rect(ex + self.collision_offset[0], ey + self.collision_offset[1], self.size[0], self.size[1])

            # -----------------------------------------------------
            # DETECTION DE COLLISION AVEC MASQUES OU AABB
            # -----------------------------------------------------
            enemy_mask = anim.get_pygame_mask(flip)
            anim_offset = (-3, -3)
            enemy_mask_x = ex + anim_offset[0]
            enemy_mask_y = ey + anim_offset[1]
            
            player_rect = player.rect()
            
            if enemy_mask:
                # Masque plein de la taille de la hitbox du joueur comme fallback
                player_mask = pygame.Mask(player_rect.size, fill=True)
                offset_p = (int(player_rect.x - enemy_mask_x), int(player_rect.y - enemy_mask_y))
                collide_joueur = enemy_mask.overlap(player_mask, offset_p) is not None
                
                # Masque plein pour l'arme (hitbox AABB)
                w_mask = pygame.Mask(weapon_hitbox.size, fill=True)
                offset_w = (int(weapon_hitbox.x - enemy_mask_x), int(weapon_hitbox.y - enemy_mask_y))
                collide_arme = enemy_mask.overlap(w_mask, offset_w) is not None
            else:
                collide_joueur = player_rect.colliderect(enemy_rect)
                collide_arme = weapon_hitbox.colliderect(enemy_rect)

            # 2. Collision Joueur (Dégâts reçus)
            if collide_joueur:
                offset_x = enemy_rect.x - player_rect.x
                offset_y = enemy_rect.y - player_rect.y
                if not self.game.dead and self.game.invincibility_time <= 0 and player.dashing == 0:
                    self.game.screenshake = max(16, self.game.screenshake)      
                    self.game.sfx['hit'].play()
                    self.game.hp-=25
                    if self.game.hp<=0:
                        self.game.dead += dt * 60
                        self.game.net.send_clear_taunt()
                        print("Player is dead")
                    else :
                        self.game.invincibility_time = 1.0 # 1 seconde d'invincibilité après un coup
                        print(f"Player HP: {self.game.hp}")

            # 3. Collision Arme
            if collide_arme:
                if is_attacking and not (eid in self.game.net.damaging_eid):
                    hit_pos = (weapon_hitbox.x, weapon_hitbox.y)
                    
                    if current_weapon.weapon_type == "slashTriangle":
                        self.game.hitstop_timer = 2
                        self.game.screenshake = 15
                        self.game.recoil=75
                        self.game.cooldown=2
                        self.game.cooldown_max=2
                        self.game.KO_time=0
                    elif current_weapon.weapon_type == "mace1":
                        self.game.hitstop_timer = 2
                        self.game.screenshake = 24
                        self.game.recoil=175
                        self.game.cooldown=50
                        self.game.cooldown_max=50
                        self.game.KO_time=25
                        current_weapon.play_hit_animation()
                    elif current_weapon.weapon_type == "mace":
                        self.game.hitstop_timer = 2
                        self.game.screenshake = 33
                        self.game.recoil=250
                        self.game.cooldown=80
                        self.game.cooldown_max=80
                        self.game.KO_time=40
                        current_weapon.play_hit_animation()
                    current_weapon.already_hitstop = 1

                    self.game.freeze_time = 0.06 #pause pour le feeling
                    self.game.screenshake = max(8, self.game.screenshake)

                    # POGO
                    if current_weapon.attack_direction == 'down' and player.air_time > 0:
                        player.velocity[1] = -230
                        player.air_time = 0.08
                        player.can_dash = True
                        player.dashing = 0

                    # RECUL
                    elif current_weapon.attack_direction in ['front', 'left', 'right']:
                        recoil_dir = 1 if player.flip else -1
                        player.velocity[0] = recoil_dir * self.game.recoil


                    for i in range(30):
                        angle = random.random() * math.pi * 2
                        self.game.sparks.append(Spark(hit_pos, angle, 2 + random.random()))

                    to_damage.append(eid)
        # Retrait des ennemis retirer temporairement le temps que l on teste les retrait des pv 
        #for eid in to_remove:
        #    if eid in self.game.net.enemies:
        #        del self.game.net.enemies[eid]
        #    self.game.net.remove_enemy(eid)

        for eid in to_damage:
            self.game.net.damage_enemy(eid, current_weapon.damage_number)
            


    def render(self, surf, offset=(0, 0), dt=1):
        """Affiche les ennemis ronds violets à l'écran."""

        #surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False),
        #          (self.pos[0] - offset[0] + self.anim_offset[0],
        #           self.pos[1] - offset[1] + self.anim_offset[1]))
        
        active_eids = set(self.game.net.enemies.keys())
        current_eids = set(self.enemy_anims.keys())
        for eid in current_eids - active_eids:
            del self.enemy_anims[eid]

        for eid, (x, y, flip, etype, state, hp) in self.game.net.enemies.items():
            self.set_state_for_enemy(eid, etype, state)
            anim = self.enemy_anims[eid]
            
            anim.update(dt)
            imgAnim = anim.img()
            
            imgAnim = anim.img()
            
            # Alignement consistant avec le joueur (Top-left + Offset)
            anim_offset = (-3, -3)
            ex_topleft = x - offset[0] + anim_offset[0]
            ey_topleft = y - offset[1] + anim_offset[1]

            # Rendu Principal avec Flip
            surf.blit(pygame.transform.flip(imgAnim, flip, False), (ex_topleft, ey_topleft))


            bar_width = 25
            bar_height = 2
            max_hp_par_type = {"patrol": 50, "Blob": 25, "Dromp": 160, "Boss": 1500, "Hand": 1, "HandLeft": 1, "HandRight": 1}
            bar_offset_y = {"Boss": 44, "HandLeft": 68, "HandRight": 76}
            position_x_centre = ex_topleft + (imgAnim.get_width() - bar_width) // 2
            position_y = ey_topleft + bar_offset_y.get(etype, -3)
            
            # barre de couleur pour hp
            ratio = max(0.0, min(1.0, hp / max_hp_par_type.get(etype, 50)))
            largeur_remplie = int(bar_width * ratio)
            red = (max(0, min(255, int(255 * ratio))), 0, 0)

            pygame.draw.rect(surf, (0, 0, 0), (position_x_centre, position_y, bar_width, bar_height))
            if largeur_remplie > 0:
                pygame.draw.rect(surf, red, (position_x_centre, position_y, largeur_remplie, bar_height))



            self.game.tilemap.grass_manager.apply_force((x, y), 6, 12)

            if getattr(self.game, 'debug', False):
                if etype == 'patrol':
                    debug_size = (18, 25)
                    debug_offset = (5, 0)
                elif etype == 'Dromp':
                    debug_size = (64, 64)
                    debug_offset = (0, 0)
                elif etype == 'Landmark':
                    debug_size = (0, 0)
                    debug_offset = (0, 0)
                elif etype in ['Hand', 'HandLeft', 'HandRight']:
                    debug_size = (15, 10)
                    debug_offset = (0, 0)
                else:
                    debug_size = self.size
                    debug_offset = self.collision_offset
                enemy_mask = anim.get_pygame_mask(flip)
                if enemy_mask:
                    mask_surf = enemy_mask.to_surface(setcolor=(255, 0, 255, 128), unsetcolor=(0, 0, 0, 0)).convert_alpha()
                    surf.blit(mask_surf, (ex_topleft, ey_topleft))
                else:
                    debug_rect = pygame.Rect(x + debug_offset[0] - offset[0], y + debug_offset[1] - offset[1], debug_size[0], debug_size[1])
                    pygame.draw.rect(surf, (0, 255, 255), debug_rect, 1)
            
            
class RemotePlayerRenderer:
    """Affiche et anime les autres joueurs avec leur sprite."""

    class RemotePlayer:
        def __init__(self, game, pid, pos=(0,0), action='idle', flip=False, size=(8, 15), weapon_id=1):
            self.game = game
            self.pid = pid
            self.pos = list(pos)
            self.target_pos = list(pos) # Position cible pour le smoothing
            self.velocity = [0.0, 0.0]  # Vélocité reçue pour l'extrapolaton
            self.size = size
            self.flip = flip
            self.smoothing_speed = 20 # Vitesse de lissage
            self.air_time = 0 # Pour le weapon check
            self.weapon_id = weapon_id
            self.weapon_map = {1: 'slashTriangle', 2: 'mace1', 3: 'mace'}
            
            # Initialise l'arme correcte
            w_type = self.weapon_map.get(weapon_id, 'mace')
            self.weapon = Weapon(self, w_type)
            
            self.set_action(action)

        def rect(self):
            return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])

        def set_action(self, action):
            if hasattr(self, 'action') and self.action == action:
                return
            self.action = action
            base_anim = self.game.assets.get(f'player/{action}', self.game.assets['player/idle'])
            self.animation = base_anim.copy()

            if action.startswith('attack_'):
                direction = action.split('_')[1]
                # Hack pour permettre l'attaque vers le bas meme si on sait pas si il vole
                if direction == 'down':
                    self.air_time = 1.0
                else: 
                    self.air_time = 0
                self.weapon.swing(direction)
            else:
                 self.air_time = 0

        def update(self, pos, action, flip, dt=1, weapon_id=1, vx=0.0, vy=0.0):
            self.target_pos = list(pos) # On met à jour la cible
            self.flip = flip
            self.velocity = [vx, vy] # On met à jour la vélocité
            
            # Weapon Sync
            if weapon_id != self.weapon_id:
                self.weapon_id = weapon_id
                w_type = self.weapon_map.get(weapon_id, 'mace')
                self.weapon.set_weapon(w_type)

            # 1. Extrapolation (Dead Reckoning)
            # On prédit où le joueur devrait être selon sa vélocité
            self.pos[0] += self.velocity[0] * dt
            self.pos[1] += self.velocity[1] * dt

            # 2. Smoothing (LERP)
            # On lisse la différence entre notre prédiction et la réalité du serveur
            self.pos[0] += (self.target_pos[0] - self.pos[0]) * self.smoothing_speed * dt
            self.pos[1] += (self.target_pos[1] - self.pos[1]) * self.smoothing_speed * dt
            
            self.set_action(action)
            self.animation.update(dt)
            self.weapon.update(dt)

            



        def render(self, surf, offset=(0,0)):
            img = pygame.transform.flip(self.animation.img(), self.flip, False)
            render_pos = (self.pos[0] - offset[0] - 3, self.pos[1] - offset[1] - 3)
            surf.blit(img, render_pos)
            
            # Render weapon
            # On utilise weapon_equiped.render comme le joueur local
            self.weapon.weapon_equiped.render(surf, offset)
            
            if getattr(self.game, 'debug', False):
                mask = self.animation.get_pygame_mask(self.flip)
                if mask:
                    mask_surf = mask.to_surface(setcolor=(255, 0, 255, 128), unsetcolor=(0, 0, 0, 0)).convert_alpha()
                    surf.blit(mask_surf, render_pos)
                else:
                    rect = self.rect()
                    pygame.draw.rect(surf, (0, 255, 255), (rect.x - offset[0], rect.y - offset[1], rect.width, rect.height), 1)

            

    def __init__(self, game):
        self.game = game
        self.players = {}  # pid -> RemotePlayer

    def render(self, surf, offset=(0,0), dt=1):
        for pid, data in self.game.remote_players.items():
            if pid == self.game.net.id:
                continue

            x, y, action, flip, weapon_id, vx, vy = data

            #self.game.tilemap.grass_manager.apply_force((x, y), 4, 8)
            # On veut la force au centre des pieds, pas en haut à gauche
            player_height = self.game.player.size[1]  # même taille que le joueur local
            force_pos = (x + self.game.player.size[0] / 2, y + player_height)
            self.game.tilemap.grass_manager.apply_force(force_pos, 4, 8)

            if pid not in self.players:
                self.players[pid] = self.RemotePlayer(self.game, pid, (x,y), action, flip, weapon_id=weapon_id)

            self.players[pid].update((x,y), action, flip, dt, weapon_id=weapon_id, vx=vx, vy=vy)
            self.players[pid].render(surf, offset)



            

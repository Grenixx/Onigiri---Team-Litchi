import pygame
import math
import random
from scripts.particle import Particle
from scripts.spark import Spark
from scripts.weapon import Weapon
from scripts.grass import GrassManager


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

        
                
        if movement[0] > 0:
            self.flip = False
        if movement[0] < 0:
            self.flip = True
            
        self.last_movement = movement
        
        #self.velocity[1] = min(5, self.velocity[1] + 0.1)
        self.velocity[1] = min(self.max_fall_speed, self.velocity[1] + self.gravity * dt)

        if self.collisions['down'] or self.collisions['up']:
            self.velocity[1] = 0
            
        self.animation.update(dt)
        #self.pos[0] = round(self.pos[0])
        #self.pos[1] = round(self.pos[1])

        current_img = self.animation.img()

        if self.flip:
            current_img = pygame.transform.flip(current_img, True, False)

        self.image = current_img

    def render(self, surf, offset=(0, 0)):
        render_pos = (self.pos[0] - offset[0] + self.anim_offset[0],
                     self.pos[1] - offset[1] + self.anim_offset[1])
        surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False), render_pos)

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
        self.dash_dir = None # Direction du dash actuel ('down' ou None)
        self.dash_cooldown_timer = 0 # Cooldown entre deux dashs


    def update(self, tilemap, movement=(0, 0), dt=0):
        # On ignore le mouvement normal si on est en train de dasher
        # pour éviter d'additionner run_speed (120) + dash_speed (330)
        actual_movement = (0, 0) if self.dashing != 0 else movement
        
        was_dashing = self.dashing != 0
        super().update(tilemap, movement=actual_movement, dt=dt) 

        if self.collisions['down']:
            self.air_time = 0
        else:
            self.air_time += dt  # dt est en secondes

        self.dash_cooldown_timer = max(0, self.dash_cooldown_timer - dt)
        self.weapon.weapon_equiped.update(dt)
        self.jump_buffer_timer = max(0, self.jump_buffer_timer - dt)

        if self.air_time > 4 :
            if not self.game.dead:
                self.game.screenshake = max(16, self.game.screenshake)
            self.game.dead += dt * 60
        
        if self.wall_slide:
            self.air_time = 0.08
        if self.collisions['down'] :
            self.air_time = 0
            # On redonne 2 sauts au joueur quand il touche le sol.
            self.jumps = True
            # --- JUMP BUFFER CHECK ---
            # Si le buffer de saut est actif au moment où on atterrit, on saute.
            if self.jump_buffer_timer > 0:
                self.jump()
             
        self.wall_slide = False
        if (self.collisions['right'] or self.collisions['left']) and self.air_time > 0 and not self.collisions['down']:
            self.wall_slide = True
            self.velocity[1] = min(self.velocity[1], self.wall_slide_speed)
            if self.collisions['right']:
                self.flip = False
            else:
                self.flip = True
            self.set_action('wall_slide')
        
        if not self.wall_slide and not self.action.startswith('attack'):
            if self.air_time > 0.1:
                self.set_action('jump')
            elif actual_movement[0] != 0:
                self.set_action('run')
            else:
                self.set_action('idle')

        if self.action.startswith('attack') and self.animation.done:
            self.set_action('idle')
        
        if self.dashing > 0:
            self.dashing = max(0, self.dashing - dt)
        if self.dashing < 0:
            self.dashing = min(0, self.dashing + dt)
            
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
                self.velocity[1] = 0
            elif self.dash_dir == 'up':
                self.velocity[1] = 0
            else:
                self.velocity[0] *= 0.2 # On casse l'inertie violemment
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


    
    def render(self, surf, offset=(0, 0)):
        if abs(self.dashing) <= self.dash_duration - self.dash_invisible_duration:
            super().render(surf, offset=offset)
            # Puis on dessine l'arme par-dessus pour qu'elle soit devant
            self.weapon.weapon_equiped.render(surf, offset)
            
    def jump(self):
        if self.wall_slide:
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
        elif self.jumps and self.air_time < self.coyote_time: # 9 frames = ~0.15s
            self.velocity[1] = self.jump_force
            self.jumps = False
            self.air_time = 0.08
            self.jump_buffer_timer = 0 # On a sauté, on annule le buffer
            return True
    
        # Si aucune des conditions de saut n'est remplie
        return False

    def dash(self):
        if not self.dashing and self.dash_cooldown_timer <= 0:
            self.game.sfx['dash'].play()
            
            # Burst unique d'étincelles au début
            if self.is_pressed == 'down':
                # Dash vers le bas
                self.dash_dir = 'down'
                spark_angle = -math.pi / 2 # Tirer vers le HAUT
                angle_width = 1.5
                offset_y = -10
                offset_x = 0
            elif self.is_pressed == 'up':
                # Dash vers le haut
                self.dash_dir = 'up'
                spark_angle = math.pi / 2 # Tirer vers le BAS
                angle_width = 1.5
                offset_y = 10
                offset_x = 0
            else:
                # Dash horizontal
                self.dash_dir = None
                direction = -1 if self.flip else 1
                spark_angle = math.pi if direction > 0 else 0
                angle_width = 1.5
                offset_y = random.randint(-2, 2)
                offset_x = -5 if direction > 0 else 5

            for i in range(15):
                angle = spark_angle + (random.random() - 0.5) * angle_width
                spawn_pos = list(self.rect().center)
                spawn_pos[0] += offset_x
                spawn_pos[1] += offset_y
                self.game.sparks.append(Spark(spawn_pos, angle, 2 + random.random() * 1.5))

            if self.flip:
                self.dashing = -self.dash_duration
            else:
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
        if (not self.action.startswith('attack') or self.animation.done)and not self.wall_slide:
            
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
    """Classe gérant les ennemis ronds violets + collisions avec le joueur."""
    def __init__(self, game):
        self.game = game
        self.size = (18, 25) # (Largeur, Hauteur)
        self.collision_offset = (5, 0) # (X, Y)

        base_anim = self.game.assets.get(f'patrol/idle', self.game.assets['patrol/idle'])
        self.animation = base_anim.copy()
        self.enemy_anims = {}  # eid -> animation
        self.state = 'idle'

    def set_state_for_enemy(self, eid, etype, state):
        if eid not in self.enemy_anims or getattr(self.enemy_anims[eid], 'state', None) != state:
            print(f'{etype}/{state}')
            base_anim = self.game.assets.get(f'{etype}/{state}')
            self.enemy_anims[eid] = base_anim.copy()
            self.enemy_anims[eid].state = state

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

        for eid, (ex, ey, flip, etype, state) in list(self.game.net.enemies.items()):
            self.set_state_for_enemy(eid, etype, state)
            anim = self.enemy_anims[eid]
            
            # Hitbox basée sur la position serveur (Top-Left)
            if etype == "patrol":
                self.size = (18, 25)
                self.collision_offset = (5, 0)
            elif etype == "Dromp":
                self.size = (64, 64)
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
                if not self.game.dead and self.game.invincible_frame_time <= 0:
                    self.game.screenshake = max(16, self.game.screenshake)      
                    self.game.sfx['hit'].play()
                    self.game.hp-=25
                    if self.game.hp<=0:
                        self.game.dead += dt * 60
                        print("Player is dead")
                    else :
                        self.game.invincible_frame_time = 60  
                        print(f"Player HP: {self.game.hp}")

            # 3. Collision Arme
            if collide_arme:
                  if is_attacking and not (eid in self.game.net.damaging_eid):
                    hit_pos = (weapon_hitbox.x, weapon_hitbox.y)
                    for i in range(30):
                        angle = random.random() * math.pi * 2
                        self.game.sparks.append(Spark(hit_pos, angle, 2 + random.random()))
                    
                    #pas encore coder mais dcp quand il a plus de pv et que le client le sais deja go le supprimer intantanement et bien sur aussi envoyer 
                    #une requete coter serv au cas ou et puis ces deja code faut juste fare gafffe a pas ccrash si la valeur est deja retirer coter serv
                    
                    #to_remove.append(eid)
                    if not (eid in self.game.net.damaging_eid):
                        to_damage.append(eid)
                
            if not is_attacking and not collide_arme:
                self.game.net.damaging_eid = []
        # Retrait des ennemis retirer temporairement le temps que l on teste les retrait des pv 
        #for eid in to_remove:
        #    if eid in self.game.net.enemies:
        #        del self.game.net.enemies[eid]
        #    self.game.net.remove_enemy(eid)

        for eid in to_damage:
            self.game.net.damage_enemy(eid, current_weapon.damage_number)
            


    def render(self, surf, offset=(0, 0), dt=1):
        """Affiche les ennemis ronds violets à l’écran."""

        #surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False),
        #          (self.pos[0] - offset[0] + self.anim_offset[0],
        #           self.pos[1] - offset[1] + self.anim_offset[1]))
        
        active_eids = set(self.game.net.enemies.keys())
        current_eids = set(self.enemy_anims.keys())
        for eid in current_eids - active_eids:
            del self.enemy_anims[eid]

        for eid, (x, y, flip, etype, state) in self.game.net.enemies.items():
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

            self.game.tilemap.grass_manager.apply_force((x, y), 6, 12)

            if getattr(self.game, 'debug', False):
                enemy_mask = anim.get_pygame_mask(flip)
                if enemy_mask:
                    mask_surf = enemy_mask.to_surface(setcolor=(255, 0, 255, 128), unsetcolor=(0, 0, 0, 0)).convert_alpha()
                    surf.blit(mask_surf, (ex_topleft, ey_topleft))
                else:
                    debug_rect = pygame.Rect(x + self.collision_offset[0] - offset[0], y + self.collision_offset[1] - offset[1], self.size[0], self.size[1])
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



            

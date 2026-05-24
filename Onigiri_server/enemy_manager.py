import random
from math import *

from TilemapServer import PHYSICS_TILES

PLAYER_SIZE = (14, 18)

LANDMARK_TYPE_CHECK = "eid"

PRINT_DEBUG_SPAWNING_INFO = True

class EnemyManager:
    def __init__(self, tilemap):
        self.tilemap = tilemap
        self.enemies = {}
        self.next_enemy_id = 1
        self.players = []
        self.landmark_variable = 0 # can be number of landmarks or eid to reduce the amount of landmarks
        self.reset(tilemap)

    def reset(self, tilemap) -> None:
        """Resets all the enemies on the map"""
        self.tilemap = tilemap
        self.enemies.clear()
        self.next_enemy_id = 1
        self.landmark_variable = 0
        # Find spawners
        spawners = getattr(self.tilemap, 'spawners', [])
        for spawner in spawners:
            if spawner['variant'] == 1: # Enemy spawner
                self.create_enemy(spawner['pos'], "patrol")

            if spawner['variant'] == 2: # Boss spawner
                self.create_enemy(spawner['pos'], "Boss") # will be changed to spawn the boss
            
            if spawner['variant'] == 3:
                self.create_enemy(spawner['pos'], "Dromp")

    def create_enemy(self, pos: list, enemy_type: str, Landmark_eid: int = 0) -> None:
        """Creates an enemy at 'pos' with the type 'enemy_type'"""
        enemy_types = {
            "blob": Blob, "patrol": Patrol, "Dromp": Dromp, "Boss": Boss, "Projectile": Projectile,
            "Hand": Hand, "hand": Hand,
            "HandLeft": HandLeft, "HandRight": HandRight,
            "hand_left": HandLeft, "hand_right": HandRight
        }
        if enemy_type == "Landmark":
            LM = Landmark(self.next_enemy_id, pos, self, 200, LANDMARK_TYPE_CHECK, Landmark_eid)
            try:
                LM.eid
                self.enemies[self.next_enemy_id] = LM
            except:
                return
        else:
            self.enemies[self.next_enemy_id] = enemy_types[enemy_type](self.next_enemy_id, pos, self)
            if enemy_type == "patrol":
                if self.landmark_variable == 0:
                    self.landmark_variable = self.next_enemy_id
        self.next_enemy_id += 1

    def update(self, players: dict) -> None:
        """Updates all enemies based on the map and the players"""
        if not players:
            return
        self.players = players

        enemies = list_copy(self.enemies.items()) #dict can change size when running for loop
        for _, enemy in enemies:
            enemy.physics_process(0.0)

KNOCKBACK_MIN_ANGLE = pi/6
KNOCKBACK_DEPLETION = 0.5 # units / tick

class Landmark: # The hole purpose is to make testing easier by showing some positions on screen
    def __init__(self, eid: int, pos: list, enemy_manager: EnemyManager, persistance: int, checking: str, checking_value: int): #checking value can be either eid or number of Landmark max
        if checking == 'eid' and checking_value != 0 and checking_value != enemy_manager.landmark_variable:
            return
        if checking == 'number' and enemy_manager.landmark_variable > checking_value:
            for enemy_eid in sorted(enemy_manager.enemies.keys()):
                if enemy_manager.landmark_variable <= checking_value:
                    break
                enemy = enemy_manager.enemies[enemy_eid]
                if enemy.properties['type'] == "Landmark":
                    enemy.kill()

        self.eid = eid
        self.properties = {
            'x': pos[0],
            'y': pos[1],
            'vx': 0.0,
            'vy': 0.0,
            'target_player': None,
            'flip': False,
            'state': "idle",
        }
        self.enemy_manager = enemy_manager
        self.persistance = persistance
        self.properties['type'] = "Landmark"
        if PRINT_DEBUG_SPAWNING_INFO: print(f"Landmark created at {pos} with eid : {eid} !")
    
    def physics_process(self, dt: float):
        if self.persistance <= 0:
            self.kill()
        self.persistance -= 1
    
    def kill(self):
        self.enemy_manager.enemies.pop(self.eid)
        if PRINT_DEBUG_SPAWNING_INFO: print(f"Landmark deleted with eid : {self.eid} !")

class Enemy:
    def __init__(self, eid: int, pos: list, enemy_manager: EnemyManager, speed: float, hp: int, size: tuple, knockback_type: str = "any", knockback_strength: float | int = 8, hitbox_offset = (0,0)):
        self.eid = eid
        self.properties = {
            'x': pos[0],
            'y': pos[1],
            'vx': 0.0,
            'vy': 0.0,
            'target_player': None,
            'taunt_target': None,
            'flip': False,
            'state': "idle",
        }
        self.enemy_manager = enemy_manager
        self.speed = speed
        self.size = size
        self.spawn_position = pos
        self.unstuck()
        self.hp = hp
        self.knockback_velocity = [0,0]
        self.knockback_type = knockback_type
        self.knockback_strength = knockback_strength
        self.last_pos = pos
        self.last_velocity = [0,0]
        self.last_collisions = [False, False]
        self.hitbox_offset = hitbox_offset

    def can_see_player(self, player: list, max_dist : float = None) -> None:
        """Returns a boolean indicating whether the enemy can see the player"""
        pos = self.middle_pos()
        player_pos = middle_pos_player(player)

        if max_dist != None and distance_to(pos, player_pos) > max_dist:
            return False
        
        return not raycast_collide(
            pos,
            angle(vector_to(pos, player_pos)),
            self.enemy_manager.tilemap,
            distance_to(pos, player_pos) - 10,
            4,
            PHYSICS_TILES,
            False
        )

    def create_enemy(self, pos: list, enemy_type: str, Landmark_eid: int = 0) -> None:
        self.enemy_manager.create_enemy(pos, enemy_type, Landmark_eid)

    def unstuck(self): 

        """Moves the enemy if it spawns inside a wall"""
        if not self.check_collision(self.pos()):
            return

        for r in range(2, 64, 4):
            for angle_deg in range(0, 360, 45):
                rad = radians(angle_deg)
                nx = self.properties['x'] + cos(rad) * r
                ny = self.properties['y'] + sin(rad) * r
                if not self.check_collision((nx, ny)):
                    self.properties['x'] = nx
                    self.properties['y'] = ny
                    return

    def check_collision(self, pos: list) -> bool:
        """Vérifie si la hitbox de l'ennemi à la position 'pos' touche un mur."""
        x, y = pos
        w, h = self.size
        epsilon = 0.1 # Petite marge pour éviter de coller aux murs adjacents
        points = [
            (x + epsilon + 5, y + epsilon),           # Haut-Gauche
            (x + w - epsilon + 5, y + epsilon),       # Haut-Droite
            (x + epsilon + 5, y + h - epsilon),       # Bas-Gauche
            (x + w - epsilon + 5, y + h - epsilon)    # Bas-Droite
        ]
        for p in points:
            if self.enemy_manager.tilemap.solid_check(p):
                return True
        return False

    def does_collide(self,new_pos: list) -> list:
        """
        Returns whether the mob will have a collision on the next frame as an array of booleans,
        where the first element corresponds to a collision on the x-axis and the second to a collision on the y-axis.
        Example:
        [False, True]: collision on the y-axis
        """
        res = [False, False]
        if self.check_collision((new_pos[0], self.properties['y'])):
            res[0] = True
        if self.check_collision((self.properties['x'], new_pos[1])):
            res[1] = True
        return res

    def adjust_position(self, pos, new_pos, precision):
        velo = sub_vecs(new_pos, pos)
        pos_check = pos
        rep = 1
        for _ in range(precision):
            pos_check = [pos[i]/2 + new_pos[i]/2 for i in range(2)]
            collide = self.check_collision(pos_check)
            if collide:
                pos_check = add_vecs(mult_vec(pos, 1/2), mult_vec(new_pos, 1/2))
            else:
                pos = add_vecs(mult_vec(pos, 1/2), mult_vec(new_pos, 1/2))

        return pos

    def move_and_slide(self, velocity: list, delta: float) -> None:
        """
        Applies the velocity and updates the position
        (verifying collisions) 
        """
        self.properties['vx'] = velocity[0]
        self.properties['vy'] = velocity[1]
        pos = self.pos()
        new_pos = [self.properties['x'] + self.properties['vx'] + self.knockback_velocity[0], self.properties['y'] + self.properties['vy'] + self.knockback_velocity[1]]
        pos_shift = sub_vecs(pos, self.last_pos)
        collision = self.does_collide(new_pos)
        if (pos_shift[0] != 0 and collision[0] == True) or (pos_shift[1] != 0 and collision[1] == True):
            self.properties['x'], self.properties['y'] = self.adjust_position(pos, new_pos, 10)
        self.last_pos = pos
        self.last_collisions = collision
        self.last_velocity = velocity
        if collision[0]:
            self.properties['vx'] = 0
        else:
            self.properties['x'] = new_pos[0]
        if collision[1]:
            self.properties['vy'] = 0
        else:
            self.properties['y'] = new_pos[1]
        
        norm_k = norm(self.knockback_velocity)
        if norm_k != 0:
            self.knockback_velocity = mult_vec(self.knockback_velocity, max((norm_k - KNOCKBACK_DEPLETION) / norm_k, 0))
    
    def move(self, velocity: list, delta: float) -> None:
        """
        Applies the velocity and updates the position
        (without verifying collisions)
        """
        self.properties['vx'] = velocity[0]
        self.properties['vy'] = velocity[1]
        pos = self.pos()
        new_pos = [self.properties['x'] + self.properties['vx'] + self.knockback_velocity[0], self.properties['y'] + self.properties['vy'] + self.knockback_velocity[1]]
        self.last_pos = pos
        self.last_velocity = velocity
        self.properties['x'] = new_pos[0]
        self.properties['y'] = new_pos[1]
        
        norm_k = norm(self.knockback_velocity)
        if norm_k != 0:
            self.knockback_velocity = mult_vec(self.knockback_velocity, max((norm_k - KNOCKBACK_DEPLETION) / norm_k, 0))

    def damage(self, damage_amount: int, pid: int) -> None:
        self.hp -= damage_amount
        if self.hp <= 0:
            self.kill()
        knockback_velocity = sub_vecs(self.pos(), self.enemy_manager.players[pid])
        if self.knockback_type == "any":
            knockback_velocity = mult_vec(normalized(knockback_velocity), self.knockback_strength)
            self.knockback_velocity = knockback_velocity
        elif self.knockback_type == "left-right":
            if diff_angles(pi/2, angle(knockback_velocity)) > KNOCKBACK_MIN_ANGLE and diff_angles(-pi/2, angle(knockback_velocity)) > KNOCKBACK_MIN_ANGLE:
                knockback_velocity = [sign(knockback_velocity[0]) * self.knockback_strength, 0]
                self.knockback_velocity = knockback_velocity
    
    def kill(self):
        self.enemy_manager.enemies.pop(self.eid)
        if LANDMARK_TYPE_CHECK == "eid":
            if self.enemy_manager.landmark_variable == self.eid:
                if self.enemy_manager.enemies:
                    self.enemy_manager.landmark_variable = random.choice(list(self.enemy_manager.enemies.keys()))
                else:
                    self.enemy_manager.landmark_variable = 0
    
    def pos(self):
        return [self.properties['x'], self.properties['y']]

    def velo(self):
        return [self.properties['vx'], self.properties['vy']]

    def middle_pos(self):
        if self.properties['type'] == "patrol":
            return add_vecs(self.pos(), [15,15])
        if self.properties['type'] == "Dromp":
            return add_vecs(self.pos(), [32,40])
        return add_vecs(self.pos(), mult_vec(self.size, 0.5))

SPEED_BLOB = 1.5

class Blob(Enemy):
    def __init__(self, eid: int, pos: list, enemy_manager: EnemyManager):
        super().__init__(eid, pos, enemy_manager, SPEED_BLOB, 25, (15, 10)) #hp 50->25 pour etre one shoter par tous
        self.properties['type'] = "Blob"
        if PRINT_DEBUG_SPAWNING_INFO: print(f"Blob created at {pos} with eid : {eid} !")
    
    def physics_process(self, delta: float) -> None:
        """The physics engine of the enemy called every tick by EnemyManager.update()"""
        pos = self.pos()
        velocity = self.velo()
        players = self.enemy_manager.players
        tilemap = self.enemy_manager.tilemap

        # --- Gravité ---
        if not tilemap.solid_check((pos[0], pos[1] + 4)):
            velocity[1] += 0  # tombe
        else:
            velocity[1] = 0

        # --- Taunt : cible forcée ---
        taunt_pid = self.properties['taunt_target']
        if taunt_pid is not None and taunt_pid in players:
            closest_pid = taunt_pid
        else:
            # --- Trouver la cible la plus proche ---
            closest_dist = None
            closest_pid = None
            for pid in players.keys():
                dist = distance_squared_to(pos, players[pid])
                if closest_dist == None or closest_dist > dist:
                    closest_dist,closest_pid = dist,pid

        if taunt_pid is not None and taunt_pid in players:
            self.properties['target_player'] = taunt_pid
            step = [0,0]
            dist = distance_to(pos, players[taunt_pid])
            if dist > 1:
                step = normalized(vector_to(pos, players[taunt_pid]))
                step = [i * self.speed for i in step]

            # --- Test collisions map ---
            new_x = pos[0] + step[0]
            new_y = pos[1] + step[1] + velocity[1]

            if not self.check_collision((new_x, pos[1])):
                velocity[0] = step[0]
            else:
                velocity[0] = 0

            if not self.check_collision((pos[0], new_y)):
                velocity[1] += step[1]
            else:
                velocity[1] = 0

            # Limites de la map
            pos[0] = max(0, min(pos[0] + velocity[0], 1000))
            pos[1] = max(0, min(pos[1] + velocity[1], 1000))

            velocity[1] = 0

        elif distance_to(pos, players[closest_pid]) < 16*30 and self.can_see_player(players[closest_pid]):
            self.properties['target_player'] = closest_pid
            step = [0,0]
            dist = distance_to(pos, players[closest_pid])
            if dist > 1:
                step = normalized(vector_to(pos, players[closest_pid]))
                step = [i * self.speed for i in step]

            # --- Test collisions map ---
            new_x = pos[0] + step[0]
            new_y = pos[1] + step[1] + velocity[1]

            if not self.check_collision((new_x, pos[1])):
                velocity[0] = step[0]
            else:
                velocity[0] = 0

            if not self.check_collision((pos[0], new_y)):
                velocity[1] += step[1]
            else:
                velocity[1] = 0

            # Limites de la map
            pos[0] = max(0, min(pos[0] + velocity[0], 1000))
            pos[1] = max(0, min(pos[1] + velocity[1], 1000))

            velocity[1] = 0

        else:
            self.properties['target_player'] = None
            velocity = [0,0]
            
            # test
            if len(players) > 0 and random.randint(0, 500) == 0:
                pid = list(players.keys())[0]
                new_blob_pos = raycast_pos(pos, angle(vector_to(pos, players[pid])), tilemap, distance_to(pos, players[pid]) - 10, 4, PHYSICS_TILES, 10, True)
                if new_blob_pos != None:
                    self.create_enemy(new_blob_pos, "blob")
                else:
                    print("raycast_pos failed")
        self.properties['x'] = pos[0]
        self.properties['y'] = pos[1]
        self.properties['vx'] = velocity[0]
        self.properties['vy'] = velocity[1]

SPEED_PATROL = 1.5
VISION_DISTANCE_PATROL = 16*8
DIST_WANDER_PATROL = 8
MIN_WANDER_DIST_PATROL = 2
MIN_WANDER_SPEED_PATROL = 1.5
WANDER_SPEED_DECAY_PATROL = 0.01
MAX_DISTANCE_FROM_SPAWN_PATROL = 16*12
PATROL_MAX_SIGHT_PATROL = 16*8

class Patrol(Enemy):
    def __init__(self, eid: int, pos: list, enemy_manager: EnemyManager):
        super().__init__(eid, pos, enemy_manager, SPEED_PATROL, 50, (15, 10)) #hp 150->50 pour etre one shoter que par la grosse mace (mace)
        self.properties['type'] = "patrol"
        self.players_last_pos = {}
        self.wander_pos = []
        self.wander_angle = None
        self.wander_dist = None
        self.wander_speed = self.speed
        if PRINT_DEBUG_SPAWNING_INFO: print(f"Patrol created at {pos} with eid : {eid} !")
    
    def create_wander_pos(self, hit_result: list = [False, False]) -> None:
        """Creates a wandering position when the patrol doesn't see the player"""
        pos = self.pos()
        if self.wander_angle == None:
            self.wander_angle = angle(self.velo())
            #print("first", self.wander_angle)
        else:
            self.wander_angle += random.uniform(-pi/6, pi/6)
            self.wander_angle = angle_modulo(self.wander_angle)
            #print(self.wander_angle)
        
        if self.wander_dist == None:
            self.wander_dist = random.uniform(DIST_WANDER_PATROL//2, DIST_WANDER_PATROL)
        else:
            self.wander_dist = max(self.wander_dist + random.uniform(-DIST_WANDER_PATROL//4, DIST_WANDER_PATROL//4), MIN_WANDER_DIST_PATROL)
        
        #self.wander_pos = [self.properties['x'] + random.choice((-1, 1)) * dist, self.properties['y'] + random.randint(int(-dist), int(dist))]

        if hit_result[0] and not hit_result[1]: # round angle to -pi/2 or pi/2
            if self.wander_angle >= 0 and self.wander_angle <= pi:
                self.wander_angle = pi/2
            else:
                self.wander_angle = -pi/2
        elif hit_result[1] and not hit_result[0]: # round angle to 0 or pi
            if self.wander_angle >= -pi/2 and self.wander_angle <= pi/2:
                self.wander_angle = 0
            else:
                self.wander_angle = pi
        
        if hit_result == [False, False]:
            if distance_to(pos, self.spawn_position) > MAX_DISTANCE_FROM_SPAWN_PATROL:
                self.wander_angle = angle(sub_vecs(self.spawn_position, pos))
        wander_pos = add_vecs(vec_from_angle(self.wander_dist, self.wander_angle), pos)
        collide = self.check_collision(wander_pos)
        if collide:
            self.wander_angle = angle_modulo(self.wander_angle - pi)
            wander_pos = add_vecs(vec_from_angle(self.wander_dist, self.wander_angle), pos)
        #print(self.wander_pos, self.properties['x'], self.properties['y'])
        #print(f"dist : {self.wander_dist}")
        #print(f"angle : {self.wander_angle}")
        
        self.wander_pos = wander_pos
        #self.create_enemy(self.wander_pos, "Landmark", self.eid)

    def wander(self) -> list:
        pos = self.pos()
        self.properties['state'] = 'idle'
        if not self.wander_pos:
            self.create_wander_pos()
        #print(distance_to(self.wander_pos, pos))
        velocity = [0,0]
        if distance_to(self.wander_pos, pos) > 1:
            velocity = normalized(vector_to(pos, self.wander_pos))
            self.wander_speed = max(self.wander_speed - WANDER_SPEED_DECAY_PATROL, MIN_WANDER_SPEED_PATROL) # * delta
            velocity = [i * self.wander_speed for i in velocity]
            new_x = pos[0] + velocity[0] # * delta
            new_y = pos[1] + velocity[1] # * delta
            hit_result = self.does_collide([new_x, new_y])
            if hit_result != [False, False]: # encountered a wall
                #print(f"{self.eid} encountered a wall")
                self.create_wander_pos(hit_result)
                velocity = [0,0]
        else: # reached wander pos
            #print(f"{self.eid} reached wander pos")
            self.create_wander_pos()
        return velocity

    def physics_process(self, delta: float) -> None:
        """The physics engine of the enemy called every tick by EnemyManager.update()"""
        pos = self.pos()
        players = self.enemy_manager.players
        
        taunt_pid = self.properties['taunt_target']

        # --- Trouver la cible la plus proche ---
        closest_dist = None
        closest_pid = None
        if taunt_pid is not None and taunt_pid in players:
            closest_pid = taunt_pid
            closest_dist = distance_squared_to(pos, players[taunt_pid])
        else:
            for pid in players.keys():
                if pid in self.players_last_pos.keys():
                    dist = distance_squared_to(pos, self.players_last_pos[pid])
                    if closest_dist == None or closest_dist > dist:
                        closest_dist,closest_pid = dist,pid
        
        velocity = [0,0]
        if closest_pid: # if has target
            dist = sqrt(closest_dist)
            self.properties['state'] = 'rage'
            self.wander_angle = None
            self.wander_dist = None
            self.wander_pos = None
            self.wander_speed = self.speed
            self.properties['target_player'] = closest_pid
            if taunt_pid is not None and taunt_pid in players:
                velocity = normalized(vector_to(pos, players[taunt_pid]))
                velocity = [i * self.speed for i in velocity]
            elif dist > 4:
                velocity = normalized(vector_to(pos, self.players_last_pos[closest_pid]))
                velocity = [i * self.speed for i in velocity]
            elif not self.can_see_player(players[closest_pid], PATROL_MAX_SIGHT_PATROL):
                velocity = self.wander()
        else:
            velocity = self.wander()
        
        self.move_and_slide(velocity, delta)

        # --- For animations --- 

        if closest_pid:
            if sqrt(closest_dist) > 4:
                if self.properties['vx'] < 0:
                    self.properties['flip'] = True
                elif self.properties['vx'] > 0:
                    self.properties['flip'] = False
        elif self.wander_angle is not None:
            if self.properties['flip'] and self.wander_angle > -pi/3 and self.wander_angle < pi/3:
                self.properties['flip'] = False
            elif (not self.properties['flip']) and (self.wander_angle < -2*pi/3 or self.wander_angle > 2*pi/3):
                self.properties['flip'] = True

        players_last_pos = {}
        for pid in players.keys():
            if taunt_pid is not None and pid == taunt_pid:
                players_last_pos[pid] = [players[pid][0], players[pid][1]]
            elif self.can_see_player(players[pid], PATROL_MAX_SIGHT_PATROL):
                if distance_to(players[pid], pos) < VISION_DISTANCE_PATROL and distance_to(players[pid], pos) > 1:
                    players_last_pos[pid] = [players[pid][0],players[pid][1]]
            else:
                if pid in self.players_last_pos.keys():
                    if distance_to(self.players_last_pos[pid], pos) > 4:
                        players_last_pos[pid] = self.players_last_pos[pid]
        self.players_last_pos = players_last_pos

DROMP_SPEED = 1.5
DROMP_HP = 100
DROMP_VISION_DISTANCE = 16*8
DROMP_VISION_FOV = pi/3
DROMP_SPEED_MODIFIER_RAGE = 2
DROMP_GRAVITY = 5
DROMP_RAGE_COOLDOWN = 5 * 20 # seconds * ticks

class Dromp(Enemy):
    def __init__(self, eid: int, pos: list, enemy_manager: EnemyManager):
        super().__init__(eid, pos, enemy_manager, DROMP_SPEED, 160, (47,59.5), "any") #hp 100->180 pour etre two shoter par la grosse masse lente
        self.properties['type'] = "Dromp"
        self.orientation = random.choice([-1, 1])
        self.properties['flip'] = self.orientation == 1
        self.rage_cooldown_timer = -1
        self.properties['state'] = 'idle'
        if PRINT_DEBUG_SPAWNING_INFO: print(f"Dromp created at {pos} with eid : {eid} !")
        for _ in range(500):
            if self.does_collide(add_vecs(self.pos(), [0, 1]))[1]:
                break
            self.properties['y'] += 1

    def physics_process(self, delta: float) -> None:
        """The physics engine of the enemy called every tick by EnemyManager.update()"""
        pos = self.pos()
        players = self.enemy_manager.players
        
        taunt_pid = self.properties['taunt_target']
        rage = False
        if taunt_pid is not None and taunt_pid in players:
            rage = True
        else:
            for pid in players.keys():
                dist = distance_to(pos, players[pid])
                if dist <= DROMP_VISION_DISTANCE:
                    agl = diff_angles(angle(sub_vecs(players[pid], pos)), angle([self.orientation, 0]))
                    if agl <= DROMP_VISION_FOV:
                        if self.can_see_player(players[pid], DROMP_VISION_DISTANCE):
                            rage = True
                            break

        if rage:
            self.properties['state'] = 'rage'
        elif self.properties['state'] == 'rage':
            if self.rage_cooldown_timer == -1:
                self.rage_cooldown_timer = DROMP_RAGE_COOLDOWN
            elif self.rage_cooldown_timer > 0:
                self.rage_cooldown_timer -= 1
            else:
                self.properties['state'] = 'idle'
                self.rage_cooldown_timer = -1

        if self.does_collide(add_vecs(pos, [0, DROMP_GRAVITY]))[1]:
            pos_check = add_vecs([self.orientation * self.speed, 0], pos)
            if self.orientation == 1:
                add = self.size[0] * self.orientation
            else:
                add = 0
            pos_check = add_vecs(pos_check, [add, self.size[1] + 10])
            if self.last_collisions[0] or not self.enemy_manager.tilemap.solid_check(pos_check):
                self.orientation *= -1
                self.properties['flip'] = not self.properties['flip']
            velocity = [self.orientation * self.speed, DROMP_GRAVITY]
        else:
            velocity = [self.orientation * self.speed / 4, DROMP_GRAVITY]

        if self.properties['state'] == 'rage':
            if self.rage_cooldown_timer == -1:
                velocity[0] *= DROMP_SPEED_MODIFIER_RAGE
            else:
                velocity[0] *= 1 + (DROMP_SPEED_MODIFIER_RAGE - 1) * easeOutCubic(self.rage_cooldown_timer / DROMP_RAGE_COOLDOWN)

        self.move_and_slide(velocity, delta)

# ---------- Spawn Projectiles ----------

BOSS_MIN_ANGLE_PROJECTILE = pi/6 # > 0
BOSS_NUMBER_PROJECTILE_AT_ONCE = 6
BOSS_DISTANCE_PROJECTILE = 100

BOSS_ANGLE_RANGE_PROJECTILE = pi - BOSS_MIN_ANGLE_PROJECTILE * 2
BOSS_ANGLES_BETWEEN_PROJECTILE = BOSS_ANGLE_RANGE_PROJECTILE / (BOSS_NUMBER_PROJECTILE_AT_ONCE - 1) if BOSS_NUMBER_PROJECTILE_AT_ONCE != 1 else 0

BOSS_COOLDOWN_BETWEEN_PROJECTILES = 13

# ---------- Summon Patrols ----------

BOSS_MIN_ANGLE_PATROL = pi/6 # > 0
BOSS_NUMBER_PATROL_AT_ONCE = 3
BOSS_MIN_DISTANCE_PATROL = 50
BOSS_MAX_DISTANCE_PATROL = 100

BOSS_ANGLE_RANGE_PATROL = pi - BOSS_MIN_ANGLE_PATROL * 2
BOSS_ANGLES_BETWEEN_PATROL = BOSS_ANGLE_RANGE_PATROL / (BOSS_NUMBER_PATROL_AT_ONCE - 1) if BOSS_NUMBER_PATROL_AT_ONCE != 1 else 0

BOSS_COOLDOWN_BETWEEN_PATROLS = 10

# ---------- Teleportation ----------

BOSS_MAX_DIST_FROM_SPAWN = (150, 150, 20, 20) # left, right, down, up

# ---------- Double Hit ----------

BOSS_PIVOTS_DISTANCE = 0
BOSS_RADIUS_X = 200
BOSS_RADIUS_Y = 75
BOSS_SPEED = 3

# ---------- Hands ----------

BOSS_HANDS_DISTANCE_SPAWN_X = 75
BOSS_HANDS_DISTANCE_SPAWN_Y = -150

# ---------- All animations ----------

BOSS_ALL_ATTACKS = {
    'double-hit': 10, # 'double-hit': 10,
    'idle': 15, # 'idle': 15,
    'projectiles': 20, # 'projectiles': 10,
    'dromps': 10, # 'dromps': 5,
    'patrols': 15, # 'patrols': 10,
    'teleportIn': 30. # 'teleportIn': 50
}

BOSS_STATES_DURATION = {
    'double-hit': 202,
    'idle': 106,
    'death': 10,
    'projectiles': BOSS_COOLDOWN_BETWEEN_PROJECTILES * BOSS_NUMBER_PROJECTILE_AT_ONCE + 3,
    'spawn': 297,
    'dromps': 247,
    'patrols': 133,
    'teleportIn': 52,
    'teleportOut': 52,
}

BOSS_EXCLUDED_TRANSITIONS = ('death', 'spawn', 'teleportOut')

BOSS_MIDDLE_DOUBLE_ATTACK = 100
# BOSS_END_DOUBLE_ATTACK = 25

class Boss(Enemy):
    def __init__(self, eid: int, pos: list, enemy_manager: EnemyManager):
        super().__init__(eid, pos, enemy_manager, BOSS_SPEED, 1500, (200, 200), "any", 0)
        self.properties['type'] = "Boss"
        self.properties['state'] = 'spawn'
        if PRINT_DEBUG_SPAWNING_INFO: print(f"Boss created at {pos} with eid : {eid} !")

        self.animation_timer = BOSS_STATES_DURATION['spawn']
        self.angle_shoot = 0
        self.reset_angle_shoot()
        self.patrols = 0
        self.teleported = False
        self.double_hit = False
        self.angle_double_hit = pi/2
        self.animations = {k: v for k, v in BOSS_ALL_ATTACKS.items()}

    def reset_angle_shoot(self):
        self.angle_shoot = -pi + BOSS_MIN_ANGLE_PROJECTILE if BOSS_NUMBER_PROJECTILE_AT_ONCE != 1 else pi/2

    def physics_process(self, delta: float) -> None:
        """The physics engine of the enemy called every tick by EnemyManager.update()"""
        if self.animation_timer == 0:
            self.patrols = 0
            self.reset_angle_shoot()
            if self.properties['state'] == 'double-hit':
                self.double_hit = False
                self.properties['state'] = 'teleportIn'
            elif self.properties['state'] == 'teleportOut' and self.double_hit:
                self.properties['state'] = 'double-hit'
                self.angle_double_hit = pi/2
            elif self.properties['state'] == 'teleportIn':
                if self.double_hit:
                    self.properties['x'] = self.spawn_position[0] - BOSS_MAX_DIST_FROM_SPAWN[0]
                    self.properties['y'] = self.spawn_position[1] - 70
                else:
                    self.properties['x'] = random.random() * (BOSS_MAX_DIST_FROM_SPAWN[0] + BOSS_MAX_DIST_FROM_SPAWN[1]) + self.spawn_position[0] - BOSS_MAX_DIST_FROM_SPAWN[0]
                    self.properties['y'] = random.random() * (BOSS_MAX_DIST_FROM_SPAWN[2] + BOSS_MAX_DIST_FROM_SPAWN[3]) + self.spawn_position[1] - BOSS_MAX_DIST_FROM_SPAWN[3] - 42
                self.properties['state'] = 'teleportOut'
                self.teleported = True
            else:
                tmp = {k: v for k, v in self.animations.items()}
                if self.teleported:
                    self.animations['teleportIn'] = 0
                    self.animations['double-hit'] = 0
                if not self.properties['state'] in BOSS_EXCLUDED_TRANSITIONS:
                    self.animations[self.properties['state']] = 0
                self.properties['state'] = random_with_coefficients(self.animations)
                self.teleported = False
                self.animations = tmp

                if self.properties['state'] == 'double-hit':
                    self.properties['state'] = 'teleportIn'
                    self.double_hit = True

            self.animation_timer = BOSS_STATES_DURATION[self.properties['state']]
            if PRINT_DEBUG_SPAWNING_INFO: print(self.properties['state'])
        else:
            self.animation_timer -= 1
        
        if self.properties['state'] == 'projectiles':
            if self.animation_timer % BOSS_COOLDOWN_BETWEEN_PROJECTILES == 0 and self.animation_timer != 0:
                self.create_enemy(add_vecs(add_vecs(self.pos(), mult_vec(self.size, 0.425)), vec_from_angle(BOSS_DISTANCE_PROJECTILE, self.angle_shoot)), "Projectile")
                self.angle_shoot += BOSS_ANGLES_BETWEEN_PROJECTILE
        
        elif self.properties['state'] == 'patrols':
            if self.patrols < BOSS_NUMBER_PATROL_AT_ONCE and self.animation_timer % BOSS_COOLDOWN_BETWEEN_PATROLS == 0 and self.animation_timer != 0:
                self.create_enemy(add_vecs(add_vecs(add_vecs(self.pos(), [-25, 0]), mult_vec(self.size, 0.425)), vec_from_angle(random.randint(BOSS_MIN_DISTANCE_PATROL, BOSS_MAX_DISTANCE_PATROL), self.angle_shoot)), "patrol")
                self.angle_shoot += BOSS_ANGLES_BETWEEN_PATROL
                self.patrols += 1
        
        elif self.properties['state'] == 'double-hit':
            if self.animation_timer > BOSS_MIDDLE_DOUBLE_ATTACK:
                self.angle_double_hit -= 1/40
            elif self.animation_timer < BOSS_MIDDLE_DOUBLE_ATTACK:
                self.angle_double_hit += 1/40
            else:
                self.angle_double_hit += pi

            velocity = cos(self.angle_double_hit) * BOSS_RADIUS_X, sin(self.angle_double_hit) * BOSS_RADIUS_Y

            velocity = mult_vec(normalized(velocity), self.speed)

            self.move(velocity, 0)

        elif self.properties['state'] == 'dromps':
            if self.animation_timer == BOSS_STATES_DURATION['dromps']:
                self.create_enemy(add_vecs(self.middle_pos(), [BOSS_HANDS_DISTANCE_SPAWN_X, BOSS_HANDS_DISTANCE_SPAWN_Y]), "HandRight")
                self.create_enemy(add_vecs(self.middle_pos(), [-BOSS_HANDS_DISTANCE_SPAWN_X, BOSS_HANDS_DISTANCE_SPAWN_Y]), "HandLeft")
        
    def kill(self):
        self.enemy_manager.enemies.clear()

HAND_SPEED = 10
HAND_FLY_SPEED = 3           # Vitesse de vol vers le joueur (pixels/tick)
HAND_TIME_BEFORE_LAUNCH = 100 
PIXEL_AU_DESSUS_DU_PLAYER = 200

class Hand(Enemy):
    def __init__(self, eid: int, pos: list, enemy_manager: EnemyManager, size=(200, 125)):
        super().__init__(eid, pos, enemy_manager, HAND_FLY_SPEED, 1, size)
        self.properties['type'] = "Hand"
        self.properties['state'] = 'idle'
        self.velocity = [0, 0]
        self.time_before_launch = HAND_TIME_BEFORE_LAUNCH
        self.impact_timer = 0  # Ticks de pause au sol avant de disparaître
        print(f"Hand created at {pos} with eid : {eid} !")

    def unstuck(self):
        pass

    def physics_process(self, delta: float) -> None:
        """The physics engine of the enemy called every tick by EnemyManager.update()"""
        players = self.enemy_manager.players

        # --- Phase de pause au sol post-impact ---
        if self.impact_timer > 0:
            self.impact_timer -= 1
            if self.impact_timer == 0:
                self.kill()
            return

        # --- Phase de vol / hover au-dessus du joueur ---
        if self.time_before_launch > 0:
            self.properties['state'] = 'idle'

            # Trouver le joueur le plus proche
            closest_dist = None
            closest_pid = None
            for pid in players.keys():
                dist = distance_squared_to(self.pos(), players[pid])
                if closest_dist is None or closest_dist > dist:
                    closest_dist, closest_pid = dist, pid

            if closest_pid:
                player_pos = players[closest_pid]
                self.properties['target_player'] = closest_pid

                target_x = player_pos[0] + PLAYER_SIZE[0] / 2 - self.size[0] / 2
                target_y = player_pos[1] - PIXEL_AU_DESSUS_DU_PLAYER
                target_pos = [target_x, target_y]

                dist_to_target = distance_to(self.pos(), target_pos)
                if dist_to_target > 3:
                    step = mult_vec(normalized(vector_to(self.pos(), target_pos)), min(self.speed, dist_to_target))
                    self.properties['x'] += step[0]
                    self.properties['y'] += step[1]
                else:
                    self.properties['x'] = target_x
                    self.properties['y'] = target_y

            self.time_before_launch -= 1

        # --- Phase de chute ---
        else:
            self.properties['state'] = 'idle'
            
            self.last_collisions = [False, False]
            self.velocity = [0, HAND_SPEED]
            self.move_and_slide(self.velocity, delta)

            # Impact au sol ou sur un mur latéral
            if self.last_collisions[0] or self.last_collisions[1]:
                print(f"Hand {self.eid} impacted!")
                self.velocity = [0, 0]
                self.impact_timer = 15  # ~0.25s au sol avant de disparaître

class HandLeft(Hand):
    def __init__(self, eid: int, pos: list, enemy_manager: EnemyManager):
        super().__init__(eid, pos, enemy_manager, size=(200,115))
        self.properties['type'] = "HandLeft"

class HandRight(Hand):
    def __init__(self, eid: int, pos: list, enemy_manager: EnemyManager):
        super().__init__(eid, pos, enemy_manager, size=(200,125))
        self.properties['type'] = "HandRight"

PROJECTILE_MAX_DIST = 16*20
PROJECTILE_SPEED = 8
PROJECTILE_TIME_BEFORE_LAUNCH = 20

PROJECTILE_LAST_VELO_COEF = 0.975

class Projectile(Enemy):
    def __init__(self, eid: int, pos: list, enemy_manager: EnemyManager):
        super().__init__(eid, pos, enemy_manager, PROJECTILE_SPEED, 300, (16, 16), 'any', 0, (7,7))
        self.properties['type'] = "Projectile"
        self.properties['state'] = 'spawn'
        self.properties['target_player'] = None
        self.velocity = [0,0]
        self.time_before_launch = PROJECTILE_TIME_BEFORE_LAUNCH
        if PRINT_DEBUG_SPAWNING_INFO: print(f"Projectile created at {pos} with eid : {eid} !")
    
    def physics_process(self, delta: float) -> None:
        """The physics engine of the enemy called every tick by EnemyManager.update()"""
        if self.time_before_launch <= 0:
            self.properties['state'] = 'idle'
            pos = self.pos()
            players = self.enemy_manager.players

            if players == {}:
                if self.properties['target_player'] != None:
                    self.kill()
                return
            elif self.properties['target_player'] == None:
                self.properties['target_player'] = random.choice(list(players.keys()))
            
            self.velocity = mult_vec(normalized(vector_to(pos, players[self.properties['target_player']])), self.speed)

            self.velocity = add_vecs( mult_vec(self.velocity, 1 - PROJECTILE_LAST_VELO_COEF) , mult_vec(self.last_velocity, PROJECTILE_LAST_VELO_COEF))
        else:
            self.time_before_launch -=1

        self.move_and_slide(self.velocity, delta)
        
        # Col = explosion et ou juste kill
        if self.last_collisions[0] or self.last_collisions[1] or distance_to(self.pos(), self.spawn_position) > PROJECTILE_MAX_DIST:
            if PRINT_DEBUG_SPAWNING_INFO: print(f"you collided {self.eid}")
            self.kill()


def middle_pos_player(player):
    return add_vecs(player, mult_vec(PLAYER_SIZE, 0.5))

def sign(x: float | int) -> int:
    if x == 0:
        return 0
    return round(x / abs(x))

def list_copy(lst: list) -> list:
    """
    Prevents side effects in lists
    """
    return [i for i in lst]

def add_vecs(vec1: list, vec2: list) -> list:
    """
    vec1 + vec2
    """
    return [vec1[i] + vec2[i] for i in range(2)]

def sub_vecs(vec1: list, vec2: list) -> list:
    """
    vec1 - vec2
    """
    return [vec1[i] - vec2[i] for i in range(2)]

def mult_vec(vec: list, k: float) -> list:
    """
    vec1 * k
    """
    return [vec[i] * k for i in range(2)]

def vector_to(pos1: list, pos2: list) -> list:
    """
    Returns a vector from position 1 to position 2
    """
    return [pos2[0] - pos1[0], pos2[1] - pos1[1]]

def distance_squared_to(pos1: list, pos2: list) -> float:
    """
    Returns the squared distance between position 1 and position 2
    """
    vec = vector_to(pos1,pos2)
    return vec[0] ** 2 + vec[1] ** 2

def distance_to(pos1: list, pos2: list) -> float:
    """
    Returns the distance between position 1 and position 2
    """
    return sqrt(distance_squared_to(pos1,pos2))

def norm(vec: list) -> float:
    """
    Returns the norm of a vector
    """
    return distance_to([0,0],vec)

def normalized(vec: list) -> list:
    """
    Returns the normalized input vector
    """
    norm = distance_to([0,0],vec)
    if norm == 0:
        return [0, 0]
    vec = [i/norm for i in vec]
    return vec

def is_normalized(vec: list) -> bool:
    """
    Checks if the vector is normalised
    """
    return norm(vec) == 1

def vec_from_angle(norm: float, angle: float) -> list:
    """
    Returns the vector corresponding to it's norm and angle
    """
    return [cos(angle) * norm, sin(angle) * norm]

def angle(vec: list) -> float:
    """
    Returns the angle of a given vector
    (The angle of a null vector is considered 0)
    """
    n = norm(vec)
    if n == 0:
        return 0
    ax = acos(max(-1, min(1, vec[0] / n)))
    ay = asin(vec[1] / n)
    if ax == ay:
        return ax
    if ay < 0:
        if ax < pi / 2:
            return ay
        return -ax
    return ax

def angle_modulo(angle: float) -> float:
    """
    Takes an angle and returns the angle mod (2pi) in [-pi, pi]
    """
    while angle > pi:
        angle -= 2*pi
    while angle < -pi:
        angle += 2*pi
    return angle

def diff_angles(angle1: float, angle2: float) -> float:
    """
    abs(angle1 - angle2)
    """
    angle1 -= angle2
    angle1 = abs(angle_modulo(angle1))
    return angle1

def is_within(pos: list, pos1: list, pos2: list) -> bool:
    """
    Returns True if pos is between pos1 and pos2, False otherwise
    """
    pos_r1 = [pos1[i] <= pos[i] and pos2[i] >= pos[i] for i in range(2)]
    pos_r2 = [pos1[i] >= pos[i] and pos2[i] <= pos[i] for i in range(2)]
    return (pos_r1[0] and pos_r1[1]) or (pos_r2[0] and pos_r2[1])

def raycast_collide(pos: list, angle: float, tilemap, dist_max: float = 1000, dist_check: float = 4, mask: list = [], return_pos: bool = False) -> bool | list:
    """
    Creates a raycast starting from 'pos' with a given 'angle', and checks whether it hits an element of the 'tilemap' belonging to the 'mask' (if 'mask' is not empty).
    The raycast uses a maximum distance 'dist_max' and a step distance 'dist_check'.
    Returns a boolean indicating whether the raycast hit something.
    Optional parameter: 'return_pos', which returns the first (approximate) position where the raycast hits something, if any, instead of a boolean.
    """
    vec = vec_from_angle(dist_check, angle)
    dist = 0
    pos_check = pos
    while dist <= dist_max:
        check_type = tilemap.check_type((pos_check))
        if (mask == [] and check_type != None) or (check_type in mask):
            if return_pos:
                return pos_check
            return True
        pos_check = add_vecs(pos_check, vec)
        dist += dist_check
    return False

def is_round(num: float) -> bool:
    """
    Returns if a number is round
    """
    return round(num) == num

def is_almost_round(num: float, margin: float) -> list:
    """
    Returns if the number is almost round with an error margin
    """
    return floor(num) != floor(num + margin) or floor(num) != floor(num - margin)

def round_pos_if_possible(pos: list, margin: float) -> list:
    """
    Rounds the coordinates of a position if these coordinates are almost round with respect to the margin
    """
    return [round(i) if is_almost_round(i, margin) else i for i in pos]

def raycast_pos(pos: list, angle: float, tilemap, dist_max: float = 1000, dist_check: float = 4, mask: list = [], precision : int = 10, fix_collisions: bool = False) -> list | None:
    """
    Creates a raycast starting from 'pos' with a given 'angle', and checks whether it hits an element of the 'tilemap' belonging to the 'mask' (if the 'mask' is not empty).
    The raycast uses a maximum distance 'dist_max' and a step distance 'dist_check'.
    Returns the impact position of the raycast if it hits something, or 'None' otherwise.

    Optional parameters:
        'precision': sets the number of steps used to make the impact position more accurate
        'fix_collision': adjusts the returned position so it is outside the hit tile (useful for spawning a monster at the desired position)

    """
    vec = vec_from_angle(dist_check, angle)
    dist = 0
    pos_check = raycast_collide(pos, angle, tilemap, dist_max, dist_check, mask, True)
    if not pos_check:
        return None
    
    for _ in range(precision):
        vec = [i / 2 for i in vec]
        check_type = tilemap.check_type((pos_check))
        if (mask == [] and check_type != None) or (check_type in mask):
            pos_check = sub_vecs(pos_check, vec)
        else:
            pos_check = add_vecs(pos_check, vec)
    
    # Adjustments
    if precision >= 10:
        pos_check = round_pos_if_possible(pos_check, dist_check * 2**-(precision - 1))
        if fix_collisions:
            if is_round(pos_check[0]) and angle >= -pi/2 and angle <= pi/2: # collides with left side of a tile
                pos_check[0] -= 0.0000000000001
            if is_round(pos_check[1]) and angle >= 0 and angle <= pi: # collides with up side of a tile
                pos_check[1] -= 0.0000000000001

    return pos_check

# Easing functions

def easeOutCubic(t: float) -> float:
    return 1 - (1 - t)**3

def easeOutQuint(x: float) -> float:
    return 1 - (1 - x)**5

# Random functions

def random_with_coefficients(d: dict):
    r = sum(d.values())
    l = list(d.keys())
    i = 0
    r = random.randint(0, r)
    while r > 0:
        r -= d[l[i]]
        i += 1
    if l[i-1] == 'spawn':
        d.pop('spawn')
        return random_with_coefficients(d)
    return l[i-1]

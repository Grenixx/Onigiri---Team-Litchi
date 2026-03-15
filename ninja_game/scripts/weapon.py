import pygame
import math
import random

# ============================================================
# ===============   GESTIONNAIRE D'ARME    =================
# ============================================================
class Weapon:
    def __init__(self, owner, weapon_type='slashTriangle'):
        self.owner = owner
        self.weapon_type = weapon_type
        self.weapon_equiped = None  # Toujours initialisé
        self.set_weapon(weapon_type)

    def set_weapon(self, weapon_type):
        # Ici toutes les armes type “masse” utilisent WeaponBase
        if weapon_type in ['mace', 'mace1', 'slashTriangle']:
            self.weapon_equiped = WeaponBase(self.owner, weapon_type)
        else:
            # fallback si arme inconnue
            self.weapon_equiped = WeaponBase(self.owner, 'mace')

        self.weapon_type = weapon_type
        print(f"[DEBUG] Arme équipée : {self.weapon_type}")

    def update(self, dt=1):
        self.weapon_equiped.update(dt)

    def render(self, surf, offset=(0, 0)):
        # Le rendu est géré par l'arme équipée elle-même
        self.weapon_equiped.render(surf, offset)

    def swing(self, direction=None):
        self.weapon_equiped.swing(direction)


# ============================================================
# ===============   CLASSE DE BASE ARMES   =================
# ============================================================
class WeaponBase:
    debug = True  # Debug global

    def __init__(self, owner, weapon_type='slashTriangle'):
        self.owner = owner
        self.weapon_type = weapon_type
        self.attack_timer = 0
        self.attack_duration = 15
        self.attack_direction = "front"
        self.angle = 0

        self.damage_number = 50 

        # animation placeholder, charge les sprites selon le type
        self.animation = self.load_animation(weapon_type)

        # distance fixe de l'arme par rapport au joueur
        self.offset_amount = 14 
        self.current_rect = pygame.Rect(0, 0, 0, 0)
        self.cache = {} # (direction, flip, frame_index) -> (img, mask, outline)
        self.is_hitting = False # Pour le changement de couleur debug
    # ------------------------
    # Charge l'animation depuis assets
    # ------------------------
    def load_animation(self, weapon_type):
        anim_asset = self.owner.game.assets.get(weapon_type)
        if anim_asset is None:
            raise ValueError(f"Aucun asset trouvé pour {weapon_type}")
        # Scale pour s'adapter au jeu
        scaled_images = [
            pygame.transform.scale(img, (img.get_width() //4, img.get_height()//4))
            for img in anim_asset.images
        ]
        return anim_asset.__class__(scaled_images, anim_asset.img_duration, anim_asset.loop)

    # ------------------------
    # Toggle debug
    # ------------------------
    def toggle_debug(self):
        WeaponBase.debug = not WeaponBase.debug
        print(f"[DEBUG] Debug weapon: {'ON' if WeaponBase.debug else 'OFF'}")

    # ------------------------
    # Update
    # ------------------------
    def update(self, dt=1):
        self.is_hitting = False # Reset à chaque frame
        if self.attack_timer > 0:
            speed = dt * 60 if dt is not None else 1
            self.attack_timer -= speed
            self.animation.update(dt)
            
            # Sécurité : si l'animation dit qu'elle est finie, on coupe le timer
            if self.animation.done:
                self.attack_timer = 0

            # Utilisation du cache pour l'image et le mask
            self.weapon_image, self.weapon_mask, _ = self.get_cached_data()

            topleft_pos = self.get_render_pos(offset=(0,0))
            self.current_rect = pygame.Rect(topleft_pos, self.weapon_image.get_size())
    # ------------------------
    # Swing / attaque
    # ------------------------
    def swing(self, direction=None):
        # par défaut utiliser le flip du joueur
        if direction is None or direction == "front":
            direction = "left" if self.owner.flip else "right"

        #print()
        if direction == "down" and not self.owner.air_time > 0.09:
            direction = "left" if self.owner.flip else "right"

        self.attack_direction = direction
        self.attack_timer = len(self.animation.images) * self.animation.img_duration
        self.animation.frame = 0
        self.animation.done = False 

    # ------------------------
    # Obtenir l'image et le mask via le cache
    # ------------------------
    def get_cached_data(self):
        frame_idx = int(self.animation.frame / self.animation.img_duration)
        flip = self.owner.flip
        key = (self.attack_direction, flip, frame_idx)
        
        if key in self.cache:
            return self.cache[key]
        
        # Sinon on génère et on stocke
        raw_img = self.animation.images[frame_idx]
        bg_color= raw_img.get_at((0,0))
        raw_img.set_colorkey(bg_color)

        if self.attack_direction == "up":
            angle = 90
        elif self.attack_direction == "down":
            angle = -90
        else:
            angle = 0

        final_img = pygame.transform.rotate(raw_img, angle)

        if self.attack_direction == "left":
            final_img = pygame.transform.flip(final_img, True, False)
        elif self.attack_direction == "front" and flip:
            final_img = pygame.transform.flip(final_img, True, False)
        elif self.attack_direction == "up" and flip:
            final_img = pygame.transform.flip(final_img, True, False)
        elif self.attack_direction == "down" and not flip:
            final_img = pygame.transform.flip(final_img, True, False)
        
        final_mask = pygame.mask.from_surface(final_img)
        final_outline = final_mask.outline()
        self.cache[key] = (final_img, final_mask, final_outline)
        return final_img, final_mask, final_outline

    # ------------------------
    # Obtenir image et mask via le cache
    # ------------------------
    def get_cached_img_mask(self):
        img, mask, _ = self.get_cached_data()
        return img, mask

    # ------------------------
    # Deprecated: Obtenir image (remplacé par get_cached_data)
    # ------------------------
    def get_image(self):
        return self.get_cached_img_mask()[0]

    # ------------------------
    # Calcul de position de rendu
    # ------------------------
    def get_render_pos(self, offset=(0, 0)):
        center_x = self.owner.rect().centerx - offset[0]
        center_y = self.owner.rect().centery - offset[1]

        base_x = center_x - self.get_image().get_width() // 2
        base_y = center_y - self.get_image().get_height() // 2

        # offset selon direction
        if self.attack_direction in ["right", "front"]:
            base_x += self.offset_amount
        elif self.attack_direction == "left":
            base_x -= self.offset_amount
        elif self.attack_direction == "up":
            base_y -= self.offset_amount
        elif self.attack_direction == "down":
            base_y += self.offset_amount

        return (base_x, base_y)

    # ------------------------
    # Hitbox
    # ------------------------
    def rect(self):
        img = self.get_image()
        return img.get_rect(topleft=self.get_render_pos((0, 0)))

    # ------------------------
    # Render
    # ------------------------
    def render(self, surf, offset=(0, 0)):
        if self.attack_timer > 0:
            img = self.get_image()
            surf.blit(img, self.get_render_pos(offset))
            self.render_debug_hitbox(surf, self.rect(), offset)

    # ------------------------
    # Debug hitbox
    # ------------------------
    def render_debug_hitbox(self, surf, rect, offset):
        if WeaponBase.debug:
            img, mask, outline = self.get_cached_data()
            render_pos = (rect.x - offset[0], rect.y - offset[1])
            
            # 1. Draw AABB (Cyan)
            pygame.draw.rect(surf, (0, 255, 255), (render_pos[0], render_pos[1], rect.width, rect.height), 1)

            # 2. Draw Full Mask (Semi-transparent White/Red for better contrast)
            mask_color = (255, 0, 0, 150) if self.is_hitting else (255, 255, 255, 80)
            mask_surf = mask.to_surface(setcolor=mask_color, unsetcolor=(0,0,0,0)).convert_alpha()
            surf.blit(mask_surf, render_pos)

            # 3. Draw Outline (Solid color: Red if hitting, White if idle)
            if outline and len(outline) > 1:
                color_solid = (255, 0, 0) if self.is_hitting else (255, 255, 255)
                adjusted_points = [(p[0] + render_pos[0], p[1] + render_pos[1]) for p in outline]
                pygame.draw.lines(surf, color_solid, True, adjusted_points, 2)

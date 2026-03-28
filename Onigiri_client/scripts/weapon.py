import pygame
import math
import random

class Weapon:
    def __init__(self, owner, weapon_type='slashTriangle'):
        self.owner = owner
        self.weapon_type = weapon_type
        self.weapon_equiped = None  
        self.set_weapon(weapon_type)

    def set_weapon(self, weapon_type):
        if weapon_type in ['mace', 'mace1', 'slashTriangle']:
            self.weapon_equiped = WeaponBase(self.owner, weapon_type)
        else:
            self.weapon_equiped = WeaponBase(self.owner, 'mace')
        self.weapon_type = weapon_type

    def update(self, dt=1):
        self.weapon_equiped.update(dt)

    def render(self, surf, offset=(0, 0)):
        self.weapon_equiped.render(surf, offset)

    def swing(self, direction=None):
        self.weapon_equiped.swing(direction)

class WeaponBase:
    debug = True  

    def __init__(self, owner, weapon_type='slashTriangle'):
        self.owner = owner
        self.weapon_type = weapon_type
        self.attack_timer = 0
        self.attack_duration = 15
        self.attack_direction = "front"
        self.angle = 0
        self.damage_number = 50 
        self.animation = self.load_animation(weapon_type)
        self.offset_amount = 14 
        self.current_rect = pygame.Rect(0, 0, 0, 0)
        self.cache = {} 

    def load_animation(self, weapon_type):
        anim_asset = self.owner.game.assets.get(weapon_type)
        if anim_asset is None:
            raise ValueError(f"Aucun asset trouvé pour {weapon_type}")
        scaled_images = [
            pygame.transform.scale(img, (img.get_width() //4, img.get_height()//4))
            for img in anim_asset.images
        ]
        return anim_asset.__class__(scaled_images, anim_asset.img_duration, anim_asset.loop)

    def toggle_debug(self):
        WeaponBase.debug = not WeaponBase.debug

    def update(self, dt=1):
        if self.attack_timer > 0:
            speed = dt * 60 if dt is not None else 1
            self.attack_timer -= speed
            self.animation.update(dt)
            if self.animation.done:
                self.attack_timer = 0
            self.weapon_image = self.get_cached_data()
            topleft_pos = self.get_render_pos(offset=(0,0))
            self.current_rect = pygame.Rect(topleft_pos, self.weapon_image.get_size())

    def swing(self, direction=None):
        if direction is None or direction == "front":
            direction = "left" if self.owner.flip else "right"
        if direction == "down" and not self.owner.air_time > 0.09:
            direction = "left" if self.owner.flip else "right"
        self.attack_direction = direction
        self.attack_timer = len(self.animation.images) * self.animation.img_duration
        self.animation.frame = 0
        self.animation.done = False 

    def get_cached_data(self):
        frame_idx = int(self.animation.frame / self.animation.img_duration)
        flip = self.owner.flip
        key = (self.attack_direction, flip, frame_idx)
        if key in self.cache:
            return self.cache[key]
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
        if self.attack_direction == "down" and not flip:
            final_img = pygame.transform.flip(final_img, True, False)
        self.cache[key] = final_img
        return final_img

    def get_image(self):
        return self.get_cached_data()

    def get_render_pos(self, offset=(0, 0)):
        center_x = self.owner.rect().centerx - offset[0]
        center_y = self.owner.rect().centery - offset[1]
        base_x = center_x - self.get_image().get_width() // 2
        base_y = center_y - self.get_image().get_height() // 2
        if self.attack_direction in ["right", "front"]:
            base_x += self.offset_amount
        elif self.attack_direction == "left":
            base_x -= self.offset_amount
        elif self.attack_direction == "up":
            base_y -= self.offset_amount
        elif self.attack_direction == "down":
            base_y += self.offset_amount
        return (base_x, base_y)

    def rect(self):
        img = self.get_image()
        return img.get_rect(topleft=self.get_render_pos((0, 0)))

    def render(self, surf, offset=(0, 0)):
        if self.attack_timer > 0:
            img = self.get_image()
            render_pos = self.get_render_pos(offset)
            surf.blit(img, render_pos)
            if getattr(self.owner.game, 'debug', False):
                mask = self.animation.get_pygame_mask(self.owner.flip) if hasattr(self.animation, 'get_pygame_mask') else None
                if mask:
                    mask_surf = mask.to_surface(setcolor=(255, 0, 255, 128), unsetcolor=(0, 0, 0, 0)).convert_alpha()
                    surf.blit(mask_surf, render_pos)
                else:
                    rect = self.rect()
                    pygame.draw.rect(surf, (0, 255, 255), (rect.x - offset[0], rect.y - offset[1], rect.width, rect.height), 1)

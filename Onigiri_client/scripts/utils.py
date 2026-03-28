import os
import pygame
import sys

def resource_path(relative_path):
    """PyInstaller support"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

BASE_IMG_PATH = 'data/images/'

def load_image(path, convert_alpha=False):
    """path doit être relatif à BASE_IMG_PATH"""
    full_path = resource_path(os.path.join(BASE_IMG_PATH, path))
    img = pygame.image.load(full_path, "RGBA")
    
    if convert_alpha:
        img.set_colorkey((0, 0, 0))
        img = img.convert_alpha()
    
    return img


def load_images(path, convert_alpha: list | bool = False):
    folder_path = resource_path(os.path.join(BASE_IMG_PATH, path))
    images = []
    for img_name in sorted(os.listdir(folder_path)):
        if (type(convert_alpha) == bool and convert_alpha) or (type(convert_alpha) == list and img_name[:-4] in convert_alpha):
            images.append(load_image(os.path.join(path, img_name), True))
        else:
            images.append(load_image(os.path.join(path, img_name), False))
    return images

def load_animation_with_masks(path, img_dur=5, loop=True, convert_alpha=False, col_path=None):
    path = os.path.normpath(path)
    images = load_images(path, convert_alpha)
    
    if col_path is None:
        dirname, basename = os.path.split(path)
        col_path = os.path.join(dirname, f"col_{basename}")
    else:
        col_path = os.path.normpath(col_path)
    
    full_col_path = resource_path(os.path.join(BASE_IMG_PATH, col_path))
    masks = None
    if os.path.exists(full_col_path):
        masks = load_images(col_path, convert_alpha)
        
    return Animation(images, img_dur=img_dur, loop=loop, masks=masks)
class Animation:
    def __init__(self, images, img_dur=5, loop=True, masks=None):
        self.images = images
        self.masks = masks
        if self.masks:
            self.pygame_masks = [pygame.mask.from_surface(img) for img in self.masks]
            self.pygame_masks_flipped = [pygame.mask.from_surface(pygame.transform.flip(img, True, False)) for img in self.masks]
        else:
            self.pygame_masks = None
            self.pygame_masks_flipped = None

        self.loop = loop
        self.img_duration = img_dur
        self.done = False
        self.frame = 0 

    def copy(self):
        return Animation(self.images, self.img_duration, self.loop, masks=self.masks)

    def update(self, dt=None):
        speed = dt * 60 if dt is not None else 1
        
        self.frame += speed
        
        total_duration = self.img_duration * len(self.images)
        
        if self.loop:
            self.frame = self.frame % total_duration
        else:
            if self.frame >= total_duration:
                self.frame = total_duration - 0.01
                self.done = True
    
    def img(self):
        index = int(self.frame / self.img_duration)
        index = max(0, min(index, len(self.images) - 1))
        return self.images[index]

    def mask_img(self):
        if not self.masks:
            return None
        index = int(self.frame / self.img_duration)
        index = max(0, min(index, len(self.masks) - 1))
        return self.masks[index]

    def get_pygame_mask(self, flip=False):
        if not self.masks:
            return None
        index = int(self.frame / self.img_duration)
        index = max(0, min(index, len(self.masks) - 1))
        target_list = self.pygame_masks_flipped if flip else self.pygame_masks
        return target_list[index]

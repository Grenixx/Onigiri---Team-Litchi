import os
import pygame
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

BASE_IMG_PATH = 'data/images/'

def load_image(path, convert_alpha=False):
    """path doit être relatif à BASE_IMG_PATH"""
    full_path = resource_path(os.path.join(BASE_IMG_PATH, path))
    img = pygame.image.load(full_path)
    
    # On force le colorkey noir AVANT le convert_alpha pour les masques
    img.set_colorkey((0, 0, 0))
    
    if convert_alpha:
        img = img.convert_alpha()
    else:
        img = img.convert()
        
    return img


def load_images(path, convert_alpha=False):
    """path doit être relatif à BASE_IMG_PATH"""
    folder_path = resource_path(os.path.join(BASE_IMG_PATH, path))
    images = []
    for img_name in sorted(os.listdir(folder_path)):
        if os.path.isfile(os.path.join(folder_path, img_name)):
            images.append(load_image(os.path.join(path, img_name), convert_alpha=convert_alpha))  # ne pas rajouter BASE_IMG_PATH ici !
    return images


class Animation:
    def __init__(self, images, img_dur=5, loop=True):
        self.images = images
        self.loop = loop
        self.img_duration = img_dur
        self.done = False
        self.frame = 0 
        self.masks = [pygame.mask.from_surface(img) for img in self.images]
        self.flipped_masks = [pygame.mask.from_surface(pygame.transform.flip(img, True, False)) for img in self.images]

    def copy(self):
        return Animation(self.images, self.img_duration, self.loop)

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
    
    def mask(self, flip=False):
        index = int(self.frame / self.img_duration)
        masks = self.flipped_masks if flip else self.masks
        index = max(0, min(index, len(masks) - 1))
        return masks[index]

import pygame
import math
import random

import sys, os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class LightingSystem:
    def __init__(self, size):
        self.size = size
        self.light_mask = pygame.image.load(resource_path('data/images/lights/light.png')).convert()
        self.light_mask.set_colorkey((0, 0, 0))
        self.light_mask.set_alpha(255)

        self.light_masks = [pygame.transform.smoothscale(self.light_mask, (r, r)) for r in range(10, 400)]

        self.ambient_color = (10, 10, 20)

    def render(self, display, light_sources, global_time=0):
        light_surface = pygame.Surface(self.size).convert()
        light_surface.fill(self.ambient_color)

        for source in light_sources:
            if len(source) == 3:
                x, y, radius = source
                color = (255, 255, 255)
            else:
                x, y, radius, color = source

            pulse = math.sin(global_time * 0.002 + (x + y) * 0.0001) * 0.05 + 0.95
            current_radius = int(radius * pulse)
            current_radius = max(10, min(current_radius, len(self.light_masks) - 1))

            glow = self.light_masks[current_radius].copy()
            glow.fill(color, special_flags=pygame.BLEND_RGBA_MULT)

            light_surface.blit(glow, (x - glow.get_width() // 2, y - glow.get_height() // 2),
                               special_flags=pygame.BLEND_RGBA_ADD)


        display.blit(light_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

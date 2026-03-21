import math

import pygame

class Spark:
    def __init__(self, pos, angle, speed):
        self.pos = list(pos)
        self.angle = angle
        self.speed = speed
        
    def update(self, dt=1.0):
        # On normalise sur 60 FPS (si dt est en secondes, dt*60 donne le facteur par rapport à une frame à 60FPS)
        frame_factor = dt * 60 
        
        self.pos[0] += math.cos(self.angle) * self.speed * frame_factor
        self.pos[1] += math.sin(self.angle) * self.speed * frame_factor
        
        self.speed = max(0, self.speed - 0.1 * frame_factor)
        return not self.speed
    
    def render(self, surf, offset=(0, 0)):
        """
        Le glow est fonctionel juste pas utile pour l instant (jpref sans mais j'ai quand meme coder pour plus tard héhé)
        """
        # 1. Dessin de la lueur (Glow)
        # On crée une petite surface pour la lueur additive
        #glow_size = int(self.speed * 8)
        #if glow_size > 0:
        #    glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            # Couleur lueur (orange/jaune pâle)
        #    pygame.draw.circle(glow_surf, (255, 100, 50, 60), (glow_size, glow_size), glow_size)
            # On blit en mode ADD sur la surface principale
        #    surf.blit(glow_surf, (self.pos[0] - glow_size - offset[0], self.pos[1] - glow_size - offset[1]), special_flags=pygame.BLEND_RGB_ADD)

        # 2. Dessin du cœur de l'étincelle (Polygon)
        render_points = [
            (self.pos[0] + math.cos(self.angle) * self.speed * 3 - offset[0], self.pos[1] + math.sin(self.angle) * self.speed * 3 - offset[1]),
            (self.pos[0] + math.cos(self.angle + math.pi * 0.5) * self.speed * 0.5 - offset[0], self.pos[1] + math.sin(self.angle + math.pi * 0.5) * self.speed * 0.5 - offset[1]),
            (self.pos[0] + math.cos(self.angle + math.pi) * self.speed * 3 - offset[0], self.pos[1] + math.sin(self.angle + math.pi) * self.speed * 3 - offset[1]),
            (self.pos[0] + math.cos(self.angle - math.pi * 0.5) * self.speed * 0.5 - offset[0], self.pos[1] + math.sin(self.angle - math.pi * 0.5) * self.speed * 0.5 - offset[1]),
        ]
        
        pygame.draw.polygon(surf, (255, 255, 255), render_points)
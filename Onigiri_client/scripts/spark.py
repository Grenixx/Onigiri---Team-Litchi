import math

import pygame

class Spark:
    def __init__(self, pos, angle, speed):
        self.pos = list(pos)
        self.angle = angle
        self.speed = speed
        
    def update(self, dt=1.0):
        frame_factor = dt * 60 
        
        self.pos[0] += math.cos(self.angle) * self.speed * frame_factor
        self.pos[1] += math.sin(self.angle) * self.speed * frame_factor
        
        self.speed = max(0, self.speed - 0.1 * frame_factor)
        return not self.speed
    
    def render(self, surf, offset=(0, 0)):
        size = int(self.speed * 5) + 1
        if size > 1:
            glow_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            
            for sl, st, color in [(4.0, 1.2, (255, 255, 255, 120)), (3.5, 0.8, (255, 255, 255, 180))]:
                pts = [
                    (size + math.cos(self.angle) * self.speed * sl, size + math.sin(self.angle) * self.speed * sl),
                    (size + math.cos(self.angle + math.pi * 0.5) * self.speed * st, size + math.sin(self.angle + math.pi * 0.5) * self.speed * st),
                    (size + math.cos(self.angle + math.pi) * self.speed * sl, size + math.sin(self.angle + math.pi) * self.speed * sl),
                    (size + math.cos(self.angle - math.pi * 0.5) * self.speed * st, size + math.sin(self.angle - math.pi * 0.5) * self.speed * st),
                ]
                pygame.draw.polygon(glow_surf, color, pts)
            
            surf.blit(glow_surf, (self.pos[0] - size - offset[0], self.pos[1] - size - offset[1]), special_flags=pygame.BLEND_RGB_ADD)

        render_points = [
            (self.pos[0] + math.cos(self.angle) * self.speed * 3 - offset[0], self.pos[1] + math.sin(self.angle) * self.speed * 3 - offset[1]),
            (self.pos[0] + math.cos(self.angle + math.pi * 0.5) * self.speed * 0.5 - offset[0], self.pos[1] + math.sin(self.angle + math.pi * 0.5) * self.speed * 0.5 - offset[1]),
            (self.pos[0] + math.cos(self.angle + math.pi) * self.speed * 3 - offset[0], self.pos[1] + math.sin(self.angle + math.pi) * self.speed * 3 - offset[1]),
            (self.pos[0] + math.cos(self.angle - math.pi * 0.5) * self.speed * 0.5 - offset[0], self.pos[1] + math.sin(self.angle - math.pi * 0.5) * self.speed * 0.5 - offset[1]),
        ]
        pygame.draw.polygon(surf, (255, 255, 255), render_points)
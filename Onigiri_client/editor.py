import sys
    
import pygame

from scripts.utils import load_images
from scripts.tilemap import Tilemap

import os

RENDER_SCALE = 2.0

class Editor:
    def __init__(self):
        pygame.init()

        pygame.display.set_caption('Onigiri Editor')
        self.window_size = (640, 360)
        self.fullscreen = False

        self.screen = pygame.display.set_mode(
            self.window_size,
            pygame.RESIZABLE
        )
        self.display = pygame.Surface((320, 180))

        self.clock = pygame.time.Clock()
        
        self.assets = {
            'decor': load_images('tiles/decor'),
            'grass': load_images('tiles/grass'),
            'large_decor': load_images('tiles/large_decor'),
            'stone': load_images('tiles/stone'),
            'spawners': load_images('tiles/spawners'),
            'grassSpawner': load_images('grass'), #celui qui retire le commentaire je l encule 
            'tuto': load_images('tuto/steles'),
            'texte':load_images('tuto/texte'),
        }
        
        
        self.movement = [False, False, False, False]
        
        self.tilemap = Tilemap(self, tile_size=16)
        
        self.level = 0
        self.load_level(self.level)
        
        self.scroll = [0, 0]
        
        self.tile_list = list(self.assets)
        self.tile_group = 0
        self.tile_variant = 0
        
        self.clicking = False
        self.right_clicking = False
        self.shift = False
        self.ongrid = True
        
        # UI
        self.font = pygame.font.SysFont('Arial', 16)
        self.text_input_active = False
        self.level_input = ""
        
    def load_level(self, level_id):
        self.level = level_id
        self.tilemap.tilemap = {}
        self.tilemap.offgrid_tiles = []
        self.scroll = [0, 0]
        try:
            self.tilemap.load(f'data/maps/{self.level}.json')
            print(f"Loaded level {self.level}")
        except FileNotFoundError:
            print(f"New level {self.level} created (empty)")
        
    def run(self):
        while True:
            self.display.fill((0, 0, 0))
            
            self.scroll[0] += (self.movement[1] - self.movement[0]) * 2
            self.scroll[1] += (self.movement[3] - self.movement[2]) * 2
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))
            
            self.tilemap.render(self.display, offset=render_scroll, show_spawners=True)
            
            current_tile_img = self.assets[self.tile_list[self.tile_group]][self.tile_variant].copy()
            current_tile_img.set_alpha(100)
            
            mx, my = pygame.mouse.get_pos()
            sw, sh = self.screen.get_size()

            scale_x = sw / self.display.get_width() 
            scale_y = sh / self.display.get_height()

            mpos = (mx / scale_x, my / scale_y)

            tile_pos = (int((mpos[0] + self.scroll[0]) // self.tilemap.tile_size), int((mpos[1] + self.scroll[1]) // self.tilemap.tile_size))
            
            if self.ongrid:
                self.display.blit(current_tile_img, (tile_pos[0] * self.tilemap.tile_size - self.scroll[0], tile_pos[1] * self.tilemap.tile_size - self.scroll[1]))
            else:
                self.display.blit(current_tile_img, mpos)
            
            if self.clicking and self.ongrid:
                self.tilemap.tilemap[str(tile_pos[0]) + ';' + str(tile_pos[1])] = {'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': tile_pos}
            if self.right_clicking:
                tile_loc = str(tile_pos[0]) + ';' + str(tile_pos[1])
                if tile_loc in self.tilemap.tilemap:
                    del self.tilemap.tilemap[tile_loc]
                for tile in self.tilemap.offgrid_tiles.copy():
                    tile_img = self.assets[tile['type']][tile['variant']]
                    tile_r = pygame.Rect(tile['pos'][0] - self.scroll[0], tile['pos'][1] - self.scroll[1], tile_img.get_width(), tile_img.get_height())
                    if tile_r.collidepoint(mpos):
                        self.tilemap.offgrid_tiles.remove(tile)
            
            self.display.blit(current_tile_img, (5, 5))
            
            # HUD
            level_text = self.font.render(f"Level: {self.level}", False, (255, 255, 255))
            self.display.blit(level_text, (5, 160))
            
            tile_text = self.font.render(f"Tile: {self.tile_list[self.tile_group]} #{self.tile_variant}", False, (255, 255, 255))
            self.display.blit(tile_text, (5, 145))
            
            if self.text_input_active:
                pygame.draw.rect(self.display, (0, 0, 0), (95, 160, 40, 20))
                pygame.draw.rect(self.display, (255, 255, 255), (95, 160, 40, 20), 1)
                input_text = self.font.render(self.level_input + "_", False, (255, 255, 255))
                self.display.blit(input_text, (100, 160))
            else:
                help_text = self.font.render("[UP/DOWN] Level [L] Jump [N] New [O] Save", False, (150, 150, 150))
                self.display.blit(help_text, (5, 175))
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                    
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.clicking = True
                        if not self.ongrid:
                            self.tilemap.offgrid_tiles.append({'type': self.tile_list[self.tile_group], 'variant': self.tile_variant, 'pos': (mpos[0] + self.scroll[0], mpos[1] + self.scroll[1])})
                    if event.button == 3:
                        self.right_clicking = True
                    if self.shift:
                        if event.button == 4:
                            self.tile_variant = (self.tile_variant - 1) % len(self.assets[self.tile_list[self.tile_group]])
                        if event.button == 5:
                            self.tile_variant = (self.tile_variant + 1) % len(self.assets[self.tile_list[self.tile_group]])
                    else:
                        if event.button == 4:
                            self.tile_group = (self.tile_group - 1) % len(self.tile_list)
                            self.tile_variant = 0
                        if event.button == 5:
                            self.tile_group = (self.tile_group + 1) % len(self.tile_list)
                            self.tile_variant = 0
                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.clicking = False
                    if event.button == 3:
                        self.right_clicking = False
                        

                if event.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:
                        self.window_size = (event.w, event.h)

                if event.type == pygame.KEYDOWN:
                    if self.text_input_active:
                        if event.key == pygame.K_RETURN:
                            if self.level_input:
                                self.load_level(int(self.level_input))
                            self.text_input_active = False
                            self.level_input = ""
                        elif event.key == pygame.K_BACKSPACE:
                            self.level_input = self.level_input[:-1]
                        elif event.unicode.isdigit():
                            self.level_input += event.unicode
                        elif event.key == pygame.K_ESCAPE:
                            self.text_input_active = False
                        continue # Skip other key inputs when typing

                    if event.key == pygame.K_q:
                        self.movement[0] = True
                    if event.key == pygame.K_d:
                        self.movement[1] = True
                    if event.key == pygame.K_z:
                        self.movement[2] = True
                    if event.key == pygame.K_s:
                        self.movement[3] = True
                    if event.key == pygame.K_g:
                        self.ongrid = not self.ongrid
                    if event.key == pygame.K_l:
                        self.text_input_active = True
                        self.level_input = ""
                    if event.key == pygame.K_t:
                        self.tilemap.autotile()
                    if event.key == pygame.K_n:
                        # Trouver le prochain numéro libre
                        i = 0
                        while os.path.exists(f'data/maps/{i}.json'):
                            i += 1
                        self.load_level(i)
                        print(f"Created new level at index {self.level}")
                    if event.key == pygame.K_o:
                        client_path = f'data/maps/{self.level}.json'
                        server_path = f'../Onigiri_server/data/maps/{self.level}.json'
                        
                        # Sauvegarde Client
                        self.tilemap.save(client_path)
                        print(f'Map saved to {client_path}')
                        
                        # Sauvegarde Serveur (si le dossier existe)
                        if os.path.exists('../Onigiri_server/data/maps'):
                            self.tilemap.save(server_path)
                            print(f'Map saved to {server_path}')
                        else:
                            print(f'Warning: Server map folder not found at {server_path}')
                    if event.key == pygame.K_UP:
                        self.load_level(self.level + 1)
                    if event.key == pygame.K_DOWN:
                        if self.level > 0:
                            self.load_level(self.level - 1)

                    if event.key == pygame.K_LSHIFT:
                        self.shift = True
                    if event.key == pygame.K_F11:
                        self.fullscreen = not self.fullscreen

                        if self.fullscreen:
                            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        else:
                            self.screen = pygame.display.set_mode(
                                self.window_size,
                                pygame.RESIZABLE
                            )


                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_q:
                        self.movement[0] = False
                    if event.key == pygame.K_d:
                        self.movement[1] = False
                    if event.key == pygame.K_z:
                        self.movement[2] = False
                    if event.key == pygame.K_s:
                        self.movement[3] = False
                    if event.key == pygame.K_LSHIFT:
                        self.shift = False
                

            
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
            pygame.display.update()
            self.clock.tick(60)

Editor().run()
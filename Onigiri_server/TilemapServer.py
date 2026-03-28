import json

PHYSICS_TILES = {'grass', 'stone'}

class TilemapServer:
    def __init__(self, tile_size=16):
        self.tile_size = tile_size
        self.tilemap = {}
    
    def load(self, path):
        """Charge la map depuis le JSON généré par le client."""
        with open(path, 'r') as f:
            map_data = json.load(f)
        
        self.tilemap = map_data['tilemap']
        self.tile_size = map_data['tile_size']
        
        self.spawners = []
        if 'offgrid' in map_data:
            for item in map_data['offgrid']:
                if item['type'] == 'spawners':
                    self.spawners.append(item)
                    
        # Check grid tiles for spawners
        for loc, tile in self.tilemap.items():
            if tile['type'] == 'spawners':
                # Create a copy to not modify the original tile data in place if we were to save it back
                spawner = tile.copy()
                # Grid pos to pixel pos
                spawner['pos'] = [tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size]
                self.spawners.append(spawner)

    def solid_check(self, pos):
        """Vérifie si une position est dans une tuile solide."""
        tile_loc = f"{int(pos[0] // self.tile_size)};{int(pos[1] // self.tile_size)}"
        if tile_loc in self.tilemap:
            if self.tilemap[tile_loc]['type'] in PHYSICS_TILES:
                return True
        return False

    def rects_around(self, pos):
        """Retourne les rectangles de collision autour d'une position."""
        rects = []
        tile_loc = (int(pos[0] // self.tile_size), int(pos[1] // self.tile_size))
        for x in range(tile_loc[0] - 1, tile_loc[0] + 2):
            for y in range(tile_loc[1] - 1, tile_loc[1] + 2):
                loc = f"{x};{y}"
                if loc in self.tilemap:
                    tile = self.tilemap[loc]
                    if tile['type'] in PHYSICS_TILES:
                        rects.append(((x * self.tile_size, y * self.tile_size),
                                      self.tile_size, self.tile_size))
        return rects
    
    def check_type(self, pos):
        tile_loc = f"{int(pos[0] // self.tile_size)};{int(pos[1] // self.tile_size)}"
        if tile_loc in self.tilemap:
            return self.tilemap[tile_loc]['type']
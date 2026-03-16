import os
os.environ['SDL_VIDEO_CENTERED'] = '1'
import sys
import subprocess
import atexit
import pygame
import moderngl
import json
from game import Game
from scripts.lobby_discovery import LobbyManager
from scripts.shader_bg import ShaderBackground

pygame.init()

from screeninfo import get_monitors

monitors = get_monitors()
for m in monitors:
    if m.is_primary:
        monitor = m
        break

WIDTH, HEIGHT = monitor.width, monitor.height

FPS = 60
BG_COLOR = (30, 30, 40)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER = (100, 160, 210)
TEXT_COLOR = (255, 255, 255)
FONT_NAME = None  
FONT_SIZE = 36
CONTROLS={"LEFT":pygame.K_q,"RIGHT":pygame.K_d,"JUMP":pygame.K_SPACE,"DASH":pygame.K_LSHIFT,"CHANGE ARM":pygame.K_TAB,"UP":pygame.K_z,"DOWN":pygame.K_DOWN,"ATTACK":pygame.K_f}
DATA = {
    "controls": CONTROLS, "graphics": [WIDTH, HEIGHT], "fps": FPS
}



USER_PREFS_FILE = "user_prefs.json"
wait_key=False
action_changing=None


def reset_user_prefs():
    global CONTROLS, WIDTH, HEIGHT, FPS
    CONTROLS={"LEFT":pygame.K_q,"RIGHT":pygame.K_d,"JUMP":pygame.K_SPACE,"DASH":pygame.K_LSHIFT,"CHANGE ARM":pygame.K_TAB,"UP":pygame.K_UP,"DOWN":pygame.K_DOWN,"ATTACK":pygame.K_f}
    WIDTH, HEIGHT = monitor.width, monitor.height
    FPS = 60
    update_user_prefs()
    save_user_prefs()
    resize(WIDTH, HEIGHT) 
    for menu in lst_menu:
        menu.rebuild()  

def save_user_prefs():
    with open(USER_PREFS_FILE, 'w') as f:
        json.dump(DATA, f)

    
def update_user_prefs():
    DATA["controls"] = CONTROLS
    DATA["graphics"] = [WIDTH, HEIGHT]
    DATA["fps"] = FPS
    save_user_prefs()


def load_user_prefs():
    global CONTROLS, WIDTH, HEIGHT, FPS
    with open(USER_PREFS_FILE, 'r') as f:
        data = json.load(f)
        CONTROLS.update(data.get("controls", {}))
        graphics = data.get("graphics", [WIDTH, HEIGHT])
        if len(graphics) == 2:
            WIDTH, HEIGHT = graphics
        FPS = data.get("fps", FPS)


if os.path.exists(USER_PREFS_FILE):
    load_user_prefs()

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Menu")
clock = pygame.time.Clock()
font = pygame.font.Font(FONT_NAME, FONT_SIZE)
# Initialisation Shader
ctx = moderngl.create_standalone_context()
# On utilise une résolution interne plus petite pour l'effet pixel art, comme dans le jeu (320x180)
# Mais pour le menu, on peut vouloir un truc plus net. Essayons la résolution native / 4 pour un effet un peu rétro mais lisible.
# Ou restons cohérents avec le jeu : 320x180.
limit_res = (320, 180) 
limit_surface = pygame.Surface(limit_res)
shader_bg = ShaderBackground(limit_res[0], limit_res[1], "data/shaders/2.7.frag", ctx=ctx)

# On garde BACKGROUND_DIM pour la fonction resize au cas où, mais on ne l'utilise plus pour l'affichage direct
BACKGROUND = pygame.image.load("data/images/menuImage/Background/backgroundtemp.png").convert()
BACKGROUND_DIM = pygame.transform.smoothscale(BACKGROUND, (WIDTH, HEIGHT))

def render_text(text, font, color):
    return font.render(text, True, color)


class Button:
    def __init__(self, rect, text, callback, font,
                 color=BUTTON_COLOR, hover_color=BUTTON_HOVER,
                 text_color=TEXT_COLOR):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.hovered = False
        self._render_label()

    def _render_label(self):
        self.label = render_text(self.text, self.font, self.text_color)
        self.label_rect = self.label.get_rect(center=self.rect.center)

    def draw(self, surface):
        color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        surface.blit(self.label, self.label_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if callable(self.callback):
                    self.callback()




class InputButton(Button):
    def __init__(self, rect, text, font, color=BUTTON_COLOR, hover_color=BUTTON_HOVER, text_color=TEXT_COLOR):
        super().__init__(rect, text, None, font, color, hover_color, text_color)
        self.active = False
        self.input_text = text

    def draw(self, surface):
        color = self.hover_color if self.active or self.hovered else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        
        # Render text (append cursor if active)
        display_text = self.input_text + ("|" if self.active and (pygame.time.get_ticks() // 500) % 2 == 0 else "")
        label = render_text(display_text, self.font, self.text_color)
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def handle_event(self, event):
        super().handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.active = True
            else:
                self.active = False
        
        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                # Add character if printable
                if len(self.input_text) < 20 and event.unicode.isprintable():
                    self.input_text += event.unicode
            # Update label isn't strictly necessary here as draw handles it dynamically

class Menu:
    def __init__(self, title, items, font, spacing=16):
        self.title = title
        self.font = font
        self.items = []
        self.items_data = items
        self.spacing = spacing
        self.selected = 0
        self.visible = True
        self._build_buttons(items)

    def rebuild(self):
        self.items.clear()
        self._build_buttons(self.items_data)

    def _build_buttons(self, items):
        button_w = 300
        button_h = 60
        total_h = len(items) * button_h + (len(items) - 1) * self.spacing
        start_y = (HEIGHT - total_h) // 2
        x = (WIDTH - button_w) // 2
        
        for i, item in enumerate(items):
            y = start_y + i * (button_h + self.spacing)
            rect = (x, y, button_w, button_h)
            
            if isinstance(item, Button):
                 # Item is already a widget, just update its position
                 item.rect = pygame.Rect(rect)
                 # Re-render label if it's a standard button to center it
                 if hasattr(item, '_render_label'):
                     item._render_label()
                 self.items.append(item)
            elif isinstance(item, tuple):
                # Standard text, callback tuple
                text, callback = item
                display_text = text() if callable(text) else text
                btn = Button(rect, display_text, callback, self.font)
                self.items.append(btn)

    def draw(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        surface.blit(overlay, (0, 0))
        title_font = pygame.font.Font(FONT_NAME, FONT_SIZE + 10)
        title_surf = title_font.render(self.title, True, TEXT_COLOR)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, HEIGHT * 0.2))
        surface.blit(title_surf, title_rect)
        for i, btn in enumerate(self.items):
            if isinstance(btn, Button) and not isinstance(btn, InputButton):
                 btn.hovered = (i == self.selected)
            elif isinstance(btn, InputButton):
                 btn.hovered = (i == self.selected)
            
            btn.draw(surface)

    def handle_event(self, event):
        # Prioritize input handling
        for btn in self.items:
            btn.handle_event(event)
            
        # Navigation logic
        if not any(isinstance(b, InputButton) and b.active for b in self.items):
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    self.selected = (self.selected + 1) % len(self.items)
                elif event.key == pygame.K_UP:
                    self.selected = (self.selected - 1) % len(self.items)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    selected_btn = self.items[self.selected]
                    if hasattr(selected_btn, 'callback') and callable(selected_btn.callback):
                        selected_btn.callback()


def start_game(ip="127.0.0.1"):
    game = Game(FPS, [WIDTH,HEIGHT], ip=ip)
    update_user_prefs()
    save_user_prefs()
    game.run()
    
    # Au retour, on s'assure que l'écran du menu est bien défini
    global screen
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

def open_options():
    global active_menu
    active_menu = options_menu


def quit_game():
    update_user_prefs()
    save_user_prefs()
    pygame.quit()
    sys.exit()
  

def cleanup_server():
    """Ferme proprement le serveur s'il est resté ouvert."""
    if sys.platform == "win32":
        try:
            # On tue tous les processus qui ont 'NinjaGameServer' dans le titre de leur fenêtre
            # /T tue aussi les processus enfants (le script python lui-même)
            subprocess.run(['taskkill', '/F', '/FI', 'WINDOWTITLE eq NinjaGameServer*', '/T'], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

# Enregistre la fonction pour qu'elle s'exécute à la fermeture (même Alt+F4)
atexit.register(cleanup_server)

def resize(new_width, new_height):
    global WIDTH,HEIGHT, screen, BACKGROUND_DIM
    WIDTH,HEIGHT = new_width,new_height
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    # On laisse le shader à sa résolution interne fixe (320x180) qu'on étire, 
    # c'est plus joli pour le pixel art et plus performant.
    for menu in lst_menu:
        menu.rebuild()
    update_user_prefs()
    

def rebinding(action):
    global wait_key, action_changing
    wait_key = True
    action_changing = action
    print(CONTROLS)


def refps(fps_value):
    global FPS
    FPS=fps_value
    update_user_prefs()




def refresh_servers():
    global server_menu
    items = []
    print("Recherche de serveurs...")
    servers = LobbyManager.get_server_list()
    
    if not servers:
        items.append(("No servers found", None))
    else:
        for s in servers:
            # On capture la variable s['ip'] avec un argument par défaut dans la lambda
            label = f"{s.get('name', 'Unknown')} ({s.get('ip')})"
            action = lambda ip=s.get('ip'): start_game(ip)
            items.append((label, action))
            
    items.append(("Refresh", refresh_servers))
    items.append(("Back", lambda: set_active_menu(main_menu)))
    
    server_menu.items_data = items
    server_menu.rebuild()

def open_server_browser():
    refresh_servers()
    set_active_menu(server_menu)

# Input field for server name
server_name_input = InputButton((0,0,0,0), "Ninja Server", font)

def host_game():
    update_user_prefs() 
    save_user_prefs() 
    """Lance le serveur via le fichier .bat et rejoint la partie."""
    import time
    
    print("Démarrage du serveur via start_server.bat...")
    
    # Chemin vers le .bat dans ninja_game_server
    bat_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ninja_game_server/start_server.bat'))
    
    try:
        # Lance le .bat (qui ouvre une nouvelle console automatiquement)
        subprocess.Popen([bat_path], shell=True)
        
        # Attente simple de 2 secondes (le .bat est rapide et fiable)
        print("Attente du démarrage du serveur (2 secondes)...")
        time.sleep(2)
        
        # On rejoint automatiquement en local
        start_game("127.0.0.1")
        
    except Exception as e:
        print(f"Erreur au lancement du serveur : {e}")

def open_host_menu():
    set_active_menu(host_menu)

# Menu vide pour l'instant, sera rempli par refresh_servers
server_menu = Menu("Server Browser", [("Loading...", None), ("Back", lambda: set_active_menu(main_menu))], font)

host_menu = Menu("Host Game", [
    server_name_input,
    ("Start Server", host_game),
    ("Back", lambda: set_active_menu(main_menu))
], font)

main_menu = Menu("Main Menu", [("HOST GAME", open_host_menu), ("FIND GAME", open_server_browser),("OPTIONS", open_options),("QUIT GAME", quit_game),], font)
options_menu = Menu("Options", [("Audio",None),("Keyboards",lambda: set_active_menu(keyboard_menu)),("Graphics",lambda: set_active_menu(graphics_menu)),("FPS",lambda: set_active_menu(fps_menu)),("Reset Preferences", lambda : reset_user_prefs()),("Back", lambda: set_active_menu(main_menu)),], font)
keyboard_menu = Menu("Keyboard", [(lambda: f"Jump : {pygame.key.name(CONTROLS['JUMP'])}", lambda: rebinding("JUMP")),(lambda: f"Change Arm : {pygame.key.name(CONTROLS['CHANGE ARM'])}", lambda: rebinding("CHANGE ARM")),(lambda: f"Dash : {pygame.key.name(CONTROLS['DASH'])}", lambda: rebinding("DASH")),(lambda: f"Left : {pygame.key.name(CONTROLS['LEFT'])}", lambda: rebinding("LEFT")),(lambda: f"Right : {pygame.key.name(CONTROLS['RIGHT'])}", lambda: rebinding("RIGHT")),("Back", lambda: set_active_menu(options_menu))
], font)
graphics_menu = Menu("Graphics",[("3840-2160",lambda: resize(3840, 2160)),("2560-1440",lambda: resize(2560, 1440)),("1920-1080",lambda: resize(1920, 1080)),("1680-1050",lambda: resize(1680, 1050)),("1280-720",lambda: resize(1280,720)),("1024-768",lambda: resize(1024,768)),("800-600",lambda: resize(800,600)),("Back", lambda: set_active_menu(options_menu))],font)
fps_menu = Menu("FPS",[("30 FPS",lambda: refps(30)),("45 FPS",lambda: refps(45)),("60 FPS",lambda: refps(60)),("120 FPS",lambda: refps(120)),("144 FPS",lambda: refps(144)),("165 FPS",lambda: refps(165)),("180 FPS",lambda: refps(180)),("240 FPS",lambda: refps(240)),("UNCAPPED FPS",lambda: refps(100000000)),("Back", lambda: set_active_menu(options_menu))],font)
lst_menu = [main_menu,host_menu,options_menu,keyboard_menu,graphics_menu,server_menu]


def set_active_menu(menu):
    global active_menu, last_menu
    last_menu = active_menu 
    active_menu = menu
    


active_menu = main_menu
last_menu = main_menu


def main():
    if not os.path.exists(USER_PREFS_FILE):
        save_user_prefs()  # Crée un fichier de préférences par défaut s'il n'existe pas
    else :
        load_user_prefs() 
    for menu in lst_menu:
        menu.rebuild()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                set_active_menu(last_menu)
            global wait_key, action_changing
            if wait_key and event.type == pygame.KEYDOWN:
                CONTROLS[action_changing] = event.key
                wait_key = False
                action_changing = None
                update_user_prefs()
                for menu in lst_menu:  
                    menu.rebuild() 
                continue
            if active_menu:
                active_menu.handle_event(event)

        # Rendu du Shader
        # On peut simuler une caméra qui bouge lentement pour l'effet
        cam_x = pygame.time.get_ticks() * 0.5
        cam_y = pygame.time.get_ticks() * 0.5
        shader_surf = shader_bg.render(camera=(cam_x, cam_y))
        
        # On redimensionne le shader pour remplir l'écran (crée une nouvelle surface)
        scaled_bg = pygame.transform.scale(shader_surf, (WIDTH, HEIGHT))
        # Puis on l'affiche
        screen.blit(scaled_bg, (0, 0))
        
        #screen.blit(BACKGROUND_DIM, (0, 0)) # Ancienne image désactivée
        if active_menu:
            active_menu.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)

def splash_screen():
    if not os.path.exists(USER_PREFS_FILE):
        save_user_prefs()  # Crée un fichier de préférences par défaut s'il n'existe pas
    else :
        load_user_prefs() 
    for menu in lst_menu:
        menu.rebuild()
    logo = pygame.image.load("logo.png").convert_alpha()
    lw, lh = logo.get_size()

    scale = min(WIDTH / lw, HEIGHT / lh)
    new_size = (int(lw * scale), int(lh * scale))
    logo = pygame.transform.smoothscale(logo, new_size)

    logo_x = (WIDTH - new_size[0]) // 2
    logo_y = (HEIGHT - new_size[1]) // 2

    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.fill((0, 0, 0))
    for alpha in range(255, -1, -5):
        overlay.set_alpha(alpha)
        screen.fill((0, 0, 0))
        screen.blit(logo, (logo_x, logo_y))
        screen.blit(overlay, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    start = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start < 2000:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.fill((0, 0, 0))
        screen.blit(logo, (logo_x, logo_y))
        pygame.display.flip()

    for alpha in range(0, 255, 5):
        overlay.set_alpha(alpha)
        screen.fill((0, 0, 0))
        screen.blit(logo, (logo_x, logo_y))
        screen.blit(overlay, (0, 0))
        pygame.display.flip()
        clock.tick(60)

splash_screen()
main() 



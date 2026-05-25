import os
os.environ['SDL_VIDEO_CENTERED'] = '1'
import sys
import subprocess
import atexit
import socket
import ipaddress
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
BUTTON_COLOR = (0, 0, 0)
BUTTON_HOVER = (20, 20, 20)
TEXT_COLOR = (255, 255, 255)
FONT_NAME = None
FONT_SIZE = 36

CONTROLS = {
    "LEFT": pygame.K_q,
    "RIGHT": pygame.K_d,
    "JUMP": pygame.K_SPACE,
    "DASH": pygame.K_LSHIFT,
    "CHANGE ARM": pygame.K_TAB,
    "UP": pygame.K_z,
    "DOWN": pygame.K_s,
    "ATTACK": pygame.K_f
}

DATA = {
    "controls": CONTROLS,
    "graphics": [WIDTH, HEIGHT],
    "fps": FPS
}

USER_PREFS_FILE = "user_prefs.json"

wait_key = False
action_changing = None
server_process = None


def app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_server_exe():
    base_dir = app_dir()
    candidates = [
        os.path.join(base_dir, "Onigiri_server.exe"),
        os.path.abspath(os.path.join(base_dir, "..", "ServerBuild", "Onigiri_server.exe")),
        os.path.abspath(os.path.join(base_dir, "..", "..", "ServerBuild", "Onigiri_server.exe")),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def get_private_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def parse_network_target(host_text, fallback_port):
    host_text = host_text.strip()

    if host_text.count(":") == 1:
        host, port_text = host_text.rsplit(":", 1)
        if host and port_text.isdigit():
            return host, int(port_text)

    return host_text, fallback_port


def should_enable_upnp(host):
    try:
        address = ipaddress.ip_address(host)
        return not (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_unspecified
        )
    except ValueError:
        return False


def reset_user_prefs():
    global CONTROLS, WIDTH, HEIGHT, FPS

    CONTROLS = {
        "LEFT": pygame.K_q,
        "RIGHT": pygame.K_d,
        "JUMP": pygame.K_SPACE,
        "DASH": pygame.K_LSHIFT,
        "CHANGE ARM": pygame.K_TAB,
        "UP": pygame.K_z,
        "DOWN": pygame.K_s,
        "ATTACK": pygame.K_f
    }

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
pygame.display.set_caption("Onigiri Menu")

clock = pygame.time.Clock()
font = pygame.font.Font(FONT_NAME, FONT_SIZE)

ctx = moderngl.create_standalone_context()

limit_res = (320, 180)
limit_surface = pygame.Surface(limit_res)

shader_bg = ShaderBackground(
    limit_res[0],
    limit_res[1],
    "data/shaders/2.8sky.frag",
    ctx=ctx
)

BACKGROUND = pygame.image.load(
    "data/images/menuImage/Background/backgroundtemp.png"
).convert()

BACKGROUND_DIM = pygame.transform.smoothscale(
    BACKGROUND,
    (WIDTH, HEIGHT)
)


def render_text(text, font, color):
    return font.render(text, True, color)


class Button:
    def __init__(
        self,
        rect,
        text,
        callback,
        font,
        color=BUTTON_COLOR,
        hover_color=BUTTON_HOVER,
        text_color=TEXT_COLOR
    ):
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
        self.label = render_text(
            self.text,
            self.font,
            self.text_color
        )

        self.label_rect = self.label.get_rect(
            center=self.rect.center
        )

    def draw(self, surface):
        color = self.hover_color if self.hovered else self.color

        pygame.draw.rect(
            surface,
            color,
            self.rect,
            border_radius=8
        )

        surface.blit(self.label, self.label_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if callable(self.callback):
                    self.callback()


class InputButton(Button):
    def __init__(
        self,
        rect,
        text,
        font,
        color=BUTTON_COLOR,
        hover_color=BUTTON_HOVER,
        text_color=TEXT_COLOR
    ):
        super().__init__(
            rect,
            text,
            None,
            font,
            color,
            hover_color,
            text_color
        )

        self.active = False
        self.input_text = text

    def draw(self, surface):
        color = self.hover_color if self.active or self.hovered else self.color

        pygame.draw.rect(
            surface,
            color,
            self.rect,
            border_radius=8
        )

        display_text = self.input_text

        if self.active and (pygame.time.get_ticks() // 500) % 2 == 0:
            display_text += "|"

        label = render_text(
            display_text,
            self.font,
            self.text_color
        )

        label_rect = label.get_rect(
            center=self.rect.center
        )

        surface.blit(label, label_rect)

    def handle_event(self, event):
        super().handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)

        if self.active and event.type == pygame.KEYDOWN:

            if event.key == pygame.K_RETURN:
                self.active = False

            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]

            else:
                if len(self.input_text) < 32 and event.unicode.isprintable():
                    self.input_text += event.unicode


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

        button_w = 400
        button_h = 60

        total_h = (
            len(items) * button_h +
            (len(items) - 1) * self.spacing
        )

        start_y = (HEIGHT - total_h) // 2
        x = (WIDTH - button_w) // 2

        for i, item in enumerate(items):

            y = start_y + i * (button_h + self.spacing)

            rect = (x, y, button_w, button_h)

            if isinstance(item, Button):

                item.rect = pygame.Rect(rect)

                if hasattr(item, '_render_label'):
                    item._render_label()

                self.items.append(item)

            elif isinstance(item, tuple):

                text, callback = item

                display_text = text() if callable(text) else text

                btn = Button(
                    rect,
                    display_text,
                    callback,
                    self.font
                )

                self.items.append(btn)

    def draw(self, surface):

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))

        surface.blit(overlay, (0, 0))

        title_font = pygame.font.Font(
            FONT_NAME,
            FONT_SIZE + 10
        )

        title_surf = title_font.render(
            self.title,
            True,
            TEXT_COLOR
        )

        title_rect = title_surf.get_rect(
            center=(WIDTH // 2, HEIGHT * 0.2)
        )

        surface.blit(title_surf, title_rect)

        for i, btn in enumerate(self.items):

            btn.hovered = (i == self.selected)

            btn.draw(surface)

    def handle_event(self, event):

        for btn in self.items:
            btn.handle_event(event)

        if not any(
            isinstance(b, InputButton) and b.active
            for b in self.items
        ):

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_DOWN:
                    self.selected = (
                        self.selected + 1
                    ) % len(self.items)

                elif event.key == pygame.K_UP:
                    self.selected = (
                        self.selected - 1
                    ) % len(self.items)

                elif event.key in (
                    pygame.K_RETURN,
                    pygame.K_KP_ENTER
                ):

                    selected_btn = self.items[self.selected]

                    if (
                        hasattr(selected_btn, 'callback')
                        and callable(selected_btn.callback)
                    ):
                        selected_btn.callback()


def start_game(ip="127.0.0.1", port=5005):

    game = Game(
        FPS,
        [WIDTH, HEIGHT],
        ip=ip,
        port=port
    )

    update_user_prefs()
    save_user_prefs()

    game.run()

    global screen

    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT),
        pygame.RESIZABLE
    )


def open_options():
    global active_menu
    active_menu = options_menu


def quit_game():

    update_user_prefs()
    save_user_prefs()

    pygame.quit()
    sys.exit()


def cleanup_server():
    global server_process

    if server_process and server_process.poll() is None:
        server_process.terminate()
        server_process = None

    if sys.platform == "win32":

        try:
            subprocess.run(
                [
                    'taskkill',
                    '/F',
                    '/FI',
                    'WINDOWTITLE eq Onigiri Server*',
                    '/T'
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        except:
            pass


atexit.register(cleanup_server)


def resize(new_width, new_height):

    global WIDTH, HEIGHT, screen

    WIDTH, HEIGHT = new_width, new_height

    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT),
        pygame.RESIZABLE
    )

    for menu in lst_menu:
        menu.rebuild()

    update_user_prefs()


def rebinding(action):

    global wait_key, action_changing

    wait_key = True
    action_changing = action


def refps(fps_value):

    global FPS

    FPS = fps_value

    update_user_prefs()


def refresh_servers():

    global server_menu

    items = []

    servers = LobbyManager.get_server_list()

    if not servers:

        items.append(("No servers found", None))

    else:

        for s in servers:

            label = f"{s.get('name', 'Unknown')} ({s.get('ip')}:{s.get('port', 5005)})"

            action = lambda s=s: start_game(
                s.get("ip"),
                int(s.get("port", 5005))
            )

            items.append((label, action))

    items.append(("Refresh", refresh_servers))

    items.append((
        "Direct Connect",
        lambda: set_active_menu(direct_connect_menu)
    ))

    items.append((
        "Back",
        lambda: set_active_menu(main_menu)
    ))

    server_menu.items_data = items
    server_menu.rebuild()


def open_server_browser():
    refresh_servers()
    set_active_menu(server_menu)


server_name_input = InputButton(
    (0, 0, 0, 0),
    "Onigiri Server",
    font
)

host_ip_input = InputButton(
    (0, 0, 0, 0),
    get_private_ip(),
    font
)

host_port_input = InputButton(
    (0, 0, 0, 0),
    "5005",
    font
)

direct_ip_input = InputButton(
    (0, 0, 0, 0),
    "127.0.0.1",
    font
)

direct_port_input = InputButton(
    (0, 0, 0, 0),
    "5005",
    font
)


def direct_connect():

    try:
        port = int(direct_port_input.input_text)

    except:
        port = 5005

    ip, port = parse_network_target(direct_ip_input.input_text, port)

    start_game(ip, port)


def host_game():
    global server_process

    update_user_prefs()
    save_user_prefs()

    import time

    try:
        local_port = int(host_port_input.input_text.strip())
    except:
        local_port = 5005

    advertised_ip, advertised_port = parse_network_target(
        host_ip_input.input_text,
        local_port
    )
    name = server_name_input.input_text.strip()
    bind_ip = "0.0.0.0"
    local_ip = "127.0.0.1"
    start_local = "0" if should_enable_upnp(advertised_ip) else "1"

    print(f"Starting server on {bind_ip}:{local_port}")

    # 👉 ICI on crée le lobby AVANT de lancer le serveur
    lobby = LobbyManager(
        mode="server",
        server_ip=advertised_ip,
        server_port=advertised_port,
        server_name=name
    )

    lobby.start_heartbeat()

    server_path = find_server_exe()
    if not server_path:
        print("Server error: Onigiri_server.exe not found")
        return

    try:
        server_process = subprocess.Popen(
            [server_path, bind_ip, str(local_port), "--start_local", start_local, "--no_lobby"],
            cwd=os.path.dirname(server_path)
        )
        print(f"Launching server on {bind_ip}:{local_port}")
        print(f"Lobby advertised as {advertised_ip}:{advertised_port}")
        if advertised_port != local_port:
            print(f"Tunnel mapping expected: {advertised_port} -> {local_port}")
        if start_local == "0":
            print("Public host mode: UPnP enabled")

        print("Waiting server...")
        time.sleep(2)

        if server_process.poll() is not None:
            print(f"Server error: process exited with code {server_process.returncode}")
            return

        start_game(local_ip, local_port)

    except Exception as e:
        print(f"Server error: {e}")

def open_host_menu():
    set_active_menu(host_menu)


server_menu = Menu(
    "Server Browser",
    [
        ("Loading...", None),
        ("Back", lambda: set_active_menu(main_menu))
    ],
    font
)

host_menu = Menu(
    "Host Game",
    [
        server_name_input,
        host_ip_input,
        host_port_input,
        ("Start Server", host_game),
        ("Back", lambda: set_active_menu(main_menu))
    ],
    font
)

main_menu = Menu(
    "ONIGIRI",
    [
        ("HOST GAME", open_host_menu),
        ("FIND GAME", open_server_browser),
        ("OPTIONS", open_options),
        ("QUIT GAME", quit_game),
    ],
    font
)

direct_connect_menu = Menu(
    "Direct Connect",
    [
        direct_ip_input,
        direct_port_input,
        ("Connect", direct_connect),
        ("Back", lambda: set_active_menu(server_menu))
    ],
    font
)

keyboard_menu = Menu("Keyboard", 
    [(f"Jump : {CONTROLS['JUMP']}",lambda: rebinding("JUMP"))
    ,(f"Change Arm : {CONTROLS['CHANGE ARM']}",lambda: rebinding("ATTACK"))
    ,(f"Dash : {CONTROLS['DASH']}",lambda: rebinding("DODGE"))
    ,(f"left : {CONTROLS['LEFT']}",lambda: rebinding("LEFT"))
    ,(f"Right : {CONTROLS['RIGHT']}",lambda: rebinding("RIGHT"))
    ,("Back", lambda: set_active_menu(options_menu))
    ],
    font
)

graphics_menu = Menu("Graphics",
    [("3840-2160",lambda: resize(3840, 2160)),
     ("2560-1440",lambda: resize(2560, 1440)),
     ("1920-1080",lambda: resize(1920, 1080)),
     ("1680-1050",lambda: resize(1680, 1050)),
     ("1280-720",lambda: resize(1280,720)),
     ("1024-768",lambda: resize(1024,768)),
     ("800-600",lambda: resize(800,600)),
     ("Back", lambda: set_active_menu(options_menu))
     ],
     font
)


fps_menu = Menu("FPS",
                [("30 FPS",lambda: refps(30)),
        ("45 FPS",lambda: refps(45)),
        ("60 FPS",lambda: refps(60)),
        ("120 FPS",lambda: refps(120)),
        ("144 FPS",lambda: refps(144)),
        ("165 FPS",lambda: refps(165)),
        ("180 FPS",lambda: refps(180)),
        ("240 FPS",lambda: refps(240)),
        ("UNCAPPED FPS",lambda: refps(100000000)),
        ("Back", lambda: set_active_menu(options_menu))
    ],
    font
)


options_menu = Menu(
    "Options",
    [
        ("Keyboards",lambda: set_active_menu(keyboard_menu)),
        ("Graphics",lambda: set_active_menu(graphics_menu)),
        ("FPS",lambda: set_active_menu(fps_menu))
        ,("Back", lambda: set_active_menu(main_menu))
    ],
    font
)

lst_menu = [
    main_menu,
    host_menu,
    server_menu,
    direct_connect_menu,
    options_menu,
    keyboard_menu,
    graphics_menu,
    fps_menu
]


def set_active_menu(menu):

    global active_menu, last_menu

    last_menu = active_menu
    active_menu = menu


active_menu = main_menu
last_menu = main_menu


def main():

    if not os.path.exists(USER_PREFS_FILE):
        save_user_prefs()

    else:
        load_user_prefs()

    for menu in lst_menu:
        menu.rebuild()

    while True:

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_ESCAPE
            ):
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

        cam_x = pygame.time.get_ticks() * 0.5
        cam_y = pygame.time.get_ticks() * 0.5

        shader_surf = shader_bg.render(
            camera=(cam_x, cam_y)
        )

        scaled_bg = pygame.transform.scale(
            shader_surf,
            (WIDTH, HEIGHT)
        )

        screen.blit(scaled_bg, (0, 0))

        if active_menu:
            active_menu.draw(screen)

        pygame.display.flip()

        clock.tick(FPS)

def splash_screen():
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

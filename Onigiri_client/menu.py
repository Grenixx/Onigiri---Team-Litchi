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

            label = f"{s.get('name', 'Unknown')} ({s.get('ip')})"

            action = lambda ip=s.get('ip'): start_game(ip)

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
    "0.0.0.0",
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

    ip = direct_ip_input.input_text

    try:
        port = int(direct_port_input.input_text)

    except:
        port = 5005

    start_game(ip, port)


def host_game():

    update_user_prefs()
    save_user_prefs()

    import time

    ip = host_ip_input.input_text

    try:
        port = int(host_port_input.input_text)

    except:
        port = 5005

    print(f"Starting server on {ip}:{port}")

    bat_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '../Onigiri_server/start_server.bat'
        )
    )

    try:

        subprocess.Popen(
            [bat_path, ip, str(port)],
            shell=True
        )

        print("Waiting for server startup...")
        time.sleep(2)

        start_game("127.0.0.1", port)

    except Exception as e:
        print(f"Server error : {e}")


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

options_menu = Menu(
    "Options",
    [
        ("Back", lambda: set_active_menu(main_menu))
    ],
    font
)

lst_menu = [
    main_menu,
    host_menu,
    server_menu,
    direct_connect_menu,
    options_menu
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


main()
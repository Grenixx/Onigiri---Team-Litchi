# controller.py
import pygame

class Controller:
    """
    Classe générique pour gérer toutes les entrées d'une manette avec pygame.
    Supporte :
    - Boutons
    - Sticks analogiques
    - Gâchettes (triggers)
    - Croix directionnelle (D-pad)
    """

    def __init__(self, deadzone=0.25):
        pygame.joystick.init()
        self.deadzone = deadzone
        self.joystick = None

        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"Manette détectée : {self.joystick.get_name()}")
        else:
            print("Aucune manette détectée. (mode clavier actif)")

        # Variables pour les états
        self.axes = []
        self.buttons = []
        self.hats = []

        # Mappage standard Xbox/PlayStation
        self.button_a = False
        self.button_b = False
        self.button_x = False
        self.button_y = False
        self.button_lb = False
        self.button_rb = False
        self.button_back = False
        self.button_start = False
        self.button_ls = False
        self.button_rs = False

        self.left_trigger = 0.0
        self.right_trigger = 0.0

        # Axes du stick gauche et droit
        self.left_stick_x = 0.0
        self.left_stick_y = 0.0
        self.right_stick_x = 0.0
        self.right_stick_y = 0.0

        # Croix directionnelle (D-pad)
        self.dpad_up = False
        self.dpad_down = False
        self.dpad_left = False
        self.dpad_right = False

    def update(self):
        """Met à jour les valeurs de la manette à chaque frame."""
        if not self.joystick:
            return

        # Récupération des axes
        self.axes = [self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())]

        # Stick gauche (axes 0,1)
        self.left_stick_x = self.apply_deadzone(self.axes[0]) if len(self.axes) > 0 else 0.0
        self.left_stick_y = self.apply_deadzone(self.axes[1]) if len(self.axes) > 1 else 0.0

        # Stick droit (axes 3,4 sur la plupart des manettes)
        self.right_stick_x = self.apply_deadzone(self.axes[2]) if len(self.axes) > 2 else 0.0
        self.right_stick_y = self.apply_deadzone(self.axes[3]) if len(self.axes) > 3 else 0.0

        # Gâchettes (axes 4 et 5 ou 2 et 5 selon modèle)
        self.left_trigger = self.get_trigger_value(4)
        self.right_trigger = self.get_trigger_value(5)

        # Boutons
        self.buttons = [self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())]

        # Mapping classique Xbox / DualShock
        self.button_a = self.get_button(0)
        self.button_b = self.get_button(1)
        self.button_x = self.get_button(2)
        self.button_y = self.get_button(3)
        self.button_lb = self.get_button(4)
        self.button_rb = self.get_button(5)
        self.button_back = self.get_button(6)
        self.button_start = self.get_button(7)
        self.button_ls = self.get_button(8)
        self.button_rs = self.get_button(9)

        # D-pad (HAT)
        self.hats = [self.joystick.get_hat(i) for i in range(self.joystick.get_numhats())]
        if len(self.hats) > 0:
            hat_x, hat_y = self.hats[0]
            self.dpad_left = hat_x == -1
            self.dpad_right = hat_x == 1
            self.dpad_up = hat_y == 1
            self.dpad_down = hat_y == -1

    # ---- Helpers ----
    def apply_deadzone(self, value):
        if abs(value) < self.deadzone:
            return 0.0
        return value

    def get_button(self, index):
        if len(self.buttons) > index:
            return self.buttons[index]
        return False

    def get_trigger_value(self, axis_index):
        """Renvoie la valeur normalisée de la gâchette (0 à 1)."""
        if len(self.axes) > axis_index:
            val = self.axes[axis_index]
            return (val + 1) / 2  # convertit -1..1 en 0..1
        return 0.0

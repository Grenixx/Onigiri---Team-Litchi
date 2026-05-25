import json
import time
import urllib.request
import urllib.error
import threading

FIREBASE_URL = "https://onigiri-83780-default-rtdb.europe-west1.firebasedatabase.app/"
LOBBY_PATH = "/lobbies"


def get_public_ip():
    try:
        with urllib.request.urlopen('https://api.ipify.org') as response:
            return response.read().decode('utf-8')
    except Exception:
        return "127.0.0.1"


class LobbyManager:
    """
    - SERVER: envoie son lobby sur Firebase
    - CLIENT: récupère la liste des serveurs
    """

    def __init__(self, mode="client", server_ip="127.0.0.1", server_port=5555, server_name="Game Room"):
        self.mode = mode

        # valeurs choisies par le joueur
        self.server_ip = server_ip
        self.server_port = int(server_port)
        self.server_name = server_name

        self.running = False
        self.my_id = None

    # -----------------------------
    # SERVER SIDE
    # -----------------------------

    def start_heartbeat(self):
        if self.mode != "server":
            return

        print("Démarrage lobby...")

        self.running = True
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def _heartbeat_loop(self):
        while self.running:
            try:
                self._send_beat()
            except Exception as e:
                print(f"Lobby error: {e}")

            time.sleep(5)

        self._remove_lobby()

    def _send_beat(self):
        """
        Sauvegarde EXACTEMENT les données du joueur dans Firebase
        """

        data = {
            "ip": self.server_ip,      # 👈 IP TAPÉE PAR LE JOUEUR
            "port": self.server_port,  # 👈 PORT TAPÉ PAR LE JOUEUR
            "name": self.server_name,
            "last_seen": time.time()
        }

        payload = json.dumps(data).encode("utf-8")

        # CREATE
        if self.my_id is None:
            url = f"{FIREBASE_URL}{LOBBY_PATH}.json"
            req = urllib.request.Request(url, data=payload, method="POST")

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                self.my_id = result["name"]
                print(f"Lobby créé : {self.my_id}")

        # UPDATE
        else:
            url = f"{FIREBASE_URL}{LOBBY_PATH}/{self.my_id}.json"
            req = urllib.request.Request(url, data=payload, method="PUT")

            with urllib.request.urlopen(req):
                pass

    def _remove_lobby(self):
        if not self.my_id:
            return

        try:
            url = f"{FIREBASE_URL}{LOBBY_PATH}/{self.my_id}.json"
            req = urllib.request.Request(url, method="DELETE")
            urllib.request.urlopen(req)
            print("Lobby supprimé")
        except:
            pass

    def stop(self):
        self.running = False
        self._remove_lobby()

    # -----------------------------
    # CLIENT SIDE
    # -----------------------------

    @staticmethod
    def get_server_list():
        try:
            url = f"{FIREBASE_URL}{LOBBY_PATH}.json"
            req = urllib.request.Request(url, method="GET")

            with urllib.request.urlopen(req) as response:
                data = response.read().decode()

                if data == "null":
                    return []

                lobbies = json.loads(data)
                now = time.time()

                active = []

                for _, info in lobbies.items():
                    if "last_seen" in info and now - info["last_seen"] < 15:
                        active.append(info)

                return active

        except Exception as e:
            print("Lobby fetch error:", e)
            return []
import socket
import struct
import threading
import time

class ClientNetwork:
    def __init__(self, server_ip="127.0.0.1", server_port=5005):
        self.server = (server_ip, server_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.05)
        self.id = None
        self.players = {}
        self.enemies = {}
        self.running = True

        self.remote_players = {}
        self.ping = 0.0
        self.map_change_id = None # <--- Nouveau

        # thread de réception
        threading.Thread(target=self.listen, daemon=True).start()

        # thread ping régulier
        threading.Thread(target=self._ping_loop, daemon=True).start()  # <--- Nouveau


    def connect(self):
        print("Connexion au serveur...")
        while self.id is None and self.running:
            try:
                # envoyer le paquet de connexion
                self.sock.sendto(b'\x0A', self.server)
                start_time = time.time()

                while time.time() - start_time < 2:  # attente max 2 secondes
                    try:
                        data, _ = self.sock.recvfrom(4096)
                        if len(data) == 4:
                            self.id = struct.unpack("I", data)[0]
                            print(f"Connected with ID {self.id}")
                            break
                        else:
                            print("Paquet inattendu reçu, en attente du PID...")
                    except socket.timeout:
                        pass

                if self.id is None:
                    print("Timeout, nouvelle tentative de connexion...")
                    time.sleep(0.5)

            except ConnectionResetError:
                print("Serveur injoignable, nouvelle tentative...")
                time.sleep(0.5)

    def listen(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(4096)
                if not data:
                    continue

                msg_type = data[0]

                # --- PONG (Type 9) ---
                if msg_type == 9 and len(data) >= 9:
                    sent_time = struct.unpack("d", data[1:9])[0]
                    self.ping = (time.time() - sent_time) * 1000
                    continue

                # --- WORLD UPDATE (Type 2) ---
                if msg_type == 2:
                    offset = 1
                    if len(data) < offset + 1: continue
                    count = data[offset]
                    offset += 1
                    new_remote_players = {}

                    for _ in range(count):
                        if len(data) >= offset + 37:
                            pid = struct.unpack("I", data[offset:offset+4])[0]
                            x, y, vx, vy = struct.unpack("ffff", data[offset+4:offset+20])
                            action = data[offset+20:offset+35].decode('utf-8').rstrip('\x00')
                            flip = data[offset+35] == 1
                            weapon_id = data[offset+36]
                            new_remote_players[pid] = (x, y, action, flip, weapon_id, vx, vy)
                            offset += 37
                        else:
                            break
                    self.remote_players = new_remote_players

                    if len(data) >= offset + 1:
                        enemy_count = data[offset]
                        offset += 1
                        new_enemies = {}
                        for _ in range(enemy_count):
                            # 13 = Iff? (4+4+4+1)
                            # +15 = taille du state
                            if len(data) >= offset + 28:  # 13 + 15
                                eid, x, y, flip = struct.unpack("Iff?", data[offset:offset+13])
                                state = data[offset+13:offset+28].decode('utf-8').rstrip('\x00')
                                new_enemies[eid] = (x, y, flip, state)
                                offset += 28
                        self.enemies = new_enemies
                    continue

                # --- MAP CHANGE (Type 4) ---
                if msg_type == 4:
                    if len(data) >= 5:
                        map_id = struct.unpack("<I", data[1:5])[0]
                        self.map_change_id = map_id
                    continue

            except socket.timeout:
                pass
            except Exception as e:
                print("Listen error:", e)
                break
            time.sleep(0.01)


    def send_state(self, x, y, action, flip, weapon_id, vx, vy):
        try:
            packet = b'\x00' + struct.pack("ffffBBB", x, y, vx, vy, action, flip, weapon_id)
            self.sock.sendto(packet, self.server)
        except Exception as e:
            print("Send error:", e)


    def remove_enemy(self, eid):
        try:
            packet = b'\x03' + struct.pack("I", eid)
            self.sock.sendto(packet, self.server)
            print(f"Demande suppression du monstre {eid}")
        except Exception as e:
            print("Remove enemy error:", e)

    def damage_enemy(self, eid,damage_number):
        try:
            packet = b'\x08' + struct.pack("III", eid, damage_number, self.id)
            self.sock.sendto(packet, self.server)
            print(f"Demande d'infliger {damage_number} a ce monstre {eid}")
        except Exception as e:
            print("Damage enemy error:", e)

    def send_map_change_request(self):
        try:
            # Type 5: Request Map Change
            packet = b'\x05'
            self.sock.sendto(packet, self.server)
        except Exception as e:
            print("Send map change error:", e)

    def _ping_loop(self):
        """Thread séparé qui envoie périodiquement un ping."""
        while self.running:
            try:
                packet = b'\x09' + struct.pack("d", time.time())
                self.sock.sendto(packet, self.server)
            except Exception:
                pass
            time.sleep(1.0)  # ping toutes les 1 seconde


    def disconnect(self):
        try:
            self.sock.sendto(b'\x01', self.server)
            self.running = False
            self.sock.close()
            print("Disconnected from server.")
        except Exception as e:
            print("Disconnect error:", e)

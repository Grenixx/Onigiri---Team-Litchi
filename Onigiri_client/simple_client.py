import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3)

ip = input("IP du serveur : ")
sock.sendto(b'\x0A', (ip, 24024))
print(f"Paquet envoye vers {ip}:24024")

try:
    data, addr = sock.recvfrom(1024)
    print(f"Reponse reçue de {addr} : {data.hex()}")
except socket.timeout:
    print("Timeout — aucune reponse")
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 24024))
print("Serveur en attente sur port 24024...")

while True:
    data, addr = sock.recvfrom(1024)
    print(f"Recu de {addr} : {data.hex()}")
    sock.sendto(b'\xFF', addr)
    print(f"Reponse envoyee a {addr}")
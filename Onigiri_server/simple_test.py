import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.sendto(b'\x01', ("91.165.254.108", 5005))

print("packet envoyé")
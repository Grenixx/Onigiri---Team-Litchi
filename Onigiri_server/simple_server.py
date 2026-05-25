import socket
import miniupnpc

def init_upnp(port):
    try:
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        ndevices = upnp.discover()
        print(f"[UPnP] {ndevices} device(s) trouve(s)")
        upnp.selectigd()
        print(f"[UPnP] IGD selectionne : {upnp.lanaddr}")
        try:
            upnp.deleteportmapping(port, 'UDP')
        except:
            pass
        result = upnp.addportmapping(port, 'UDP', upnp.lanaddr, port, 'Onigiri Test', '')
        print(f"[UPnP] Mapping result : {result}")
    except Exception as e:
        print(f"[UPnP] Echec : {e}")

init_upnp(24024)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 24024))
print("Serveur en attente sur port 24024...")

while True:
    data, addr = sock.recvfrom(1024)
    print(f"Recu de {addr} : {data.hex()}")
    sock.sendto(b'\xFF', addr)
    print(f"Reponse envoyee a {addr}")
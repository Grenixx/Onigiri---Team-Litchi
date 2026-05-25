==================================================
                ONIGIRI - USER MANUAL
                    Team Litchi
==================================================

Thank you for playing Onigiri.

This document explains how to launch the game,
host a multiplayer session, and compile the project.

==================================================
                MULTIPLAYER CONNECTION
==================================================

Onigiri currently uses a direct connection system
for multiplayer games.

To host a session:

1. Launch the server
2. Open/forward the chosen port on your router
3. Share your public IP address and port with the other player

The client player must then connect using:

PUBLIC_IP:PORT

Example:
123.45.67.89:5000


==================================================
        1. RUNNING THE PRECOMPILED VERSION
==================================================

Inside the Onigiri folder:

1. Start the server:
   ServerBuild/server.exe

2. Start the client:
   ClientBuild/menu.exe


==================================================
          2. RUNNING FROM SOURCE CODE
==================================================

Required Python dependencies:

pip install pygame moderngl numpy miniupnpc screeninfo


Start the server:

Onigiri_server/server.py


Start the client:

Onigiri_client/game.py


==================================================
             BUILDING THE EXECUTABLES
==================================================

To compile the project yourself:

1. Open a terminal at the project root
2. Run:

pyinstaller.bat

The script automatically builds both the server
and the client executables.


==================================================
                    TROUBLESHOOTING
==================================================

If another player cannot connect:

- Verify that the server is running
- Verify that the selected port is forwarded correctly
- Verify that Windows Firewall allows server.exe
- Verify that the public IP address is correct


==================================================
                    TEAM LITCHI
==================================================

Thank you for playing Onigiri.
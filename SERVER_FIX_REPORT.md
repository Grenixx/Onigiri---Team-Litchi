# Onigiri Server Fix Report

## Executive summary

The server failed primarily because local startup imported missing optional dependencies and loaded maps through working-directory-relative paths. The fixes make the local UDP server runnable from source without `miniupnpc` or `pygame`, resolve map paths relative to the server package or PyInstaller resources, and restrict online lobby/UPnP behavior to online mode.

## Files changed

- `Onigiri_server/server.py`
- `Onigiri_server/enemy_manager.py`
- `start_server.bat`
- `start_server_online.bat`
- `pyinstaller.bat`
- `requirements.txt`

## Fixes applied

### Dependency handling

- Removed the top-level `miniupnpc` import from `server.py`.
- Made UPnP import and setup lazy inside `init_upnp()`.
- Removed the unused `pygame` import from `enemy_manager.py`.
- Added `requirements.txt` for reproducible source setup.

Local server startup now uses only the Python standard library plus project files.

### Path handling

- Added a `resource_path()` helper in `server.py`.
- Map paths now resolve from:
  1. PyInstaller `_MEIPASS`, when bundled data exists.
  2. The executable directory, when external data is copied next to the exe.
  3. The `Onigiri_server` source directory.
- Replaced direct `data/maps/...` and `os.listdir("data/maps")` usage with server-owned helper methods.

This allows startup from both:

```bash
python Onigiri_server/server.py
```

and:

```bash
cd Onigiri_server
python server.py
```

### Online mode behavior

- Firebase lobby heartbeat now starts only when `--start_local=0` is used.
- UPnP setup catches all setup failures and logs them instead of terminating the server.

### Runtime robustness

- Empty UDP packets are ignored.
- Malformed damage packets no longer trigger a `struct.unpack()` size error.
- Unexpected per-packet exceptions are logged and the server loop continues.
- Fixed `Blob` creation by passing the required enemy hitbox size to the base `Enemy` constructor.

### Windows launch and build scripts

- `start_server.bat` and `start_server_online.bat` now use `%~dp0`, so they do not depend on the caller's current working directory.
- `pyinstaller.bat` now bundles server `data` with `--add-data "data;data"` for the server executable.

## Validation performed

- Python bytecode compilation passed for server modules.
- Local source startup was validated from the repository root.
- Local source startup was validated from `Onigiri_server`.
- UDP handshake was validated against a local server instance.

## Remaining risks

- Packaged client/server data should still be rebuilt cleanly and verified because the existing `dist` folders contain stale and mismatched map sets.
- Online hosting still depends on router/firewall/NAT behavior. If UPnP fails, the server can run but may not be reachable from outside the LAN without manual UDP port forwarding for port `5005`.
- Client networking still has a possible handshake race because `ClientNetwork` starts its listener thread before `connect()` completes.

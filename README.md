# dwarf3tostellarium
A simple python bridge server allowing to bridge and remote control Dwarf3 smart telescopes with Stellarium.
I created dwarf3tostellarium because due to changes in the latest dwarf3 firmware, the great dwarfium software doesn't work anymore.

Disclaimer: The server is entirely vibe-coded, therefore use with care ^^

---

Server must be on the same WiFi network as the dwarf 3. Usage of server is simple:

python3 server.py IP-ADDESS-DWARF --lat YOUR_LAT --lon YOUR_LON --alt YOUR_ALT

Setting the lattitude/longitude is necessary for dwarf3 as this is normally done via app.
For example, if the dwarf3 is on its standard IP 192.168.88.1 and you're in Berlin:

python3 server.py 192.168.88.1 --lat 52.5200 --lon 13.4050 --alt 34

After starting, you should be able to check the telescope state via browser on http://localhost:5002/api/status or the dashboard at http://localhost:5002 

In case you want to set/change the location at runtime after starting:
  curl -s -X POST http://localhost:5002/api/location \
    -H 'Content-Type: application/json' \-----
    -d '{"lat": 52.5200, "lon": 13.4050, "alt": 34}'-

---
Stellarium Setup

Prerequisites:
- Stellarium 24.x or later with the Telescope Control plugin
- The bridge server running: python3 server.py <DWARF3_IP> --lat <LAT> --lon <LON>

Steps:
  1. Enable the plugin (first time only)
    - Open Stellarium → click the wrench icon (bottom toolbar) → Plugins tab
    - Find Telescope Control in the list → tick Load at startup → click Configure
    - Restart Stellarium
  2. Add the telescope
    - Press F2 (or go to Configuration Window) → Plugins tab → Telescope Control → click Configure
    - Click Add a new telescope
    - Set Name to anything, e.g. Dwarf3
    - Set Telescope controlled by → External software or remote computer
    - Set Host to localhost (or the IP of the machine running the bridge)
    - Set TCP port to 10001 (standard is 10001 or whatever --tcp-port you chose)
    - Leave Start/connect at startup ticked if desired
    - Click OK
  3. Connect
    - In the Telescope Control window, select Dwarf3 → click Connect
    - The status indicator turns green when the bridge accepts the connection
  4. Slew the telescope
    - Click any object in the sky
    - Press Ctrl+1 (or right-click → Slew telescope to → Dwarf3)
    - The bridge logs GOTO → RA … Dec … and the Dwarf3 starts its one-click goto sequence (plate-solve → slew → track)

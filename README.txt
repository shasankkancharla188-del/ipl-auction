IPL AUCTION MULTIPLAYER - STARTER PROJECT

WHAT THIS IS
A working starter website for a 10-person, real-time IPL-style auction.
It includes room codes, 10 franchise seats, player bidding, purse tracking,
squad limits, host controls and CSV player import.

IMPORTANT
The included player pool is a starter sample, NOT a verified complete/current
IPL auction list. Player eligibility and actual auction rosters change by season.
Before a real game, the host should import the agreed player list using players.csv.

RUN ON YOUR LAPTOP (Windows)
1. Install Python 3.10 or newer.
2. Extract this ZIP.
3. Open Command Prompt in this folder.
4. Run: py -m venv .venv
5. Run: .venv\Scripts\activate
6. Run: pip install -r requirements.txt
7. Run: python app.py
8. Open http://127.0.0.1:5000 in Chrome.

TEST WITH FRIENDS ON SAME WI-FI
Use your laptop's local IPv4 address, e.g. http://192.168.1.5:5000.
Allow Python through Windows Firewall if prompted. All phones must be on the
same Wi-Fi. This local setup is for testing, not internet play.

PLAY FROM SEPARATE LOCATIONS
Deploy the project to a Python hosting service that supports persistent
WebSocket connections. Set SECRET_KEY to a private random value. A production
version should use a shared persistent database/Redis and authentication;
this starter keeps rooms in server memory, so rooms reset when the server restarts
and multiple server instances are not supported.

GAME DEFAULTS
10 franchises, ₹120 Cr purse, 25-player squad, maximum 8 overseas players.
Host creates room; all 10 people join, choose different teams, then host starts.
Host confirms SOLD/UNSOLD after bidding. Bidding timer is displayed as a guide;
the host controls closing the player.

CSV FORMAT
name,role,country,base
Player Name,Batter,India,2.0

The sample pool is intentionally small. Upload a complete, verified pool in the
lobby before starting. Use one row per player; base price is in crore.

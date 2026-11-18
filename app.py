from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import csv, io, os, secrets, threading, time

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret")
socketio = SocketIO(app, cors_allowed_origins="*")
ROOMS = {}
LOCK = threading.RLock()

TEAMS = ["CSK","MI","RCB","KKR","SRH","RR","DC","PBKS","GT","LSG"]
PURSE = 120.0
MAX_SQUAD = 25
MAX_OVERSEAS = 8

DEFAULT_PLAYERS = [
    {"name":"Virat Kohli","role":"Batter","country":"India","base":2.0},
    {"name":"Rohit Sharma","role":"Batter","country":"India","base":2.0},
    {"name":"Jasprit Bumrah","role":"Bowler","country":"India","base":2.0},
    {"name":"Suryakumar Yadav","role":"Batter","country":"India","base":2.0},
    {"name":"Hardik Pandya","role":"All-rounder","country":"India","base":2.0},
    {"name":"MS Dhoni","role":"Wicketkeeper","country":"India","base":1.0},
    {"name":"Ravindra Jadeja","role":"All-rounder","country":"India","base":2.0},
    {"name":"Ruturaj Gaikwad","role":"Batter","country":"India","base":2.0},
    {"name":"Shubman Gill","role":"Batter","country":"India","base":2.0},
    {"name":"Rashid Khan","role":"Bowler","country":"Afghanistan","base":2.0},
    {"name":"Jos Buttler","role":"Wicketkeeper","country":"England","base":2.0},
    {"name":"Travis Head","role":"Batter","country":"Australia","base":2.0},
    {"name":"Pat Cummins","role":"Bowler","country":"Australia","base":2.0},
    {"name":"Sunil Narine","role":"All-rounder","country":"West Indies","base":2.0},
    {"name":"Andre Russell","role":"All-rounder","country":"West Indies","base":2.0},
    {"name":"Rinku Singh","role":"Batter","country":"India","base":1.0},
    {"name":"Sanju Samson","role":"Wicketkeeper","country":"India","base":2.0},
    {"name":"Yashasvi Jaiswal","role":"Batter","country":"India","base":2.0},
    {"name":"Rishabh Pant","role":"Wicketkeeper","country":"India","base":2.0},
    {"name":"KL Rahul","role":"Wicketkeeper","country":"India","base":2.0},
    {"name":"Shreyas Iyer","role":"Batter","country":"India","base":2.0},
    {"name":"Arshdeep Singh","role":"Bowler","country":"India","base":2.0},
    {"name":"Nicholas Pooran","role":"Wicketkeeper","country":"West Indies","base":2.0},
    {"name":"Mitchell Starc","role":"Bowler","country":"Australia","base":2.0},
    {"name":"Phil Salt","role":"Wicketkeeper","country":"England","base":1.5},
    {"name":"Axar Patel","role":"All-rounder","country":"India","base":2.0},
    {"name":"Kuldeep Yadav","role":"Bowler","country":"India","base":2.0},
    {"name":"Ishan Kishan","role":"Wicketkeeper","country":"India","base":2.0},
    {"name":"David Miller","role":"Batter","country":"South Africa","base":1.5},
    {"name":"Rachin Ravindra","role":"All-rounder","country":"New Zealand","base":1.5}
]

def new_room(code, host):
    return {
        "code": code, "host": host, "players": [dict(p, id=i, status="upcoming") for i,p in enumerate(DEFAULT_PLAYERS)],
        "index": -1, "teams": {t: {"owner": None, "purse": PURSE, "squad": []} for t in TEAMS},
        "members": {}, "current_bid": None, "bid_team": None, "bid_owner": None,
        "status": "lobby", "timer_end": None, "sold": [], "unsold": []
    }

def public_state(room):
    current = room["players"][room["index"]] if 0 <= room["index"] < len(room["players"]) else None
    return {
        "code": room["code"], "host": room["host"], "members": room["members"],
        "teams": room["teams"], "current": current, "current_bid": room["current_bid"],
        "bid_team": room["bid_team"], "bid_owner": room["bid_owner"],
        "status": room["status"], "timer_end": room["timer_end"],
        "sold_count": len(room["sold"]), "unsold_count": len(room["unsold"]),
        "upcoming": [p for p in room["players"] if p["status"] == "upcoming"][:6],
        "players_total": len(room["players"])
    }

def broadcast(code):
    socketio.emit("state", public_state(ROOMS[code]), to=code)

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("create_room")
def create_room(data):
    name = (data.get("name") or "Host").strip()[:24]
    code = secrets.token_hex(3).upper()
    with LOCK:
        ROOMS[code] = new_room(code, name)
    join_room(code)
    emit("joined", {"code": code, "name": name, "team": None, "host": True})
    broadcast(code)

@socketio.on("join_room")
def join(data):
    code = (data.get("code") or "").upper().strip()
    name = (data.get("name") or "Player").strip()[:24]
    with LOCK:
        room = ROOMS.get(code)
        if not room:
            emit("error_msg", "Room not found. Check the code.")
            return
        if len(room["members"]) >= 10 and request.sid not in room["members"]:
            emit("error_msg", "This room already has 10 players.")
            return
        room["members"][request.sid] = {"name": name, "team": None}
    join_room(code)
    emit("joined", {"code": code, "name": name, "team": None, "host": room["host"] == name})
    broadcast(code)

@socketio.on("select_team")
def select_team(data):
    code, team = data.get("code"), data.get("team")
    with LOCK:
        room = ROOMS.get(code)
        if not room or team not in TEAMS or request.sid not in room["members"]:
            emit("error_msg", "Invalid team selection.")
            return
        if room["status"] != "lobby":
            emit("error_msg", "Team selection is closed.")
            return
        if any(m.get("team") == team for sid,m in room["members"].items() if sid != request.sid):
            emit("error_msg", "That franchise is already taken.")
            return
        room["members"][request.sid]["team"] = team
        room["teams"][team]["owner"] = room["members"][request.sid]["name"]
    broadcast(code)

@socketio.on("start_auction")
def start_auction(data):
    code = data.get("code")
    with LOCK:
        room = ROOMS.get(code)
        if not room or room["host"] != room["members"].get(request.sid, {}).get("name"):
            emit("error_msg", "Only the room host can start the auction.")
            return
        if len(room["members"]) != 10 or any(not m.get("team") for m in room["members"].values()):
            emit("error_msg", "All 10 friends must join and select a different team first.")
            return
        room["status"] = "auction"
        advance_player(room)
    broadcast(code)

def advance_player(room):
    room["index"] += 1
    room["current_bid"] = None
    room["bid_team"] = None
    room["bid_owner"] = None
    room["timer_end"] = None
    if room["index"] >= len(room["players"]):
        room["status"] = "finished"
        return
    p = room["players"][room["index"]]
    p["status"] = "live"
    room["current_bid"] = float(p["base"])
    room["timer_end"] = time.time() + 25

@socketio.on("bid")
def bid(data):
    code = data.get("code")
    with LOCK:
        room = ROOMS.get(code)
        member = room["members"].get(request.sid) if room else None
        if not room or room["status"] != "auction" or not member or not member.get("team"):
            emit("error_msg", "You cannot bid right now.")
            return
        team = member["team"]
        current = room["players"][room["index"]]
        if room["bid_team"] == team:
            emit("error_msg", "You already hold the highest bid.")
            return
        squad = room["teams"][team]["squad"]
        overseas = sum(1 for p in squad if p["country"] != "India")
        if len(squad) >= MAX_SQUAD or (current["country"] != "India" and overseas >= MAX_OVERSEAS):
            emit("error_msg", "Your squad limit does not allow this purchase.")
            return
        minimum = room["current_bid"] + (0.2 if room["current_bid"] < 1 else 0.5)
        amount = round(float(data.get("amount") or minimum), 2)
        if amount < minimum or amount > room["teams"][team]["purse"]:
            emit("error_msg", f"Next valid bid is at least ₹{minimum:.2f} Cr and must fit your purse.")
            return
        room["current_bid"] = amount
        room["bid_team"] = team
        room["bid_owner"] = member["name"]
        room["timer_end"] = time.time() + 15
    broadcast(code)

@socketio.on("host_action")
def host_action(data):
    code, action = data.get("code"), data.get("action")
    with LOCK:
        room = ROOMS.get(code)
        if not room or room["host"] != room["members"].get(request.sid, {}).get("name"):
            emit("error_msg", "Only the host can do that.")
            return
        if action == "sold":
            if room["status"] != "auction": return
            p = room["players"][room["index"]]
            if room["bid_team"]:
                team = room["teams"][room["bid_team"]]
                team["purse"] = round(team["purse"] - room["current_bid"], 2)
                team["squad"].append({**p, "price": room["current_bid"]})
                p["status"] = "sold"
                room["sold"].append(p)
            else:
                p["status"] = "unsold"
                room["unsold"].append(p)
            advance_player(room)
        elif action == "unsold":
            p = room["players"][room["index"]]
            p["status"] = "unsold"
            room["unsold"].append(p)
            advance_player(room)
    broadcast(code)

@socketio.on("upload_players")
def upload_players(data):
    code = data.get("code")
    with LOCK:
        room = ROOMS.get(code)
        if not room or room["host"] != room["members"].get(request.sid, {}).get("name") or room["status"] != "lobby":
            emit("error_msg", "Only the host can upload players before the auction.")
            return
        try:
            rows = list(csv.DictReader(io.StringIO(data.get("csv",""))))
            clean = []
            for r in rows:
                name = (r.get("name") or "").strip()
                if not name: continue
                clean.append({"id":len(clean), "name":name, "role":(r.get("role") or "Player").strip(),
                              "country":(r.get("country") or "India").strip(),
                              "base":float(r.get("base") or 0.2), "status":"upcoming"})
            if not clean: raise ValueError()
            room["players"] = clean
            room["index"] = -1
        except Exception:
            emit("error_msg", "CSV format must have columns: name,role,country,base")
            return
    broadcast(code)

@socketio.on("get_state")
def get_state(data):
    code = data.get("code")
    if code in ROOMS: emit("state", public_state(ROOMS[code]))

@socketio.on("disconnect")
def disconnect():
    # Keep seats reserved if a player temporarily loses connection.
    pass

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), allow_unsafe_werkzeug=True)

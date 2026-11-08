import time
import requests

API = "http://localhost:8008/_matrix/client/v3"
def call(method, path, user=None, body=None):
    headers = {"Authorization": f"Bearer {user['token']}"} if user else {}
    return requests.request(method, API + path, json=body or {}, headers=headers)

def register(name):
    j = call("POST", "/register", body={"username": name, "password": "pw", "auth": {"type": "m.login.dummy"}}).json()
    return {"id": j["user_id"], "token": j["access_token"]}
    
suffix = str(int(time.time()))
users = {name: register(name + suffix) for name in ("admin", "bob", "eve")}

def act(room, actor, action, target="bob"):
    body = None if action in ("join", "leave") else {"user_id": users[target]["id"]}
    return call("POST", f"/rooms/{room}/{action}", users[actor], body)

def membership(room):
    r = call("GET", f"/rooms/{room}/state/m.room.member/{users['bob']['id']}", users["admin"])
    return r.json()["membership"] if r.ok else f"none ({r.status_code})"
    
SETUP = {"never": [], "invite": [("admin", "invite")], "join": [("admin", "invite"), ("bob", "join")], "leave": [("admin", "invite"), ("bob", "join"), ("bob", "leave")], "ban": [("admin", "ban")]}
CASES = [("admin", "invite"), ("bob", "join"), ("bob", "leave"), ("admin", "kick"), ("admin", "ban"), ("admin", "unban"), ("eve", "kick"), ("eve", "ban")]
print("preset=private_chat\n")
print("| bob before | actor | action | HTTP | errcode | bob after |")
print("|---|---|---|---|---|---|")
for state, setup in SETUP.items():
    for actor, action in CASES:
        room = call("POST", "/createRoom", users["admin"], {"preset": "private_chat"}).json()["room_id"]
        for step in [("admin", "invite", "eve"), ("eve", "join")] + setup:
            act(room, *step)
        r = act(room, actor, action)
        err = "" if r.ok else r.json().get("errcode", "")
        print(f"| {state} | {actor} | {action} | {r.status_code} | {err} | {membership(room)} |")
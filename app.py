import os,sqlite3,re
from datetime import datetime,timezone
from flask import Flask,request,jsonify,session,send_from_directory
from werkzeug.security import generate_password_hash,check_password_hash
B=os.path.dirname(__file__); DB=os.path.join(B,"blackbox.db")
app=Flask(__name__,static_folder="static");app.secret_key=os.getenv("SECRET_KEY","change-me")
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def init():
 c=db();c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE COLLATE NOCASE,password TEXT,created TEXT);
 CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY,sender INTEGER,receiver INTEGER,status TEXT,created TEXT);
 CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,sender INTEGER,receiver INTEGER,body TEXT,created TEXT);""");c.commit();c.close()
init()
def now():return datetime.now(timezone.utc).isoformat()
def me():
 if not session.get("uid"):return None
 c=db();u=c.execute("SELECT id,username FROM users WHERE id=?",(session["uid"],)).fetchone();c.close();return u
def need():
 u=me()
 return u if u else None
@app.get("/")
def home():return send_from_directory(os.path.join(B,"static"),"index.html")
@app.get("/health")
def health():return {"ok":True}
@app.get("/api/me")
def api_me():
 u=me();return {"user":dict(u) if u else None}
@app.post("/api/register")
def reg():
 d=request.json or {};n=d.get("username","").strip();p=d.get("password","")
 if not re.fullmatch(r"[A-Za-z0-9_]{3,20}",n) or len(p)<8:return jsonify(error="Username: 3–20 letters/numbers/_; password: 8+ characters."),400
 c=db()
 try:c.execute("INSERT INTO users(username,password,created) VALUES(?,?,?)",(n,generate_password_hash(p),now()));c.commit()
 except sqlite3.IntegrityError:c.close();return jsonify(error="Username already taken."),409
 u=c.execute("SELECT id,username FROM users WHERE username=?",(n,)).fetchone();c.close();session["uid"]=u["id"];return {"user":dict(u)}
@app.post("/api/login")
def login():
 d=request.json or {};c=db();u=c.execute("SELECT * FROM users WHERE username=?",(d.get("username","").strip(),)).fetchone();c.close()
 if not u or not check_password_hash(u["password"],d.get("password","")):return jsonify(error="Incorrect username or password."),401
 session["uid"]=u["id"];return {"user":{"id":u["id"],"username":u["username"]}}
@app.post("/api/logout")
def logout():session.clear();return {"ok":True}
@app.get("/api/users")
def users():
 u=need()
 if not u:return jsonify(error="Sign in required"),401
 q=request.args.get("q","").strip();c=db();r=c.execute("SELECT id,username FROM users WHERE username LIKE ? AND id!=? LIMIT 20",(q+"%",u["id"])).fetchall();c.close();return {"users":[dict(x) for x in r]}
@app.get("/api/friends")
def friends():
 u=need()
 if not u:return jsonify(error="Sign in required"),401
 c=db();f=c.execute("""SELECT DISTINCT u.id,u.username FROM users u JOIN requests r ON u.id=r.sender OR u.id=r.receiver WHERE r.status='accepted' AND (r.sender=? OR r.receiver=?) AND u.id!=?""",(u["id"],u["id"],u["id"])).fetchall()
 inc=c.execute("SELECT r.id,u.id uid,u.username FROM requests r JOIN users u ON u.id=r.sender WHERE r.receiver=? AND r.status='pending'",(u["id"],)).fetchall();c.close();return {"friends":[dict(x) for x in f],"incoming":[dict(x) for x in inc]}
@app.post("/api/friends/request")
def add():
 u=need()
 if not u:return jsonify(error="Sign in required"),401
 n=(request.json or {}).get("username","").strip();c=db();t=c.execute("SELECT id FROM users WHERE username=?",(n,)).fetchone()
 if not t:c.close();return jsonify(error="User not found."),404
 if t["id"]==u["id"]:c.close();return jsonify(error="Cannot add yourself."),400
 x=c.execute("SELECT * FROM requests WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)",(u["id"],t["id"],t["id"],u["id"])).fetchone()
 if x:c.close();return jsonify(error="Request already exists."),409
 c.execute("INSERT INTO requests(sender,receiver,status,created) VALUES(?,?,?,?)",(u["id"],t["id"],"pending",now()));c.commit();c.close();return {"ok":True}
@app.post("/api/friends/respond")
def respond():
 u=need()
 if not u:return jsonify(error="Sign in required"),401
 d=request.json or {};c=db();r=c.execute("SELECT * FROM requests WHERE id=? AND receiver=? AND status='pending'",(d.get("id"),u["id"])).fetchone()
 if not r:c.close();return jsonify(error="Request not found."),404
 if d.get("action")=="accept":c.execute("UPDATE requests SET status='accepted' WHERE id=?",(r["id"],))
 else:c.execute("DELETE FROM requests WHERE id=?",(r["id"],))
 c.commit();c.close();return {"ok":True}
def friends_ok(c,a,b):return c.execute("SELECT 1 FROM requests WHERE status='accepted' AND ((sender=? AND receiver=?) OR (sender=? AND receiver=?))",(a,b,b,a)).fetchone()
@app.route("/api/messages/<int:oid>",methods=["GET","POST"])
def msgs(oid):
 u=need()
 if not u:return jsonify(error="Sign in required"),401
 c=db()
 if not friends_ok(c,u["id"],oid):c.close();return jsonify(error="Friends only."),403
 if request.method=="POST":
  body=(request.json or {}).get("body","").strip()
  if not body or len(body)>2000:c.close();return jsonify(error="Message must be 1–2000 characters."),400
  c.execute("INSERT INTO messages(sender,receiver,body,created) VALUES(?,?,?,?)",(u["id"],oid,body,now()));c.commit();c.close();return {"ok":True}
 r=c.execute("""SELECT m.*,u.username sender_name FROM messages m JOIN users u ON u.id=m.sender WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY m.id""",(u["id"],oid,oid,u["id"])).fetchall();c.close();return {"messages":[dict(x) for x in r]}
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))

import os, sqlite3, secrets, hashlib, hmac, html, json
from datetime import datetime
from contextlib import contextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

app=FastAPI(title="TET RollCall")
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", secrets.token_hex(32)), https_only=os.environ.get("RENDER")=="true", same_site="lax")
DB=os.environ.get("DB_PATH","/tmp/tet-rollcall.sqlite3")
# This prototype must never be mistaken for persistent production storage.
DEMO_MODE=os.environ.get("DEMO_MODE","false").lower()=="true"
ADMIN_PIN=os.environ.get("ADMIN_PIN","")
MEMBER_PIN=os.environ.get("MEMBER_PIN","")
def connect():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with connect() as c:
  c.executescript("""CREATE TABLE IF NOT EXISTS people(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,pin_hash TEXT);
CREATE TABLE IF NOT EXISTS presence(id INTEGER PRIMARY KEY,person_id INTEGER NOT NULL,day TEXT NOT NULL,status TEXT NOT NULL,changed_by TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(person_id,day));
CREATE TABLE IF NOT EXISTS activities(id INTEGER PRIMARY KEY,title TEXT NOT NULL,day TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS availability(id INTEGER PRIMARY KEY,activity_id INTEGER NOT NULL,person_id INTEGER NOT NULL,status TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(activity_id,person_id));
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT,action TEXT,detail TEXT,at TEXT);""")
init()
def hash_pin(pin,salt=None):
 salt=salt or secrets.token_hex(16)
 digest=hashlib.pbkdf2_hmac("sha256",pin.encode(),bytes.fromhex(salt),250000).hex()
 return salt+":"+digest
def verify_pin(pin,stored):
 try:
  salt,digest=stored.split(":")
  return hmac.compare_digest(hash_pin(pin,salt).split(":")[1],digest)
 except (ValueError,AttributeError):return False
def now():return datetime.now().strftime("%Y-%m-%d %H:%M")
def esc(x):return html.escape(str(x),quote=True)
def auth(req):return req.session.get("role")
def csrf(req):return req.session.setdefault("csrf",secrets.token_urlsafe(24))
@app.middleware("http")
async def protect_posts(req,call_next):
 if req.method=="POST" and req.url.path!="/login":
  from fastapi.responses import PlainTextResponse
  token=(await req.form()).get("csrf","")
  if not req.session.get("csrf") or not hmac.compare_digest(str(token),req.session["csrf"]):
   return PlainTextResponse("Invalid request token",status_code=403)
 return await call_next(req)
def log(c,actor,action,detail):c.execute("INSERT INTO audit(actor,action,detail,at) VALUES(?,?,?,?)",(actor,action,detail,now()))
def page(req,title,body):
 role=auth(req)
 theme=req.cookies.get("theme","dark")
 return HTMLResponse("""<!doctype html><html lang="el"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TET • """+esc(title)+"""</title><style>
:root{font-family:system-ui,-apple-system,sans-serif}body{margin:0;background:#0c1425;color:#e9f2ff}body.light{background:#f3f6fb;color:#1a2841}header{display:flex;align-items:center;justify-content:space-between;padding:16px 5%;background:#13213a}body.light header{background:#fff}a{color:#72d4b1;text-decoration:none}nav{display:flex;gap:16px;flex-wrap:wrap}main{max-width:1080px;margin:24px auto;padding:0 16px}.panel{background:#172640;border:1px solid #30445e;border-radius:16px;padding:20px;margin:16px 0}body.light .panel{background:#fff;border-color:#dae3ef}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.stat{font-size:30px;font-weight:750;color:#6fe2b1}input,select,button{font:inherit;padding:11px;border-radius:9px;border:1px solid #63738b;margin:4px;background:#eef5ff;color:#15233a}button{background:#27b58a;color:#fff;border:0;font-weight:700;cursor:pointer}button.alt{background:#486384}table{border-collapse:collapse;width:100%}td,th{text-align:left;border-bottom:1px solid #516077;padding:10px}small,.muted{opacity:.72}.wrap{overflow:auto}.tag{border-radius:20px;padding:4px 9px;background:#30445e;color:#fff}form.inline{display:inline-flex;flex-wrap:wrap;gap:5px;align-items:center}h1{font-size:26px}h2{font-size:19px}</style><body class='"""+("light" if theme=="light" else "")+"""'><header><strong>🟢 TET | Παρουσιολόγιο</strong><nav><a href="/">Αρχική</a>"""+("""<a href="/people">Μέλη</a><a href="/history">Ιστορικό</a>""" if role=="admin" else "")+"""<a href="/theme">☼ / ☾</a>"""+("""<a href="/logout">Έξοδος</a>""" if role else "")+"""</nav></header><main><h1>"""+esc(title)+"""</h1>"""+body+"""<script>document.querySelectorAll("form[method=post]").forEach(f=>{if(f.action.endsWith("/login"))return;let i=document.createElement("input");i.type="hidden";i.name="csrf";i.value="""+json.dumps(csrf(req))+""";f.appendChild(i)})</script><p class="muted"><small>ΤΕΤ • Οι δηλώσεις διαθεσιμότητας δεν καταχωρίζονται ως παρουσίες.</small></p></main></body></html>""")
def go(path="/"):return RedirectResponse(path,status_code=303)
@app.get("/login")
def login_page(req:Request):
 with connect() as c:
  people=c.execute("SELECT id,name FROM people ORDER BY name").fetchall()
 opts=''.join('<option value="'+str(p["id"])+'">'+esc(p["name"])+'</option>' for p in people)
 return page(req,"Είσοδος",'<div class="panel"><form method="post" action="/login"><label>Ρόλος <select name="role"><option value="member">Μέλος</option><option value="admin">Υπεύθυνος</option></select></label><label>Μέλος (για είσοδο μέλους) <select name="person_id"><option value="0">—</option>'+opts+'</select></label><label>Κωδικός <input type="password" name="pin" required></label><button>Είσοδος</button></form></div>')
@app.post("/login")
def login(req:Request,role:str=Form(...),pin:str=Form(...),person_id:int=Form(0)):
 if role=="admin":
  if not ADMIN_PIN or not hmac.compare_digest(pin,ADMIN_PIN):return HTMLResponse("Λανθασμένος κωδικός.",status_code=403)
  req.session.clear();req.session["role"]="admin";return go()
 if role!="member":return HTMLResponse("Invalid role",400)
 with connect() as c:person=c.execute("SELECT pin_hash FROM people WHERE id=?",(person_id,)).fetchone()
 if not person or not verify_pin(pin,person["pin_hash"]):return HTMLResponse("Λανθασμένος κωδικός.",status_code=403)
 req.session.clear();req.session.update({"role":"member","person_id":person_id});return go()
@app.get("/logout")
def logout(req:Request):req.session.clear();return go("/login")
@app.get("/theme")
def theme(req:Request):
 r=go(req.headers.get("referer","/"));r.set_cookie("theme","light" if req.cookies.get("theme")!="light" else "dark",max_age=31536000,samesite="lax");return r
@app.get("/")
def home(req:Request):
 role=auth(req)
 if not role:return go("/login")
 with connect() as c:
  people=c.execute("SELECT * FROM people ORDER BY name").fetchall()
  pres=c.execute("SELECT p.*,people.name FROM presence p JOIN people ON people.id=p.person_id WHERE day=? ORDER BY people.name",(datetime.now().strftime("%Y-%m-%d"),)).fetchall()
  acts=c.execute("SELECT * FROM activities ORDER BY id DESC").fetchall()
  counts=c.execute("SELECT activity_id,status,COUNT(*) n FROM availability GROUP BY activity_id,status").fetchall()
  summary={(r["activity_id"],r["status"]):r["n"] for r in counts}
 body='<div class="grid"><div class="panel"><div class="stat">'+str(len(people))+'</div>Μέλη ΤΕΤ</div><div class="panel"><div class="stat">'+str(sum(r["status"]=="Παρών" for r in pres))+'</div>Παρόντες σήμερα</div><div class="panel"><div class="stat">'+str(sum(a["active"] for a in acts))+'</div>Ανοιχτές διαθεσιμότητες</div></div>'
 if role=="admin":
  body+='<div class="panel"><h2>Καταχώριση παρουσίας</h2><form method="post" action="/presence"><select name="person_id" required>'+''.join('<option value="'+str(p["id"])+'">'+esc(p["name"])+'</option>' for p in people)+'</select><select name="status"><option>Παρών</option><option>Απών</option></select><button>Αποθήκευση / Επεξεργασία</button></form><h2>Σημερινές παρουσίες</h2><div class="wrap"><table><tr><th>Μέλος</th><th>Κατάσταση</th><th>Τελευταία αλλαγή</th></tr>'+''.join('<tr><td>'+esc(r["name"])+'</td><td>'+esc(r["status"])+'</td><td>'+esc(r["updated_at"])+'</td></tr>' for r in pres)+'</table></div></div>'
  body+='<div class="panel"><h2>Νέα διαθεσιμότητα</h2><form method="post" action="/activity"><select name="title"><option>Πιθανή κινητοποίηση</option><option>Άσκηση</option><option>Άλλη δραστηριότητα</option></select><input type="date" name="day" required><button>Άνοιγμα</button></form></div>'
 body+='<div class="panel"><h2>Μελλοντικές διαθεσιμότητες</h2>'
 for a in acts:
  body+='<div class="panel"><strong>'+esc(a["title"])+' • '+esc(a["day"])+'</strong> <span class="tag">'+("Ανοιχτή" if a["active"] else "Κλειστή")+'</span><p>Διαθέσιμοι: '+str(summary.get((a["id"],"Διαθέσιμος"),0))+' · Ίσως: '+str(summary.get((a["id"],"Ίσως διαθέσιμος"),0))+' · Μη διαθέσιμοι: '+str(summary.get((a["id"],"Μη διαθέσιμος"),0))+'</p>'
  if a["active"]:
   if role=="member":
    body+='<form method="post" action="/availability"><input type="hidden" name="activity_id" value="'+str(a["id"])+'"><select name="status"><option>Διαθέσιμος</option><option>Ίσως διαθέσιμος</option><option>Μη διαθέσιμος</option></select><button>Δήλωση</button></form>'
   else:body+='<form method="post" action="/close"><input type="hidden" name="activity_id" value="'+str(a["id"])+'"><button class="alt">Κλείσιμο</button></form>'
  body+='</div>'
 body+='</div>'
 return page(req,"Κεντρική εικόνα",body)
@app.get("/people")
def people(req:Request):
 if auth(req)!="admin":return go("/login")
 with connect() as c:rows=c.execute("SELECT * FROM people ORDER BY name").fetchall()
 return page(req,"Μέλη ΤΕΤ",'<div class="panel"><form method="post" action="/people"><input name="name" placeholder="Ονοματεπώνυμο" required maxlength="100"><input name="pin" type="password" minlength="6" placeholder="Προσωπικό PIN (6+ ψηφία)" required><button>Προσθήκη μέλους</button></form><div class="wrap"><table>'+''.join('<tr><td>'+esc(p["name"])+'</td></tr>' for p in rows)+'</table></div></div>')
@app.post("/people")
def addperson(req:Request,name:str=Form(...),pin:str=Form(...)):
 if auth(req)!="admin":return HTMLResponse("Forbidden",403)
 if len(pin)<6 or not pin.isdigit():return HTMLResponse("PIN: τουλάχιστον 6 ψηφία",400)
 with connect() as c:
  try:c.execute("INSERT INTO people(name,pin_hash) VALUES(?,?)",(name.strip(),hash_pin(pin)));log(c,"Υπεύθυνος","Προσθήκη μέλους",name.strip())
  except sqlite3.IntegrityError:pass
 return go("/people")
@app.post("/presence")
def presence(req:Request,person_id:int=Form(...),status:str=Form(...)):
 if auth(req)!="admin":return HTMLResponse("Forbidden",403)
 if status not in ("Παρών","Απών"):return HTMLResponse("Invalid",400)
 with connect() as c:
  c.execute("INSERT INTO presence(person_id,day,status,changed_by,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(person_id,day) DO UPDATE SET status=excluded.status,changed_by=excluded.changed_by,updated_at=excluded.updated_at",(person_id,datetime.now().strftime("%Y-%m-%d"),status,"Υπεύθυνος",now()))
  log(c,"Υπεύθυνος","Παρουσία",f"{person_id}: {status}")
 return go()
@app.post("/activity")
def activity(req:Request,title:str=Form(...),day:str=Form(...)):
 if auth(req)!="admin":return HTMLResponse("Forbidden",403)
 if title not in ("Πιθανή κινητοποίηση","Άσκηση","Άλλη δραστηριότητα"):return HTMLResponse("Invalid",400)
 try:datetime.strptime(day,"%Y-%m-%d")
 except ValueError:return HTMLResponse("Invalid date",400)
 with connect() as c:
  c.execute("INSERT INTO activities(title,day,created_at) VALUES(?,?,?)",(title,day,now()));log(c,"Υπεύθυνος","Άνοιγμα διαθεσιμότητας",title+" "+day)
 return go()
@app.post("/availability")
def availability(req:Request,activity_id:int=Form(...),status:str=Form(...)):
 if auth(req)!="member" or not req.session.get("person_id"):return HTMLResponse("Forbidden",403)
 person_id=req.session["person_id"]
 if status not in ("Διαθέσιμος","Ίσως διαθέσιμος","Μη διαθέσιμος"):return HTMLResponse("Invalid",400)
 with connect() as c:
  a=c.execute("SELECT active FROM activities WHERE id=?",(activity_id,)).fetchone()
  if not a or not a["active"]:return HTMLResponse("Η δήλωση έχει κλείσει",400)
  c.execute("INSERT INTO availability(activity_id,person_id,status,updated_at) VALUES(?,?,?,?) ON CONFLICT(activity_id,person_id) DO UPDATE SET status=excluded.status,updated_at=excluded.updated_at",(activity_id,person_id,status,now()))
  log(c,"Μέλος","Διαθεσιμότητα",f"{activity_id}/{person_id}: {status}")
 return go()
@app.post("/close")
def close(req:Request,activity_id:int=Form(...)):
 if auth(req)!="admin":return HTMLResponse("Forbidden",403)
 with connect() as c:c.execute("UPDATE activities SET active=0 WHERE id=?",(activity_id,));log(c,"Υπεύθυνος","Κλείσιμο διαθεσιμότητας",str(activity_id))
 return go()
@app.get("/history")
def history(req:Request):
 if auth(req)!="admin":return go("/login")
 with connect() as c:rows=c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 250").fetchall()
 return page(req,"Ιστορικό αλλαγών",'<div class="panel wrap"><table><tr><th>Ημερομηνία</th><th>Ενέργεια</th><th>Λεπτομέρειες</th></tr>'+''.join('<tr><td>'+esc(r["at"])+'</td><td>'+esc(r["action"])+'</td><td>'+esc(r["detail"])+'</td></tr>' for r in rows)+'</table></div>')
@app.get("/health")
def health():return {"ok":True}

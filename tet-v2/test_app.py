"""Integration smoke tests for the TET prototype. Run from tet-v2: pytest -q."""
import os
import re
import sys
from pathlib import Path
os.environ["DB_PATH"] = "/tmp/tet-rollcall-pytest.sqlite3"
os.environ["ADMIN_PIN"] = "test-admin-only"
os.environ["SESSION_SECRET"] = "test-session-secret-not-for-production"
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fastapi.testclient import TestClient
import app as tet

def csrf(response):
    m=re.search(r'i.value="([^"]+)"',response.text)
    assert m, "CSRF token not rendered"
    return m.group(1)

def test_admin_member_attendance_availability(tmp_path):
    tet.DB=str(tmp_path/"test.sqlite")
    tet.init()
    with TestClient(tet.app) as admin:
        assert admin.get("/health").json()=={"ok":True}
        assert admin.post("/login",data={"role":"admin","pin":"wrong"}).status_code==403
        assert admin.post("/login",data={"role":"admin","pin":"test-admin-only"}).status_code==200
        p=admin.get("/people")
        assert "Μέλη ΤΕΤ" in p.text
        assert admin.post("/people",data={"name":"Test Member","pin":"123456"}).status_code==422
        assert admin.post("/people",data={"name":"Test Member","pin":"123456","csrf":csrf(p)}).status_code==200
        with tet.connect() as db:
            person=db.execute("SELECT id FROM people WHERE name='Test Member'").fetchone()["id"]
        p=admin.get("/")
        assert admin.post("/presence",data={"person_id":person,"status":"Παρών","csrf":csrf(p)}).status_code==200
        with tet.connect() as db:
            assert db.execute("SELECT status FROM presence WHERE person_id=?",(person,)).fetchone()["status"]=="Παρών"
        p=admin.get("/")
        assert admin.post("/activity",data={"title":"Άσκηση","day":"2027-01-01","csrf":csrf(p)}).status_code==200
        with tet.connect() as db:
            activity=db.execute("SELECT id FROM activities ORDER BY id DESC").fetchone()["id"]
    with TestClient(tet.app) as member:
        assert member.post("/login",data={"role":"member","person_id":person,"pin":"123456"}).status_code==200
        home=member.get("/")
        assert "Άσκηση" in home.text
        assert member.post("/availability",data={"activity_id":activity,"status":"Διαθέσιμος","csrf":csrf(home)}).status_code==200
        assert member.get("/people").status_code==200
        with tet.connect() as db:
            assert db.execute("SELECT status FROM availability WHERE activity_id=? AND person_id=?",(activity,person)).fetchone()["status"]=="Διαθέσιμος"
            assert db.execute("SELECT status FROM presence WHERE person_id=?",(person,)).fetchone()["status"]=="Παρών"

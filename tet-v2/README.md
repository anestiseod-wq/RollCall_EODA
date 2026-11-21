# TET RollCall v2 — development prototype

Separate TET-only application. **Not production ready. Do not enter real personal data.**

## Implemented
- Admin: create member with individual numeric PIN, record/correct daily presence, open/close availability, view history.
- Member: authenticate using their own PIN and submit availability for their own identity only.
- Availability never changes attendance.
- Dark/light theme, responsive layout.
- Password hashing (PBKDF2), signed sessions, CSRF checks on state-changing forms.

## Local launch
```bash
cd tet-v2
python -m venv .venv
pip install -r requirements.txt
export ADMIN_PIN='choose-a-long-unique-admin-secret'
export SESSION_SECRET='choose-a-random-32-plus-character-secret'
uvicorn app:app --reload
```

Windows PowerShell: use `$env:ADMIN_PIN="..."` and `$env:SESSION_SECRET="..."`.

## Known blockers before any real deployment
1. SQLite defaults to /tmp: **data disappears on redeploy/restart** on ephemeral hosting. Replace with managed PostgreSQL, migrations and backups.
2. Admin PIN is shared and no brute-force rate limiting is implemented. Replace with named admin accounts, password/PIN rotation and rate limiting.
3. Member PIN reset, account revocation, admin roster management and robust input validation are not implemented.
4. The member page currently exposes aggregate availability counts; decide if that is intended.
5. The frontend uses inline JS, and browser/automated integration tests have not yet been run.
6. No Render deployment has been completed. Do not expose the app publicly with real member records.

## Workflow
Attendance = actual presence recorded by supervisor.
Availability = forecast for a possible future mobilization, independent of attendance.

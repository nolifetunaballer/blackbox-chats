BLACKBOX CHAT — RENDER READY

Upload this folder to GitHub, then create a Render Web Service from the repo.
Build command: pip install -r requirements.txt
Start command: gunicorn app:app

Open the Render URL and share it. This project includes signup, login, friend requests,
friend lists, direct messages, password hashing, sessions, and polling.

IMPORTANT: SQLite is included for easy testing, but Render web-service storage is not durable.
Use Render Postgres/Supabase/Neon before relying on it for permanent public data.

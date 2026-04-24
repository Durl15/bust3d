import os, json, sqlite3, smtplib, uuid, shutil
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ── Config ──────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
DB_PATH     = BASE_DIR / "data" / "orders.db"
UPLOADS_DIR = BASE_DIR / "uploads"
STATIC_DIR  = BASE_DIR / "static"

OWNER_EMAIL  = os.getenv("OWNER_EMAIL",  "diowaj@gmail.com")
GMAIL_USER   = os.getenv("GMAIL_USER",   "diowaj@gmail.com")
GMAIL_PASS   = os.getenv("GMAIL_PASS",   "")          # App password from env
ADMIN_TOKEN  = os.getenv("ADMIN_TOKEN",  "djbust2026") # Change before deploy
BASE_URL     = os.getenv("BASE_URL",     "http://localhost:8000")

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)`n(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

# ── Database ─────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id          TEXT PRIMARY KEY,
                created_at  TEXT NOT NULL,
                name        TEXT NOT NULL,
                email       TEXT NOT NULL,
                phone       TEXT,
                size        TEXT NOT NULL,
                finish      TEXT NOT NULL,
                notes       TEXT,
                photo_path  TEXT,
                photo_name  TEXT,
                status      TEXT DEFAULT 'Received',
                est_total   TEXT,
                updated_at  TEXT
            )
        """)
        conn.commit()

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="DJ 3D Bust Orders")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Serve uploaded images
@app.get("/uploads/{filename}")
def serve_upload(filename: str):
    path = UPLOADS_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path)

# ── Customer: serve order page ────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def order_page():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return FileResponse(STATIC_DIR / "admin.html")

# ── Customer: submit order ────────────────────────────────────────────────────
SIZES = {
    "small":   {"label": "Small (70×60×100mm)",   "est_hrs": "3–4",  "est_mat": "$8–$12",  "est_total": "$32–$44"},
    "medium":  {"label": "Medium (118×107×150mm)", "est_hrs": "6–8",  "est_mat": "$18–$25", "est_total": "$66–$89"},
    "large":   {"label": "Large (160×140×200mm)",  "est_hrs": "11–14","est_mat": "$30–$40", "est_total": "$118–$152"},
    "display": {"label": "Display (200×180×250mm)","est_hrs": "18–24","est_mat": "$45–$60", "est_total": "$189–$252"},
}

@app.post("/api/order")
async def submit_order(
    name:   str = Form(...),
    email:  str = Form(...),
    phone:  str = Form(""),
    size:   str = Form(...),
    finish: str = Form(...),
    notes:  str = Form(""),
    photo: UploadFile = File(...)
):
    if size not in SIZES:
        raise HTTPException(400, "Invalid size")
    if finish not in ("stone", "white"):
        raise HTTPException(400, "Invalid finish")

    # Validate photo
    ext = Path(photo.filename).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".heic", ".webp"):
        raise HTTPException(400, "Photo must be JPG, PNG, HEIC, or WEBP")

    # Save photo
    order_id   = str(uuid.uuid4())[:8].upper()
    photo_name = f"{order_id}{ext}"
    photo_path = UPLOADS_DIR / photo_name
    with open(photo_path, "wb") as f:
        shutil.copyfileobj(photo.file, f)

    size_info   = SIZES[size]
    now         = datetime.utcnow().isoformat()

    # Store in DB
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO orders
              (id, created_at, name, email, phone, size, finish, notes,
               photo_path, photo_name, status, est_total, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (order_id, now, name, email, phone,
              size_info["label"], finish.capitalize(),
              notes, str(photo_path), photo_name,
              "Received", size_info["est_total"], now))
        conn.commit()

    # Email notification to Don
    try:
        _send_notification(order_id, name, email, phone,
                           size_info, finish, notes, photo_path)
    except Exception as e:
        print(f"Email send failed: {e}")   # Non-fatal — order is still saved

    return JSONResponse({"success": True, "order_id": order_id,
                         "est_total": size_info["est_total"],
                         "est_hrs": size_info["est_hrs"]})

def _send_notification(order_id, name, email, phone, size_info, finish, notes, photo_path):
    if not GMAIL_PASS:
        print("GMAIL_PASS not set — skipping email")
        return

    msg = MIMEMultipart()
    msg["From"]    = GMAIL_USER
    msg["To"]      = OWNER_EMAIL
    msg["Subject"] = f"🖨️ New 3D Bust Order #{order_id} from {name}"

    body = f"""
New order received!

Order ID : {order_id}
Name     : {name}
Email    : {email}
Phone    : {phone or 'not provided'}
Size     : {size_info['label']}
Finish   : {finish.capitalize()}
Est Total: {size_info['est_total']}
Notes    : {notes or 'none'}

Log in to your admin dashboard to manage this order:
{BASE_URL}/admin
    """.strip()

    msg.attach(MIMEText(body, "plain"))

    # Attach photo
    with open(photo_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",
                        f"attachment; filename={photo_path.name}")
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_USER, GMAIL_PASS)
        s.send_message(msg)

# ── Admin: list orders ────────────────────────────────────────────────────────
def require_admin(request: Request):
    token = request.headers.get("X-Admin-Token") or request.query_params.get("token")
    if token != ADMIN_TOKEN:
        raise HTTPException(401, "Unauthorized")

@app.get("/api/orders")
def list_orders(db=Depends(get_db), _=Depends(require_admin)):
    rows = db.execute(
        "SELECT * FROM orders ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]

@app.patch("/api/orders/{order_id}/status")
def update_status(order_id: str, body: dict, db=Depends(get_db), _=Depends(require_admin)):
    valid = ["Received","Modeling","Printing","Ready","Delivered","Cancelled"]
    status = body.get("status")
    if status not in valid:
        raise HTTPException(400, f"Status must be one of {valid}")
    db.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?",
               (status, datetime.utcnow().isoformat(), order_id))
    db.commit()
    return {"ok": True}

@app.delete("/api/orders/{order_id}")
def delete_order(order_id: str, db=Depends(get_db), _=Depends(require_admin)):
    row = db.execute("SELECT photo_name FROM orders WHERE id=?", (order_id,)).fetchone()
    if row and row["photo_name"]:
        p = UPLOADS_DIR / row["photo_name"]
        if p.exists():
            p.unlink()
    db.execute("DELETE FROM orders WHERE id=?", (order_id,))
    db.commit()
    return {"ok": True}

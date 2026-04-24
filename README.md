# DJ 3D Bust Order System

## What's included
- `/static/index.html` — Customer-facing order page (photo upload + form)
- `/static/admin.html` — Admin order tracking dashboard
- `main.py`           — FastAPI backend (orders, photo storage, email alerts)
- `requirements.txt`
- `Procfile`          — Railway deployment

---

## Local Setup (PowerShell)

```powershell
cd C:\Projects\bust3d
pip install -r requirements.txt
$env:GMAIL_PASS = "your-gmail-app-password"
$env:ADMIN_TOKEN = "djbust2026"     # Change this
uvicorn main:app --reload --port 8000
```

Then open:
- Customer page: http://localhost:8000
- Admin dashboard: http://localhost:8000/admin

---

## Environment Variables

| Variable      | Required | Description                                              |
|---------------|----------|----------------------------------------------------------|
| GMAIL_PASS    | Yes      | Gmail App Password (not your regular password)           |
| GMAIL_USER    | No       | Defaults to diowaj@gmail.com                             |
| OWNER_EMAIL   | No       | Defaults to diowaj@gmail.com                             |
| ADMIN_TOKEN   | Yes      | Password for the admin dashboard (change from default)   |
| BASE_URL      | No       | Your deployed URL (for email links)                      |

### Gmail App Password Setup
1. Go to myaccount.google.com → Security → 2-Step Verification → App passwords
2. Create an app password for "Mail"
3. Use that 16-character code as GMAIL_PASS

---

## Deploy to Railway

1. Push this folder to a GitHub repo
2. Go to railway.app → New Project → Deploy from GitHub
3. Set environment variables in Railway dashboard
4. Update flyer QR code with your Railway URL (e.g. bust-orders.up.railway.app)

---

## Admin Dashboard

Visit `/admin` — enter your ADMIN_TOKEN to log in.

Order statuses: **Received → Modeling → Printing → Ready → Delivered**

Auto-refreshes every 60 seconds. Click any customer photo to view full size.

---

## Update Flyer QR Code

After deploying, regenerate the QR to point to your live URL:

```python
import qrcode
qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
qr.add_data("https://YOUR-RAILWAY-URL.up.railway.app")
qr.make(fit=True)
img = qr.make_image()
img.save("qr_order.png")
```

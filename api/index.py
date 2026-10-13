import json
import os
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="BANGOX Update Server")

# ডাটাবেস ফাইল (যেখানে সব ভার্সনের তথ্য সেভ থাকবে)
DB_FILE = os.path.join(os.path.dirname(__file__), "versions.json")

# এডমিন প্যানেলে ঢোকার জন্য সিক্রেট পাসওয়ার্ড
ADMIN_KEY = "bangox123"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "versions": {
            "13.10.2026": {
                "version": "13.10.2026",
                "download_url": "https://your-cloud-storage-link.com/bangox-latest.exe",
                "changelog": "- Added new UI customization\n- Added dynamic SVG icons",
                "enabled": True,
                "timestamp": datetime.now().timestamp()
            }
        }
    }

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

@app.get("/api/update")
def check_update():
    """ডেস্কটপ অ্যাপ এই API তে রিকোয়েস্ট পাঠাবে"""
    data = load_db()
    
    # যেসব ভার্সন 'enabled' আছে, সেগুলো ফিল্টার করা
    active_versions = [v for v in data["versions"].values() if v["enabled"]]
    
    if not active_versions:
        return {"error": "No active versions found."}
        
    # সবচেয়ে লেটেস্ট ভার্সন বের করা (timestamp অনুযায়ী)
    latest = sorted(active_versions, key=lambda x: x["timestamp"], reverse=True)[0]
    
    return {
        "latest_version": latest["version"],
        "download_url": latest["download_url"],
        "changelog": latest["changelog"],
        "mandatory": False
    }

@app.get("/")
def home():
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><title>BANGOX Update Server</title>
    <style>
        body {{ background-color: #000c12; color: #49ff00; font-family: 'Courier New'; text-align: center; padding-top: 50px; }}
        .container {{ border: 1px solid #49ff00; display: inline-block; padding: 40px; border-radius: 8px; background-color: #001218; }}
        a {{ color: #ff6688; text-decoration: none; padding: 10px; border: 1px solid #ff6688; border-radius: 4px; display: inline-block; margin-top: 20px; }}
        a:hover {{ background-color: #ff6688; color: #000; }}
    </style></head>
    <body>
        <div class="container">
            <h1>BANGOX API SERVER</h1>
            <p>System is ONLINE.</p>
            <br>
            <a href="/admin?key={ADMIN_KEY}">Go to Admin Dashboard</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(key: str = ""):
    """এডমিন ড্যাশবোর্ড - যেখানে নতুন ভার্সন এড করা যাবে"""
    if key != ADMIN_KEY:
        return "<h2 style='color:red; text-align:center;'>Access Denied. Wrong Admin Key.</h2>"
        
    data = load_db()
    versions = sorted(data["versions"].values(), key=lambda x: x["timestamp"], reverse=True)
    
    rows = ""
    for v in versions:
        status = "<span style='color:#49ff00;'>Active</span>" if v["enabled"] else "<span style='color:red;'>Disabled</span>"
        btn_text = "Disable" if v["enabled"] else "Enable"
        rows += f"""
        <tr>
            <td>{v['version']}</td>
            <td><a href="{v['download_url']}" target="_blank">Link</a></td>
            <td><pre style="margin:0; font-family:inherit;">{v['changelog']}</pre></td>
            <td>{status}</td>
            <td>
                <form action="/admin/toggle" method="post" style="display:inline;">
                    <input type="hidden" name="key" value="{ADMIN_KEY}">
                    <input type="hidden" name="version" value="{v['version']}">
                    <button type="submit">{btn_text}</button>
                </form>
            </td>
        </tr>
        """
        
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BANGOX Admin Dashboard</title>
        <style>
            body {{ background-color: #000c12; color: #e3e3e3; font-family: 'Courier New'; padding: 20px; }}
            h1, h2 {{ color: #49ff00; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #49ff00; padding: 10px; text-align: left; }}
            th {{ background-color: #001218; }}
            input, textarea, button {{ width: 100%; background: #001218; color: #fff; border: 1px solid #49ff00; padding: 8px; margin-bottom: 10px; font-family: 'Courier New'; }}
            button {{ background: #49ff00; color: #000; font-weight: bold; cursor: pointer; }}
            button:hover {{ background: #fff; }}
            .form-box {{ border: 1px dashed #ff6688; padding: 20px; max-width: 600px; margin-bottom: 30px; }}
        </style>
    </head>
    <body>
        <h1>BANGOX Update Admin Panel</h1>
        
        <div class="form-box">
            <h2>Add New Release</h2>
            <form action="/admin/add" method="post">
                <input type="hidden" name="key" value="{ADMIN_KEY}">
                <label>Version Name (e.g. 14.0.2026):</label>
                <input type="text" name="version" required>
                
                <label>Download URL (Google Drive / MediaFire etc):</label>
                <input type="url" name="download_url" required>
                
                <label>Changelog (What's new?):</label>
                <textarea name="changelog" rows="4" required></textarea>
                
                <button type="submit">Publish Update</button>
            </form>
        </div>

        <h2>Release History</h2>
        <table>
            <tr><th>Version</th><th>Download</th><th>Changelog</th><th>Status</th><th>Action</th></tr>
            {rows}
        </table>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/admin/add")
def add_version(key: str = Form(...), version: str = Form(...), download_url: str = Form(...), changelog: str = Form(...)):
    if key != ADMIN_KEY:
        return "Unauthorized"
        
    data = load_db()
    data["versions"][version] = {
        "version": version,
        "download_url": download_url,
        "changelog": changelog,
        "enabled": True,
        "timestamp": datetime.now().timestamp()
    }
    save_db(data)
    return RedirectResponse(url=f"/admin?key={ADMIN_KEY}", status_code=303)

@app.post("/admin/toggle")
def toggle_version(key: str = Form(...), version: str = Form(...)):
    if key != ADMIN_KEY:
        return "Unauthorized"
        
    data = load_db()
    if version in data["versions"]:
        data["versions"][version]["enabled"] = not data["versions"][version]["enabled"]
        save_db(data)
        
    return RedirectResponse(url=f"/admin?key={ADMIN_KEY}", status_code=303)
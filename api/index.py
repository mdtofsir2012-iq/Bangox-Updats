import json
import os
from datetime import datetime
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

import requests

app = FastAPI(title="BANGOX Update Server")

# এডমিন প্যানেলে ঢোকার জন্য সিক্রেট পাসওয়ার্ড
ADMIN_KEY = "bangox123"

# Firebase Config (REST API)
PROJECT_ID = "bangox-updates"
API_KEY = "AIzaSyCfNNRZmN7I4zcq_8964SQ5ptAAcJOdGZ8"
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/Updates"

def load_db():
    try:
        url = f"{FIRESTORE_URL}?key={API_KEY}"
        resp = requests.get(url)
        data = resp.json()
        
        versions = {}
        if "documents" in data:
            for doc in data["documents"]:
                doc_path = doc.get("name", "")
                doc_id = doc_path.split("/")[-1] # example: updates_1
                
                fields = doc.get("fields", {})
                v_name = fields.get("version", {}).get("stringValue", "")
                if v_name:
                    versions[v_name] = {
                        "doc_id": doc_id,
                        "version": v_name,
                        "download_url": fields.get("download_url", {}).get("stringValue", ""),
                        "changelog": fields.get("changelog", {}).get("stringValue", ""),
                        "enabled": fields.get("enabled", {}).get("booleanValue", True),
                        "timestamp": fields.get("timestamp", {}).get("doubleValue", 0.0)
                    }
        return {"versions": versions}
    except Exception as e:
        print("Error loading from Firestore:", e)
        return {"versions": {}}

def save_version(v_data):
    try:
        doc_id = v_data.get("doc_id")
        if not doc_id:
            return
            
        url = f"{FIRESTORE_URL}/{doc_id}?key={API_KEY}"
        payload = {
            "fields": {
                "version": {"stringValue": str(v_data["version"])},
                "download_url": {"stringValue": str(v_data["download_url"])},
                "changelog": {"stringValue": str(v_data["changelog"])},
                "enabled": {"booleanValue": bool(v_data["enabled"])},
                "timestamp": {"doubleValue": float(v_data["timestamp"])}
            }
        }
        # PATCH creates or updates the document
        requests.patch(url, json=payload)
    except Exception as e:
        print("Error saving to Firestore:", e)

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
    
    import base64
    rows = ""
    for v in versions:
        status = "<span style='color:#49ff00;'>Active</span>" if v["enabled"] else "<span style='color:red;'>Disabled</span>"
        btn_text = "Disable" if v["enabled"] else "Enable"
        
        # Base64 encode the changelog so it doesn't break JS quotes/newlines
        b64_changelog = base64.b64encode(v['changelog'].encode('utf-8')).decode('utf-8')
        
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
                <button type="button" style="background:#ff6688;" onclick="editVersion('{v['version']}', '{v['download_url']}', '{b64_changelog}')">Edit</button>
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
            input, textarea, button {{ width: 100%; background: #001218; color: #fff; border: 1px solid #49ff00; padding: 8px; margin-bottom: 10px; font-family: 'Courier New'; box-sizing: border-box; }}
            button {{ background: #49ff00; color: #000; font-weight: bold; cursor: pointer; width: auto; padding: 8px 15px; margin-right: 5px; }}
            button:hover {{ background: #fff; }}
            .form-box {{ border: 1px dashed #ff6688; padding: 20px; max-width: 600px; margin-bottom: 30px; position: relative; }}
        </style>
        <script>
            function editVersion(version, url, b64_changelog) {{
                document.getElementById('form-title').innerText = 'Edit Release: ' + version;
                document.getElementById('version-input').value = version;
                document.getElementById('version-input').readOnly = true; 
                document.getElementById('url-input').value = url;
                document.getElementById('changelog-input').value = decodeURIComponent(escape(window.atob(b64_changelog)));
                document.getElementById('submit-btn').innerText = 'Save Changes';
                document.getElementById('cancel-btn').style.display = 'inline-block';
                window.scrollTo(0, 0);
            }}
            function resetForm() {{
                document.getElementById('form-title').innerText = 'Add New Release';
                document.getElementById('version-input').value = '';
                document.getElementById('version-input').readOnly = false;
                document.getElementById('url-input').value = '';
                document.getElementById('changelog-input').value = '';
                document.getElementById('submit-btn').innerText = 'Publish Update';
                document.getElementById('cancel-btn').style.display = 'none';
            }}
        </script>
    </head>
    <body>
        <h1>BANGOX Update Admin Panel</h1>
        
        <div class="form-box">
            <h2 id="form-title">Add New Release</h2>
            <form action="/admin/add" method="post">
                <input type="hidden" name="key" value="{ADMIN_KEY}">
                <label>Version Name (e.g. 14.0.2026):</label>
                <input type="text" id="version-input" name="version" required>
                
                <label>Download URL (Google Drive / MediaFire etc):</label>
                <input type="url" id="url-input" name="download_url" required>
                
                <label>Changelog (What's new?):</label>
                <textarea id="changelog-input" name="changelog" rows="4" required></textarea>
                
                <button type="submit" id="submit-btn">Publish Update</button>
                <button type="button" id="cancel-btn" style="display:none; background:#ff6688;" onclick="resetForm()">Cancel</button>
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
    
    if version in data["versions"]:
        # Update existing version (preserves 'enabled' status and 'timestamp')
        v_data = data["versions"][version]
        v_data["download_url"] = download_url
        v_data["changelog"] = changelog
    else:
        # Calculate next doc_id (e.g. updates_1, updates_2)
        existing_ids = [v.get("doc_id", "") for v in data["versions"].values()]
        max_id = 0
        for eid in existing_ids:
            if eid.startswith("updates_"):
                try:
                    num = int(eid.split("_")[1])
                    if num > max_id:
                        max_id = num
                except:
                    pass
        next_doc_id = f"updates_{max_id + 1}"
        
        # Add new version
        v_data = {
            "doc_id": next_doc_id,
            "version": version,
            "download_url": download_url,
            "changelog": changelog,
            "enabled": True,
            "timestamp": datetime.now().timestamp()
        }
        
    save_version(v_data)
    return RedirectResponse(url=f"/admin?key={ADMIN_KEY}", status_code=303)

@app.post("/admin/toggle")
def toggle_version(key: str = Form(...), version: str = Form(...)):
    if key != ADMIN_KEY:
        return "Unauthorized"
        
    data = load_db()
    if version in data["versions"]:
        v_data = data["versions"][version]
        v_data["enabled"] = not v_data["enabled"]
        save_version(v_data)
        
    return RedirectResponse(url=f"/admin?key={ADMIN_KEY}", status_code=303)

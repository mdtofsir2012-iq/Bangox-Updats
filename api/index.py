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
                        "icon_url": fields.get("icon_url", {}).get("stringValue", ""),
                        "mandatory": fields.get("mandatory", {}).get("booleanValue", False),
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
                "icon_url": {"stringValue": str(v_data.get("icon_url", ""))},
                "mandatory": {"booleanValue": bool(v_data.get("mandatory", False))},
                "enabled": {"booleanValue": bool(v_data["enabled"])},
                "timestamp": {"doubleValue": float(v_data["timestamp"])}
            }
        }
        requests.patch(url, json=payload)
    except Exception as e:
        print("Error saving to Firestore:", e)

def delete_version_from_db(doc_id):
    try:
        url = f"{FIRESTORE_URL}/{doc_id}?key={API_KEY}"
        requests.delete(url)
    except Exception as e:
        print("Error deleting from Firestore:", e)

@app.get("/api/update")
def check_update():
    """ডেস্কটপ অ্যাপ এই API তে রিকোয়েস্ট পাঠাবে"""
    data = load_db()
    
    active_versions = [v for v in data["versions"].values() if v["enabled"]]
    
    if not active_versions:
        return {"error": "No active versions found."}
        
    latest = sorted(active_versions, key=lambda x: x["timestamp"], reverse=True)[0]
    
    return {
        "latest_version": latest["version"],
        "download_url": latest["download_url"],
        "changelog": latest["changelog"],
        "icon_url": latest.get("icon_url", ""),
        "mandatory": latest.get("mandatory", False)
    }

@app.get("/api/updates/all")
def get_all_updates():
    """সব আপডেট রিটার্ন করবে"""
    data = load_db()
    versions = sorted(data["versions"].values(), key=lambda x: (x["enabled"], x["timestamp"]), reverse=True)
    return {"versions": versions}

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
            <h1>BANGOX UPDATE SERVER</h1>
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
    if key != ADMIN_KEY:
        return "<h2 style='color:red; text-align:center;'>Access Denied. Wrong Admin Key.</h2>"
        
    data = load_db()
    versions = sorted(data["versions"].values(), key=lambda x: x["timestamp"], reverse=True)
    
    import base64
    rows = ""
    for v in versions:
        status = "<span style='color:#49ff00;'>Active</span>" if v["enabled"] else "<span style='color:red;'>Disabled</span>"
        btn_text = "Disable" if v["enabled"] else "Enable"
        mandatory_badge = "<span style='color:#ff6688;'>[Mandatory]</span>" if v.get("mandatory") else ""
        
        b64_old_ver = base64.b64encode(v['version'].encode('utf-8')).decode('utf-8')
        b64_ver = base64.b64encode(v['version'].encode('utf-8')).decode('utf-8')
        b64_url = base64.b64encode(v['download_url'].encode('utf-8')).decode('utf-8')
        b64_icon = base64.b64encode(v.get('icon_url', '').encode('utf-8')).decode('utf-8')
        b64_changelog = base64.b64encode(v['changelog'].encode('utf-8')).decode('utf-8')
        mand_val = 'true' if v.get('mandatory') else 'false'
        
        dt = datetime.fromtimestamp(v['timestamp']).strftime('%Y-%m-%d %H:%M') if v.get('timestamp') else 'N/A'
        
        rows += f"""
        <tr>
            <td><strong>{v.get('icon_url', '')} {v['version']}</strong> {mandatory_badge}<br><small style="color:#888;">{dt}</small></td>
            <td><a href="{v['download_url']}" target="_blank">Download Link</a></td>
            <td><pre style="margin:0; font-family:inherit; white-space: pre-wrap;">{v['changelog']}</pre></td>
            <td>{status}</td>
            <td>
                <form action="/admin/toggle" method="post" style="display:inline;">
                    <input type="hidden" name="key" value="{ADMIN_KEY}">
                    <input type="hidden" name="version" value="{v['version']}">
                    <button type="submit" style="background:#ffaa00; color:#000;">{btn_text}</button>
                </form>
                <button type="button" style="background:#00bcd4; color:#000;" onclick="editVersion('{b64_old_ver}', '{b64_ver}', '{b64_url}', '{b64_icon}', '{b64_changelog}', {mand_val})">Edit</button>
                <form action="/admin/delete" method="post" style="display:inline;" onsubmit="return confirm('Are you sure you want to delete version {v["version"]}?');">
                    <input type="hidden" name="key" value="{ADMIN_KEY}">
                    <input type="hidden" name="version" value="{v['version']}">
                    <button type="submit" style="background:#ff4444; color:#fff;">Delete</button>
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
            th, td {{ border: 1px solid #49ff00; padding: 10px; text-align: left; vertical-align: top; }}
            th {{ background-color: #001218; }}
            input, textarea, button {{ width: 100%; background: #001218; color: #fff; border: 1px solid #49ff00; padding: 8px; margin-bottom: 10px; font-family: 'Courier New'; box-sizing: border-box; }}
            button {{ background: #49ff00; color: #000; font-weight: bold; cursor: pointer; width: auto; padding: 8px 15px; margin-right: 5px; }}
            button:hover {{ background: #fff; }}
            .form-box {{ border: 1px dashed #ff6688; padding: 20px; max-width: 600px; margin-bottom: 30px; position: relative; background: #000f14; }}
            .checkbox-group {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
            .checkbox-group input {{ width: auto; margin: 0; }}
        </style>
        <script>
            function editVersion(b64_old_ver, b64_ver, b64_url, b64_icon, b64_changelog, mandatory) {{
                let old_version = decodeURIComponent(escape(window.atob(b64_old_ver)));
                let version = decodeURIComponent(escape(window.atob(b64_ver)));
                let url = decodeURIComponent(escape(window.atob(b64_url)));
                let icon = decodeURIComponent(escape(window.atob(b64_icon)));
                let changelog = decodeURIComponent(escape(window.atob(b64_changelog)));

                document.getElementById('form-title').innerText = 'Edit Release: ' + version;
                document.getElementById('old-version-input').value = old_version;
                document.getElementById('version-input').value = version;
                document.getElementById('url-input').value = url;
                document.getElementById('icon-input').value = icon;
                document.getElementById('changelog-input').value = changelog;
                document.getElementById('mandatory-input').checked = mandatory;
                document.getElementById('submit-btn').innerText = 'Save Changes';
                document.getElementById('cancel-btn').style.display = 'inline-block';
                window.scrollTo(0, 0);
            }}
            function resetForm() {{
                document.getElementById('form-title').innerText = 'Add New Release';
                document.getElementById('old-version-input').value = '';
                document.getElementById('version-input').value = '';
                document.getElementById('url-input').value = '';
                document.getElementById('icon-input').value = '';
                document.getElementById('changelog-input').value = '';
                document.getElementById('mandatory-input').checked = false;
                document.getElementById('submit-btn').innerText = 'Publish Update';
                document.getElementById('cancel-btn').style.display = 'none';
            }}
        </script>
    </head>
    <body>
        <h1>BANGOX Update Admin Panel</h1>
        
        <div class="form-box">
            <h2 id="form-title">Add New Release</h2>
            <form action="/admin/save" method="post">
                <input type="hidden" name="key" value="{ADMIN_KEY}">
                <input type="hidden" id="old-version-input" name="old_version" value="">
                
                <label>Version Name (e.g. 14.1.2026):</label>
                <input type="text" id="version-input" name="version" required>
                
                <label>Download URL (.exe / Google Drive / Direct link):</label>
                <input type="url" id="url-input" name="download_url" required>

                <label>Update Icon / Emoji (Optional):</label>
                <input type="text" id="icon-input" name="icon_url" placeholder="e.g. 🚀 or https://image-link.com/icon.png">
                
                <label>Changelog (What's new?):</label>
                <textarea id="changelog-input" name="changelog" rows="4" required></textarea>
                
                <div class="checkbox-group">
                    <input type="checkbox" id="mandatory-input" name="mandatory" value="true">
                    <label for="mandatory-input" style="margin:0; cursor:pointer;">Mandatory Update (Force user to update)</label>
                </div>
                
                <button type="submit" id="submit-btn">Publish Update</button>
                <button type="button" id="cancel-btn" style="display:none; background:#ff6688;" onclick="resetForm()">Cancel</button>
            </form>
        </div>

        <h2>Release History</h2>
        <table>
            <tr><th>Version</th><th>Download</th><th>Changelog</th><th>Status</th><th>Actions</th></tr>
            {rows}
        </table>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/admin/save")
def save_release(
    key: str = Form(...),
    old_version: str = Form(""),
    version: str = Form(...),
    download_url: str = Form(...),
    icon_url: str = Form(""),
    changelog: str = Form(...),
    mandatory: str = Form("false")
):
    if key != ADMIN_KEY:
        return "Unauthorized"
        
    data = load_db()
    is_mandatory = mandatory.lower() in ["true", "on", "1"]
    
    # If editing and version name changed, delete old version entry
    if old_version and old_version != version:
        if old_version in data["versions"]:
            old_doc_id = data["versions"][old_version].get("doc_id")
            if old_doc_id:
                delete_version_from_db(old_doc_id)
            del data["versions"][old_version]

    if version in data["versions"]:
        # Update existing version data
        v_data = data["versions"][version]
        v_data["download_url"] = download_url
        v_data["icon_url"] = icon_url
        v_data["changelog"] = changelog
        v_data["mandatory"] = is_mandatory
    else:
        # Create new version
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
            elif eid.isdigit():
                num = int(eid)
                if num > max_id:
                    max_id = num
                    
        next_doc_id = f"updates_{max_id + 1}"
        
        v_data = {
            "doc_id": next_doc_id,
            "version": version,
            "download_url": download_url,
            "icon_url": icon_url,
            "changelog": changelog,
            "mandatory": is_mandatory,
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

@app.post("/admin/delete")
def delete_version(key: str = Form(...), version: str = Form(...)):
    if key != ADMIN_KEY:
        return "Unauthorized"
        
    data = load_db()
    if version in data["versions"]:
        doc_id = data["versions"][version].get("doc_id")
        if doc_id:
            delete_version_from_db(doc_id)
            
    return RedirectResponse(url=f"/admin?key={ADMIN_KEY}", status_code=303)

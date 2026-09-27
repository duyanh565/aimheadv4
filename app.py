from __future__ import annotations

import io
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
BASE_URL = "https://api.nextdns.io"
DOMAIN_RE = re.compile(r"^(?:\*\.)?(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$", re.I)
DEFAULT_TEMPLATE = os.path.join(os.path.dirname(__file__), "ANTIBANDA.mobileconfig")


def error_detail(raw: str) -> str:
    try:
        data = json.loads(raw)
        errors = data.get("errors", [])
        if errors:
            return "; ".join(str(x.get("detail", x)) for x in errors)
        return str(data)
    except (json.JSONDecodeError, AttributeError):
        return raw[:500]


def nextdns(api_key: str, path: str, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    if not api_key or len(api_key) > 300:
        raise ValueError("API key không hợp lệ.")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json", "X-Api-Key": api_key, "User-Agent": "nextdns-railway-manager/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"NextDNS HTTP {exc.code}: {error_detail(exc.read().decode(errors='replace'))}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Không kết nối được NextDNS: {exc.reason}") from None
    try:
        result = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        raise RuntimeError("NextDNS trả về dữ liệu không hợp lệ.") from None
    if result.get("errors"):
        raise RuntimeError(error_detail(raw))
    return result.get("data", result)


def tokens(raw: str) -> list[str]:
    found, seen = [], set()
    for item in re.split(r"[\s,;]+", raw or ""):
        item = item.strip().lower().rstrip(".")
        item = re.sub(r"^https?://", "", item).split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        if item and item not in seen:
            seen.add(item)
            found.append(item)
    return found


def update_list(api_key: str, profile_id: str, list_name: str, raw: str) -> dict[str, Any]:
    domains = tokens(raw)
    current = nextdns(api_key, f"/profiles/{urllib.parse.quote(profile_id)}/{list_name}") or []
    existing = {str(x.get("id", "")).lower() for x in current}
    added, skipped, invalid = [], [], []
    for domain in domains:
        if not DOMAIN_RE.fullmatch(domain):
            invalid.append(domain)
        elif domain in existing:
            skipped.append(domain)
        else:
            nextdns(api_key, f"/profiles/{urllib.parse.quote(profile_id)}/{list_name}", "POST", {"id": domain, "active": True})
            existing.add(domain)
            added.append(domain)
    return {"added": added, "skipped": skipped, "invalid": invalid}


def replace_xml_value(xml: str, key: str, value: str, count: int = 1) -> str:
    # This targets plist string values while preserving the sample's overall XML layout.
    escaped = (value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))
    pattern = rf"(<key>{re.escape(key)}</key>\s*<string>)(.*?)(</string>)"
    return re.sub(pattern, rf"\g<1>{escaped}\g<3>", xml, count=count, flags=re.S)


def make_mobileconfig(upload, name: str, description: str, nextdns_id: str) -> tuple[io.BytesIO, str]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", nextdns_id):
        raise ValueError("NextDNS ID chỉ được chứa chữ, số, dấu gạch ngang hoặc gạch dưới.")
    if not name.strip() or len(name) > 200 or len(description) > 1000:
        raise ValueError("Tên hoặc mô tả cấu hình không hợp lệ.")
    if upload and upload.filename:
        raw = upload.read()
        if len(raw) > 1024 * 1024:
            raise ValueError("File mobileconfig quá lớn (tối đa 1 MB).")
        xml = raw.decode("utf-8-sig")
        source_name = os.path.basename(upload.filename)
    else:
        with open(DEFAULT_TEMPLATE, "r", encoding="utf-8") as fh:
            xml = fh.read()
        source_name = "ANTIBANDA.mobileconfig"
    if "<plist" not in xml or "PayloadIdentifier" not in xml or "dns.nextdns.io" not in xml:
        raise ValueError("File không giống mobileconfig NextDNS hợp lệ.")
    # The sample uses com.vip.antiban.<id>; replace only the ID portion after .antiban.
    xml = re.sub(r"(?<=\.antiban\.)[A-Za-z0-9_-]+", nextdns_id, xml)
    xml = re.sub(r"(https://dns\.nextdns\.io/)[A-Za-z0-9_-]+", rf"\g<1>{nextdns_id}", xml)
    xml = replace_xml_value(xml, "PayloadDisplayName", name.strip(), count=0)
    xml = replace_xml_value(xml, "PayloadDescription", description.strip())
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())[:80] or "nextdns-config"
    if not filename.lower().endswith(".mobileconfig"):
        filename += ".mobileconfig"
    return io.BytesIO(xml.encode("utf-8")), filename


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/profiles")
def profiles():
    try:
        data = nextdns(request.get_json(silent=True).get("api_key", ""), "/profiles")
        return jsonify({"profiles": [{"id": p.get("id"), "name": p.get("name", "(không tên)")} for p in data]})
    except (ValueError, RuntimeError, AttributeError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/update")
def update():
    try:
        payload = request.form
        api_key = payload.get("api_key", "")
        profile_id = payload.get("profile_id", "")
        if not profile_id:
            raise ValueError("Hãy chọn profile NextDNS.")
        result = {
            "denylist": update_list(api_key, profile_id, "denylist", payload.get("denylist", "")),
            "allowlist": update_list(api_key, profile_id, "allowlist", payload.get("allowlist", "")),
        }
        file_obj, filename = make_mobileconfig(request.files.get("mobileconfig"), payload.get("config_name", ""), payload.get("config_description", ""), payload.get("nextdns_id", ""))
        response = send_file(file_obj, as_attachment=True, download_name=filename, mimetype="application/x-apple-aspen-config")
        response.headers["X-NextDNS-Result"] = json.dumps(result, ensure_ascii=False)
        return response
    except (ValueError, RuntimeError, UnicodeDecodeError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "Dữ liệu hoặc file quá lớn."}), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))

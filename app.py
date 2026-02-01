#!/usr/bin/env python3
import os
import tempfile
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename

# -----------------------------
# Load .env
# -----------------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()

# -----------------------------
# Flask app
# -----------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH_MB", "10")) * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", str(Path(__file__).parent / "uploads"))
Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

# Excel database file
EXCEL_FILE = Path(__file__).parent / "reports.xlsx"

ALLOWED_EXTENSIONS = set(
    (os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,pdf,doc,docx,xls,xlsx,txt,zip").split(","))
)
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}

# -----------------------------
# Helpers
# -----------------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_ext(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def tg_api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"


def tg_send_message(text: str) -> dict:
    """Send Telegram text message."""
    if not BOT_TOKEN or not CHAT_ID:
        return {"ok": False, "error": "BOT_TOKEN or CHAT_ID not set"}

    try:
        resp = requests.post(
            tg_api_url("sendMessage"),
            json={"chat_id": CHAT_ID, "text": text},
            timeout=20
        )
        # If Telegram returns error, show it
        data = resp.json()
        if not data.get("ok"):
            return {"ok": False, "error": data.get("description", "Telegram error")}
        return data
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tg_send_document(file_path: str, caption: str = "") -> dict:
    """Send any file as document."""
    if not BOT_TOKEN or not CHAT_ID:
        return {"ok": False, "error": "BOT_TOKEN or CHAT_ID not set"}

    try:
        with open(file_path, "rb") as f:
            files = {"document": (os.path.basename(file_path), f)}
            data = {"chat_id": CHAT_ID, "caption": caption[:1024]}

            resp = requests.post(
                tg_api_url("sendDocument"),
                data=data,
                files=files,
                timeout=60
            )
            res = resp.json()
            if not res.get("ok"):
                return {"ok": False, "error": res.get("description", "Telegram error")}
            return res
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tg_send_photo(file_path: str, caption: str = "") -> dict:
    """Send image as Telegram photo (shows preview)."""
    if not BOT_TOKEN or not CHAT_ID:
        return {"ok": False, "error": "BOT_TOKEN or CHAT_ID not set"}

    try:
        with open(file_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": CHAT_ID, "caption": caption[:1024]}

            resp = requests.post(
                tg_api_url("sendPhoto"),
                data=data,
                files=files,
                timeout=60
            )
            res = resp.json()
            if not res.get("ok"):
                return {"ok": False, "error": res.get("description", "Telegram error")}
            return res
    except Exception as e:
        return {"ok": False, "error": str(e)}


def save_to_excel(data: dict):
    """Append submitted data into Excel database."""
    df_new = pd.DataFrame([data])
    if EXCEL_FILE.exists():
        df_existing = pd.read_excel(EXCEL_FILE)
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_all = df_new
    df_all.to_excel(EXCEL_FILE, index=False)


def load_reports_df() -> pd.DataFrame:
    """
    Load Excel and show ONLY columns that contain at least one real value.
    - Treat "" and whitespace-only as empty
    """
    if not EXCEL_FILE.exists():
        return pd.DataFrame()

    df = pd.read_excel(EXCEL_FILE)

    # trim whitespace on strings
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # blank strings to NA
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    # keep columns with at least 1 value
    keep_cols = df.columns[df.notna().any()].tolist()
    df = df[keep_cols]

    return df


# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        fields = [
            "date", "shift", "name", "total_glasses", "total_money",
            "aba_usd", "aba_khr", "acleda_usd", "acleda_khr", "other_bank",
            "cash_usd", "cash_khr", "expense", "balance_status", "balance_amount",
            "Time"
        ]
        data = {f: request.form.get(f, "") for f in fields}

        # Save report into Excel
        try:
            save_to_excel(data)
        except Exception as e:
            flash(f"⚠️ Could not save to Excel: {e}", "error")

        # Attachment
        uploaded = request.files.get("attachment")
        attachment_path = None
        attachment_ext = ""

        if uploaded and uploaded.filename:
            filename = secure_filename(uploaded.filename)
            if not allowed_file(filename):
                flash(f"File type not allowed: {filename}", "error")
                return redirect(url_for("index"))

            attachment_ext = get_ext(filename)

            fd, tmp_path = tempfile.mkstemp(prefix="upload_", dir=app.config["UPLOAD_FOLDER"])
            os.close(fd)
            uploaded.save(tmp_path)
            attachment_path = tmp_path

        # Telegram message
        message = (
            f"📋 របាយការណ៍ថ្មី\n"
            f"📅 កាលបរិច្ឆេទ: {data['date']}\n"
            f"⏰ ម៉ោង: {data['Time']}\n"
            f"⏰ វេន: {data['shift']}\n"
            f"👤 ឈ្មោះ: {data['name']}\n"
            f"🥤 ចំនួនកែវ: {data['total_glasses']}\n"
            f"💵 លុយសរុប: {data['total_money']}\n\n"
            f"🏦 ABA ($): {data['aba_usd']}\n"
            f"🏦 ABA (៛): {data['aba_khr']}\n"
            f"🏦 ACLEDA ($): {data['acleda_usd']}\n"
            f"🏦 ACLEDA (៛): {data['acleda_khr']}\n"
            f"🏦 Other Bank: {data['other_bank']}\n\n"
            f"💰 លុយដុល្លារ: {data['cash_usd']}\n"
            f"💰 លុយរៀល: {data['cash_khr']}\n"
            f"💸 ចំណាយ: {data['expense']}\n"
            f"⚖️ ស្ថានភាព: {data['balance_status']} / {data['balance_amount']}"
        )

        send_res = tg_send_message(message)

        attach_res = None
        if attachment_path:
            caption = f"Attachment from {data['name']}"

            if attachment_ext in IMAGE_EXTENSIONS:
                attach_res = tg_send_photo(attachment_path, caption=caption)
            else:
                attach_res = tg_send_document(attachment_path, caption=caption)

            try:
                os.remove(attachment_path)
            except Exception:
                pass

        # Result
        ok_any = send_res.get("ok") or (attach_res and attach_res.get("ok"))
        if ok_any:
            flash("Report sent to Telegram ✅ and saved to Excel 📊", "success")
        else:
            err = send_res.get("error") or (attach_res.get("error") if attach_res else "Unknown error")
            flash(f"Failed to send report. Error: {err}", "error")

        return redirect(url_for("index"))

    return render_template("index.html", chat_set=bool(BOT_TOKEN and CHAT_ID))


@app.route("/reports", methods=["GET"])
def reports():
    df = load_reports_df()
    columns = df.columns.tolist()
    rows = df.fillna("").to_dict(orient="records")
    return render_template("reports.html", columns=columns, rows=rows)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)

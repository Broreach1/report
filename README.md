# Flask Report → Telegram Bot

A minimal Flask web app where users submit a report (and optional file) and your Telegram bot forwards it to a chat.

## Quick Start

1. **Download & install**
   ```bash
   python -m venv .venv
   . .venv/Scripts/activate  # Windows
   # or: source .venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   ```

2. **Configure**
   - Create a bot with **@BotFather** → `/newbot` → copy the token.
   - Get your **CHAT_ID** (private chat or group/channel numeric ID).
   - Create `.env` (copy from `.env.example`) and fill:
     ```env
     BOT_TOKEN=123456:ABC-Your-Bot-Token
     CHAT_ID=123456789
     SECRET_KEY=change-this
     MAX_CONTENT_LENGTH_MB=10
     ALLOWED_EXTENSIONS=jpg,jpeg,png,pdf,doc,docx,xls,xlsx,txt,zip
     UPLOAD_FOLDER=uploads
     ```

3. **Run**
   ```bash
   python app.py
   # open http://localhost:5000
   ```

## Notes
- App sends the text via `sendMessage`, and attachments via `sendDocument` with a short caption.
- Max upload size is controlled by `MAX_CONTENT_LENGTH_MB` in `.env`.
- Allowed file types are controlled by `ALLOWED_EXTENSIONS` in `.env`.
- Files are temporarily stored then deleted after sending.

import os
import time
import json
import imaplib
import email
from email.header import decode_header
import requests
import ollama


# ================= CONFIGURATION =================
IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = "kavinkatahgun@gmail.com"           # Your Gmail
EMAIL_APP_PASSWORD = "ktrp hmpa aonk wund"       # 16-letter App Password (RUKO)

MY_WHATSAPP_NUMBER = "918883037979"              # Your phone with country code

MODEL_NAME = "qwen2.5:7b"
CHECK_INTERVAL_SECONDS = 120                     # Checks inbox every 2 minutes
# =================================================

# Track emails so we don't process old ones
processed_email_ids = set()
is_first_run = True

def send_whatsapp(message: str) -> bool:
    payload = {
        "number": MY_WHATSAPP_NUMBER,
        "message": message
    }
    try:
        res = requests.post("http://localhost:3000/send", json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"[-] WhatsApp dispatch error: {e}")
        return False

def clean_subject(raw_subject: str) -> str:
    if not raw_subject:
        return "No Subject"
    decoded_fragments = decode_header(raw_subject)
    subject_parts = []
    for text, encoding in decoded_fragments:
        if isinstance(text, bytes):
            subject_parts.append(text.decode(encoding or "utf-8", errors="ignore"))
        else:
            subject_parts.append(text)
    return "".join(subject_parts)

def extract_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="ignore")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(errors="ignore")
    return body[:2000].strip()

def process_email_with_qwen(sender: str, subject: str, body: str) -> dict:
    prompt = f"""You are a personal executive assistant.
Analyze this email and output ONLY strict JSON with no markdown formatting or commentary:
{{
  "urgency": <integer 1-10>,
  "summary": "<1 brief sentence>",
  "action_required": "<specific action or 'None'>"
}}

Email to evaluate:
From: {sender}
Subject: {subject}
Body: {body}
"""
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={"temperature": 0.1, "num_ctx": 2048}  # Lowered context to prevent VRAM crashes
    )
    return json.loads(response["message"]["content"])

def check_inbox():
    global is_first_run, processed_email_ids
    print(f"[{time.strftime('%H:%M:%S')}] Checking inbox for new messages...")
    
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_APP_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, "UNSEEN")
        if status != "OK" or not messages[0]:
            print(" -> No new emails.")
            mail.logout()
            is_first_run = False
            return

        email_ids = messages[0].split()

        # If this is the first time checking, memorize all unread emails and ignore them
        if is_first_run:
            processed_email_ids.update(email_ids)
            print(f" -> Startup complete: Ignoring {len(email_ids)} old unread emails.")
            is_first_run = False
            mail.logout()
            return

        new_emails_found = 0
        for e_id in email_ids:
            if e_id in processed_email_ids:
                continue  # Skip if we already saw this email

            new_emails_found += 1
            processed_email_ids.add(e_id)

            _, data = mail.fetch(e_id, "(RFC822)")
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            sender = msg.get("From", "Unknown Sender")
            subject = clean_subject(msg.get("Subject"))
            body = extract_body(msg)

            print(f" -> Processing NEW: [{subject[:30]}...] with Qwen 2.5 on RTX 5050...")
            analysis = process_email_with_qwen(sender, subject, body)
            
            urgency = analysis.get("urgency", 1)
            summary = analysis.get("summary", "No summary")
            action = analysis.get("action_required", "None")

            alert_text = (
                f"🚨 *RUKO Email Alert* (Urgency: {urgency}/10)\n\n"
                f"👤 *From:* {sender}\n"
                f"📌 *Subject:* {subject}\n\n"
                f"📝 *Summary:* {summary}\n"
                f"⚡ *Action:* {action}"
            )

            if send_whatsapp(alert_text):
                print(f" -> Alert delivered to WhatsApp! (Urgency {urgency}/10)")
            else:
                print("[-] Failed to deliver message to WhatsApp.")

        if new_emails_found == 0:
            print(" -> No new emails.")

        mail.logout()
    except Exception as e:
        print(f"[-] Pipeline error: {e}")

if __name__ == "__main__":
    print("[*] Ruko AI Email Agent is running on RTX 5050...")
    while True:
        check_inbox()
        time.sleep(CHECK_INTERVAL_SECONDS)

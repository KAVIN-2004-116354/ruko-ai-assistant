
import imaplib
import email
from email.header import decode_header
import json
import requests
import time

# ================= CONFIGURATION =================
IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = "kavinkatahgun@gmail.com"
EMAIL_PASSWORD = "ktrp hmpa aonk wund"                # Replace with your 16-digit Gmail App Password

WHATSAPP_API_URL = "http://127.0.0.1:3000/send" # Internal Docker bridge to Node server
TARGET_PHONE = "918883037979"                  # Replace with your WhatsApp number (include country code, no +)

MODEL_NAME = "qwen2.5"
CHECK_INTERVAL_SECONDS = 60
OLLAMA_HOST = "http://172.17.0.1:11434"  # Forces WSL2 to cross the bridge to your RTX 5050
# =================================================

def clean_subject(subject):
    if not subject:
        return "No Subject"
    decoded_bytes, charset = decode_header(subject)[0]
    if isinstance(decoded_bytes, bytes):
        return decoded_bytes.decode(charset or "utf-8", errors="ignore")
    return decoded_bytes

def extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode(errors="ignore")
    else:
        return msg.get_payload(decode=True).decode(errors="ignore")
    return "Could not extract body."

def process_email_with_qwen(sender, subject, body):
    prompt = f"""
    Analyze this email and return a JSON object with keys: "urgency" (1-10), "summary", and "action_required".
    From: {sender}
    Subject: {subject}
    Body: {body}
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 2048}
    }

    # Bypassing the buggy Ollama library to hit the raw API directly
    response = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=120)
    response.raise_for_status()

    result = response.json()
    return json.loads(result['message']['content'])

def send_whatsapp(message):
    try:
        payload = {
            "number": TARGET_PHONE,
            "message": message
        }
        response = requests.post(WHATSAPP_API_URL, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"[-] WhatsApp Bridge Error: {e}")
        return False

def check_inbox():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        new_emails_found = len(email_ids)

        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    sender = msg.get("From")
                    subject = clean_subject(msg.get("Subject"))
                    body = extract_body(msg)

                    print(f" -> Processing NEW: [{subject[:30]}...] with Qwen 2.5 on RTX 5050...")

                    try:
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

                    except Exception as e:
                        print(f"[-] AI Processing Error: {e}")

        if new_emails_found == 0:
            current_time = time.strftime("%H:%M:%S")
            print(f"[{current_time}] Checking inbox for new messages...\n -> No new emails.")

        mail.logout()
    except Exception as e:
        print(f"[-] Pipeline error: {e}")

if __name__ == "__main__":
    print("[*] Ruko AI Email Agent is running on RTX 5050...")
    while True:
        check_inbox()
        time.sleep(CHECK_INTERVAL_SECONDS)

import os
import smtplib
from email.mime.text import MIMEText

def send_alert(to_email, message_text, reason):
    sender = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    
    if not sender or not password or not to_email:
        print("Email configuration missing.")
        return
        
    msg = MIMEText(f"A high-severity cyberbullying message was detected.\n\nMessage: {message_text}\nReason: {reason}")
    msg['Subject'] = 'GuardianChat Alert: High Severity Cyberbullying Detected'
    msg['From'] = sender
    msg['To'] = to_email
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {e}")

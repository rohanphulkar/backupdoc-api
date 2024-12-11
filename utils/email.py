import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from decouple import config

EMAIL_SENDER = str(config('EMAIL_SENDER'))
EMAIL_PASSWORD = str(config('EMAIL_PASSWORD')) 
EMAIL_HOST = str(config('EMAIL_HOST'))
EMAIL_PORT = int(config('EMAIL_PORT'))

def send_email(sender_email, sender_password, receiver_email, subject, body):
    try:
        # Set up the MIME
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = receiver_email
        message['Subject'] = subject
        
        # Add the body to the message
        message.attach(MIMEText(body, 'plain'))
        
        # Create SMTP session for sending the mail
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.ehlo()  # Identify yourself to the server
        server.starttls()  # Enable SSL/TLS security
        server.ehlo()  # Re-identify yourself over TLS connection
        
        # Login with the sender's email and password
        server.login(sender_email, sender_password)
        
        # Send the email
        text = message.as_string()
        server.sendmail(sender_email, receiver_email, text)
        
        # Terminate the session
        server.quit()
        print("Email sent successfully!")
        
    except Exception as e:
        print(f"Failed to send email: {e}")

# Use the configured email credentials
sender_email = EMAIL_SENDER
sender_password = EMAIL_PASSWORD

def send_forgot_password_email(receiver_email, link):
    try:    
        subject = "Password Reset Request for Your Account"
        body = f"""
Dear User,

We received a request to reset the password for your account. If you didn't make this request, please ignore this email.

To reset your password, please click on the following link or copy and paste it into your browser:

{link}

This link will expire in 3 hours for security reasons.

If you have any issues or need assistance, please don't hesitate to contact our support team.

Best regards,
Backup Doc
"""
        send_email(sender_email, sender_password, receiver_email, subject, body)
        return True
    except Exception as e:
        print(f"Failed to send forgot password email: {e}")
        return False

def contact_us_email(first_name, last_name, email, topic, company_name, company_size, query):
    try:
        subject = f"New Contact Us Query from {first_name} {last_name}"
        body = f"""
Dear Support Team,

You have received a new contact us query. Here are the details:

First Name: {first_name}
Last Name: {last_name}
Email: {email}
Topic: {topic}
Company Name: {company_name}
Company Size: {company_size}
Query: {query}

Please address this query at your earliest convenience.

Best regards,
Your Automated Email System
"""
        send_email(sender_email, sender_password, EMAIL_SENDER, subject, body)
        return True
    except Exception as e:
        print(f"Failed to send contact us email: {e}")
        return False

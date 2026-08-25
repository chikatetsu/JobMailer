import locale
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTP_SERVER, SENDER_EMAIL, SENDER_PASSWORD, JOB_MAILER_URL, JOB_MAILER_PORT
from models.job_response import JobList
from utils.logger import create_logger


log = create_logger("mailer.py")
locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")  # Linux/macOS


def send_mail(new_jobs: JobList, already_saved_jobs: JobList, deleted_jobs: JobList, growth: float):
    try:
        today = date.today()
        subject = f"Offres d'emplois du {today.strftime('%A %d %B').title()}"
        email_body = format_email_body(subject, new_jobs, already_saved_jobs, deleted_jobs, growth)

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = SENDER_EMAIL
        message["To"] = SENDER_EMAIL
        message.attach(MIMEText(email_body, "html"))

        with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, SENDER_EMAIL, message.as_string())

        log.info("Email send")
    except Exception as e:
        log.error(f"Cannot send email: {e}")


def format_email_body(subject: str, new_jobs: JobList, already_saved_jobs: JobList, deleted_jobs: JobList, growth: float):
    def modals(jobs: JobList):
        lines = "".join(
            f'''
            <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;width:200px;display:inline-block;vertical-align:top;margin:8px;font-family:Arial,sans-serif;">
                <div style="width:48px;height:48px;border-radius:8px;display:flex;align-items:center;justify-content:center;margin-bottom:12px;">
                    <img src="{job.company_logo}">
                </div>
                <a href="{f"{JOB_MAILER_URL}:{JOB_MAILER_PORT}/redirect/{job.id}" if JOB_MAILER_URL != "" else job.source_url}">
                    <p style="margin:0;font-size:15px;font-weight:600;color:#111827;">{job.title}</p>
                </a>
                { f'<a href="{job.company_url}">' if job.company_url != "" else "" }
                <p style="margin:4px 0 12px;font-size:13px;color:#6b7280;">{job.company} - {job.address}</p>
                { f'</a>' if job.company_url != "" else "" }
                <hr style="border:none;border-top:1px solid #f3f4f6;margin-bottom:12px;">
                <p style="margin:0;font-size:13px;color:#6b7280;line-height:1.6;">{job.description[:123]}...</p>
            </div>
            '''
            for job in jobs
        )
        return f"""<div>{lines}</div>"""

    if growth < 0:
        growth_color = "#ff0000"
    elif growth > 0:
        growth_color = "#00ff00"
    else:
        growth_color = "#ffffff"
    title_new_jobs = f"<h3 style=\"color:#00aa00;\">Nouvelles offres ({len(new_jobs)})</h3>{modals(new_jobs[:12])}" if len(new_jobs) > 0 else ""
    title_interesting_jobs = f"<h3 style=\"color:#aaaa00\">Offres intéressantes</h3>{modals(already_saved_jobs[:12])}" if len(already_saved_jobs) > 0 else ""
    title_deleted_jobs = f"<h3 style=\"color:#aa0000\">Offres expirées ({len(deleted_jobs)})</h3>{modals(deleted_jobs[:12])}" if len(deleted_jobs) > 0 else ""
    return f"""
        <html><body>
        <h2>{subject}</h2>
        <p>Total des offres : {len(new_jobs) + len(already_saved_jobs)}</p>
        <p style="color:{growth_color};">Croissance : {"+" if growth > 0 else ""}{growth:.2f}%</p>
        {title_new_jobs}
        {title_interesting_jobs}
        {title_deleted_jobs}
        </body></html>
        """

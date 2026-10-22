"""
Kurswächter A 527 - Version für GitHub Actions.
Prüft EINMAL pro Aufruf, ob A 527 im Campusportal belegbar ist, und schickt dann eine Mail.
Zugangsdaten kommen aus den GitHub-Secrets (CAMPUS_USER, CAMPUS_PASS, MAIL_USER, MAIL_PASS).
Rückgabe: Datei "frei.txt" wird angelegt, wenn der Kurs belegbar ist (dann schaltet sich der Wächter ab).
"""
import os
import smtplib
import sys
from email.message import EmailMessage

from playwright.sync_api import sync_playwright

LOGIN_URL = "https://campus.uni-speyer.de/"
KURS_URL = "https://campus.uni-speyer.de/studium/meine-kurse.php"
KURS_KENNUNG = "26WiSe-A-527"


def env(name):
    wert = os.environ.get(name, "").strip()
    if not wert:
        sys.exit(f"Secret {name} fehlt. Bitte in GitHub unter Settings > Secrets eintragen.")
    return wert


def einloggen(page):
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    pw = page.locator("input[type='password']")
    if pw.count() == 0:
        return
    pw = pw.first
    form = pw.locator("xpath=ancestor::form[1]")
    bereich = form if form.count() > 0 else page
    bereich.locator("input[type='text'], input[type='email'], input:not([type])").first.fill(env("CAMPUS_USER"))
    pw.fill(env("CAMPUS_PASS"))
    pw.press("Enter")
    page.wait_for_load_state("networkidle", timeout=60000)
    if page.locator("input[type='password']").count() > 0:
        sys.exit("Login fehlgeschlagen (Benutzername/Passwort in den Secrets prüfen).")


def kurs_belegbar(page):
    page.goto(KURS_URL, wait_until="networkidle", timeout=60000)
    treffer = page.get_by_text(KURS_KENNUNG, exact=False)
    if treffer.count() == 0:
        sys.exit("Kurs nicht auf der Belegungsseite gefunden.")
    eintrag = treffer.first.locator(
        "xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' list-group-item ')][1]"
    )
    buttons = eintrag.locator("div.button-col").first.locator("button.book:not(.disabled)")
    return any("An" in buttons.nth(i).inner_text() for i in range(buttons.count()))


def mail_senden():
    msg = EmailMessage()
    msg["From"] = env("MAIL_USER")
    msg["To"] = env("MAIL_USER")
    msg["Subject"] = "A 527 ist wieder belegbar!"
    msg.set_content(
        "Im Campusportal ist A 527 Staatliche Sicherheit im Wandel gerade belegbar.\n"
        f"Jetzt belegen: {KURS_URL}\n\nDer GitHub-Wächter hat sich danach automatisch abgeschaltet."
    )
    with smtplib.SMTP("mail.gmx.net", 587, timeout=30) as s:
        s.starttls()
        s.login(env("MAIL_USER"), env("MAIL_PASS"))
        s.send_message(msg)


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        einloggen(page)
        frei = kurs_belegbar(page)
        browser.close()
    if frei:
        print("A 527 ist belegbar - Mail wird gesendet.")
        mail_senden()
        open("frei.txt", "w").write("frei")
    else:
        print("A 527 noch nicht belegbar.")

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://result.idu.uz"

def get_csrf_and_captcha(session):
    resp = session.get(BASE_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    csrf = soup.find("input", {"name": "_csrf-frontend"})["value"]
    captcha_src = soup.find("img", id="resultform-verifycode-image")["src"]
    return csrf, BASE_URL + captcha_src

def download_captcha(session, url):
    r = session.get(url, stream=True)
    if r.status_code == 200:
        path = "captcha.jpg"
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    return None

def submit_result(session, passport, captcha, csrf_token):
    data = {
        "_csrf-frontend": csrf_token,
        "ResultForm[passportId]": passport,
        "ResultForm[verifyCode]": captcha
    }
    resp = session.post(BASE_URL + "/", data=data)
    return resp.text

def parse_result(html):
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("div", class_="block-heading")

    if not heading:
        return "❌ Ma'lumot topilmadi. Ehtimol passport yoki captcha noto‘g‘ri."

    name = heading.find("h1").text.strip()
    scores = heading.find_all("h1", class_="text-primary")
    results = "\n".join(r.text.strip() for r in scores)
    return f"✅ {name}\n{results}"

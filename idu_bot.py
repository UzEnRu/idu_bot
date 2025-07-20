import requests
from bs4 import BeautifulSoup

BASE_URL = "https://result.idu.uz"

def get_csrf_and_captcha(session):
    response = session.get(BASE_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    csrf_token = soup.find("input", {"name": "_csrf-frontend"})["value"]
    captcha_img = soup.find("img", {"id": "resultform-verifycode-image"})["src"]
    captcha_url = BASE_URL + captcha_img

    return csrf_token, captcha_url

def get_captcha_image(session, url):
    r = session.get(url, stream=True)
    if r.status_code == 200:
        with open("captcha.jpg", "wb") as f:
            f.write(r.content)
        return "captcha.jpg"
    return None

def submit_form(session, passport_id, captcha_text, csrf_token):
    payload = {
        "_csrf-frontend": csrf_token,
        "ResultForm[passportId]": passport_id,
        "ResultForm[verifyCode]": captcha_text
    }
    response = session.post(BASE_URL + "/", data=payload)
    return response.text

def extract_results(html):
    soup = BeautifulSoup(html, "html.parser")
    result_block = soup.find("div", class_="block-heading")

    if not result_block:
        return "❌ Ma'lumot topilmadi. Ehtimol captcha yoki passport noto‘g‘ri."

    name = result_block.find("h1").text.strip()
    result_texts = result_block.find_all("h1", class_="text-primary")
    results = "\n".join(r.text.strip() for r in result_texts)

    return f"✅ {name}\n{results}"

"""Send today's card news via Kakao '나에게 보내기' API. Runs inside GitHub Actions.

Reads PAGES_URL (the deployed GitHub Pages URL) plus KAKAO_REST_API_KEY,
KAKAO_CLIENT_SECRET (optional), and KAKAO_REFRESH_TOKEN from the environment,
exchanges the refresh token for an access token, and sends a feed-template
message linking to today's card news site.
"""
import json
import os

import requests

PAGES_URL = os.environ["PAGES_URL"].rstrip("/") + "/"
REST_API_KEY = os.environ["KAKAO_REST_API_KEY"]
CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ["KAKAO_REFRESH_TOKEN"]


def get_access_token():
    data = {
        "grant_type": "refresh_token",
        "client_id": REST_API_KEY,
        "refresh_token": REFRESH_TOKEN,
    }
    if CLIENT_SECRET:
        data["client_secret"] = CLIENT_SECRET
    resp = requests.post("https://kauth.kakao.com/oauth/token", data=data, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if "refresh_token" in body:
        print("[notice] Kakao가 새 refresh_token을 발급했습니다. 기존 토큰이 곧 만료될 수 있으니 "
              "GitHub Secret KAKAO_REFRESH_TOKEN을 아래 값으로 교체하세요:")
        print(body["refresh_token"])
    return body["access_token"]


def load_site_data():
    with open("site/data.json", encoding="utf-8") as f:
        return json.load(f)


def build_template(data):
    cards = data["cards"]
    first = cards[0]
    titles = "\n".join(f"{i + 1}. {c['title_kr']}" for i, c in enumerate(cards))
    return {
        "object_type": "feed",
        "content": {
            "title": f"AI 카드뉴스 · {data['date']}",
            "description": titles[:200],
            "image_url": PAGES_URL + first["image"],
            "image_width": 1080,
            "image_height": 1080,
            "link": {
                "web_url": PAGES_URL,
                "mobile_web_url": PAGES_URL,
            },
        },
        "buttons": [
            {
                "title": "카드뉴스 전체보기",
                "link": {"web_url": PAGES_URL, "mobile_web_url": PAGES_URL},
            }
        ],
    }


def send(access_token, template):
    resp = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=30,
    )
    print(resp.status_code, resp.text)
    resp.raise_for_status()


def main():
    data = load_site_data()
    token = get_access_token()
    template = build_template(data)
    send(token, template)
    print("카카오 전송 완료")


if __name__ == "__main__":
    main()

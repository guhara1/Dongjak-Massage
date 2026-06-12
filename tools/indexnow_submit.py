#!/usr/bin/env python3
"""IndexNow 일괄 제출 스크립트.

배포가 반영된 뒤 실행하면 sitemap.xml 의 모든 URL 을 IndexNow API 로 제출한다.
Bing·Naver 등 IndexNow 참여 검색엔진이 즉시 크롤링 대상으로 인지한다.

사용:
    python3 tools/indexnow_submit.py
"""
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from build import INDEXNOW_KEY  # noqa: E402
from content.site import BASE_URL  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def main():
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    urls = re.findall(r"<loc>([^<]+)</loc>", sm)
    host = BASE_URL.split("//", 1)[1].rstrip("/")
    payload = {
        "host": host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{BASE_URL.rstrip('/')}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        print(f"IndexNow 응답: HTTP {res.status} — URL {len(urls)}건 제출 완료")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""동작 출장마사지 정적 사이트 빌드 스크립트.

content/*.md (front matter + 본문) 를 읽어 HTML 페이지를 생성한다.

규칙:
- 본문 2,000자(공백 제외) 미만 페이지는 자동으로 noindex 처리
- sitemap.xml 에는 index 페이지만 포함
- 푸터에 지역명·역명 대량 나열 금지 (템플릿에서 원천 차단)
"""
import os
import re
import sys
import html
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(ROOT, "content")
OUT_DIR = ROOT

# 배포 도메인 확정 시 변경 (sitemap·canonical 에 사용)
SITE_URL = "https://www.ganda-go.com"

BRAND = "간다 GO"
PHONE = "0508-202-4719"
PHONE_TEL = "0508-202-4719"

MIN_CHARS = 2000
MAX_CHARS = 2600

NAV = [
    ("홈", "/"),
    ("동작 출장마사지", "/service/"),
    ("지역별 안내", "/dongjak-gu/"),
    ("지하철역별 안내", "/dongjak-gu/stations/"),
    ("테마별 안내", "/themes/"),
    ("코스안내", "/courses/"),
    ("예약안내", "/reservation/"),
    ("이용가이드", "/guide/"),
    ("후기", "/reviews/"),
    ("고객센터", "/support/"),
]

# 드롭다운 하위 메뉴 (메뉴명은 짧게 — 키워드 반복 금지)
SUBNAV = {
    "/dongjak-gu/": [
        ("동작구 전체", "/dongjak-gu/"),
        ("노량진동", "/dongjak-gu/noryangjin-dong/"),
        ("상도동", "/dongjak-gu/sangdo-dong/"),
        ("본동", "/dongjak-gu/bon-dong/"),
        ("흑석동", "/dongjak-gu/heukseok-dong/"),
        ("동작동", "/dongjak-gu/dongjak-dong/"),
        ("사당동", "/dongjak-gu/sadang-dong/"),
        ("대방동", "/dongjak-gu/daebang-dong/"),
        ("신대방동", "/dongjak-gu/sindaebang-dong/"),
    ],
    "/dongjak-gu/stations/": [
        ("동작 지하철역 전체", "/dongjak-gu/stations/"),
        ("노량진역", "/dongjak-gu/stations/noryangjin-station/"),
        ("대방역", "/dongjak-gu/stations/daebang-station/"),
        ("노들역", "/dongjak-gu/stations/nodeul-station/"),
        ("흑석역", "/dongjak-gu/stations/heukseok-station/"),
        ("동작역", "/dongjak-gu/stations/dongjak-station/"),
        ("이수역", "/dongjak-gu/stations/isu-station/"),
        ("사당역", "/dongjak-gu/stations/sadang-station/"),
        ("남성역", "/dongjak-gu/stations/namseong-station/"),
        ("숭실대입구역", "/dongjak-gu/stations/soongsil-univ-station/"),
        ("상도역", "/dongjak-gu/stations/sangdo-station/"),
        ("장승배기역", "/dongjak-gu/stations/jangseungbaegi-station/"),
        ("신대방삼거리역", "/dongjak-gu/stations/sindaebang-samgeori-station/"),
        ("보라매역", "/dongjak-gu/stations/boramae-station/"),
        ("서울지방병무청역", "/dongjak-gu/stations/seoul-regional-military-manpower-station/"),
        ("보라매공원역", "/dongjak-gu/stations/boramae-park-station/"),
        ("보라매병원역", "/dongjak-gu/stations/boramae-hospital-station/"),
    ],
    "/themes/": [
        ("전체 테마", "/themes/"),
        ("스웨디시", "/themes/swedish/"),
        ("로미로미", "/themes/lomi-lomi/"),
        ("타이마사지", "/themes/thai/"),
        ("중국마사지", "/themes/chinese/"),
        ("아로마테라피", "/themes/aromatherapy/"),
        ("홈케어", "/themes/home-care/"),
        ("호텔식마사지", "/themes/hotel-style/"),
        ("발마사지", "/themes/foot/"),
        ("스포츠·경락", "/themes/sports/"),
        ("스킨케어", "/themes/skincare/"),
        ("왁싱", "/themes/waxing/"),
        ("커플 관리", "/themes/couple/"),
        ("24시간", "/themes/24-hours/"),
        ("수면 가능", "/themes/overnight/"),
    ],
}

PAGE_TMPL = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{seo_title}</title>
<meta name="description" content="{description}">
{robots}<link rel="canonical" href="{canonical}">
<link rel="stylesheet" href="/assets/style.css">
{schema}</head>
<body>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="/">{brand} <span class="brand-sub">동작 출장마사지</span></a>
    <a class="call-btn" href="tel:{phone_tel}">📞 {phone}</a>
  </div>
  <nav class="gnb" aria-label="주 메뉴">
    <div class="wrap"><ul>
{nav_items}
    </ul></div>
  </nav>
</header>
<main class="wrap">
<nav class="breadcrumb" aria-label="현재 위치">{breadcrumb}</nav>
<article>
<h1>{h1}</h1>
{body}
</article>
{related}
<aside class="cta-band">
  <p><strong>{brand}</strong> 전화예약 <a href="tel:{phone_tel}">{phone}</a></p>
  <p class="cta-note">동작구 전지역 방문 가능 여부는 예약 시 위치 기준으로 확인해 드립니다.</p>
</aside>
</main>
<footer class="site-footer">
  <div class="wrap">
    <p><strong>{brand}</strong> | 동작 출장마사지·홈타이 예약 안내 | 전화예약 <a href="tel:{phone_tel}">{phone}</a></p>
    <p class="footer-links"><a href="/support/">고객센터</a> · <a href="/guide/">이용가이드</a> · <a href="/reservation/">예약안내</a></p>
    <p class="footer-note">본 사이트는 건전한 방문 관리 예약 안내를 목적으로 하며, 불법적인 서비스는 일절 제공하지 않습니다.</p>
  </div>
</footer>
</body>
</html>
"""


def parse_front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("front matter 없음")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, m.group(2).strip()


def md_inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def render_body(body):
    """## 단위 섹션, 문단, 리스트, Q./A. FAQ 를 HTML 로 변환."""
    out = []
    faq_items = []
    blocks = re.split(r"\n\s*\n", body)
    in_faq = False
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith("## "):
            title = block[3:].strip()
            in_faq = "자주 묻는 질문" in title or "FAQ" in title.upper()
            out.append(f"<h2>{md_inline(title)}</h2>")
            continue
        if block.startswith("### "):
            out.append(f"<h3>{md_inline(block[4:].strip())}</h3>")
            continue
        lines = block.splitlines()
        if all(l.strip().startswith("- ") for l in lines):
            items = "".join(f"<li>{md_inline(l.strip()[2:])}</li>" for l in lines)
            out.append(f"<ul>{items}</ul>")
            continue
        if in_faq and lines[0].strip().startswith("Q."):
            q = md_inline(lines[0].strip()[2:].strip())
            a_lines = [l.strip()[2:].strip() if l.strip().startswith("A.") else l.strip() for l in lines[1:]]
            a = md_inline(" ".join(a_lines))
            faq_items.append((q, a))
            out.append(
                f'<div class="faq-item"><h3 class="faq-q">Q. {q}</h3><p class="faq-a">{a}</p></div>'
            )
            continue
        out.append(f"<p>{md_inline(' '.join(l.strip() for l in lines))}</p>")
    return "\n".join(out), faq_items


def body_char_count(body_html):
    text = re.sub(r"<[^>]+>", "", body_html)
    text = html.unescape(text)
    return len(re.sub(r"\s+", "", text))


def faq_schema(faq_items):
    if not faq_items:
        return ""
    import json
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)},
            }
            for q, a in faq_items
        ],
    }
    return '<script type="application/ld+json">%s</script>\n' % json.dumps(data, ensure_ascii=False)


def business_schema():
    import json
    data = {
        "@context": "https://schema.org",
        "@type": "HealthAndBeautyBusiness",
        "name": BRAND,
        "description": "동작구 전지역 출장마사지·홈타이 방문 관리 예약 안내",
        "telephone": PHONE,
        "url": SITE_URL + "/",
        "areaServed": {"@type": "AdministrativeArea", "name": "서울특별시 동작구"},
    }
    return '<script type="application/ld+json">%s</script>\n' % json.dumps(data, ensure_ascii=False)


def nav_html(active_url):
    items = []
    for label, url in NAV:
        cls = ' class="active"' if active_url == url or (
            url != "/" and active_url.startswith(url)
        ) else ""
        sub = SUBNAV.get(url)
        if sub:
            subitems = "".join(
                f'<li><a href="{su}">{sl}</a></li>' for sl, su in sub
            )
            items.append(
                f'      <li class="has-sub"{""}><a href="{url}"{cls}>{label}</a>'
                f"<ul class=\"subnav\">{subitems}</ul></li>"
            )
        else:
            items.append(f'      <li><a href="{url}"{cls}>{label}</a></li>')
    return "\n".join(items)


def breadcrumb_html(meta):
    crumbs = [("홈", "/")]
    section = meta.get("section", "")
    section_map = {
        "service": ("동작 출장마사지", "/service/"),
        "regions": ("지역별 안내", "/dongjak-gu/"),
        "stations": ("지하철역별 안내", "/dongjak-gu/stations/"),
        "themes": ("테마별 안내", "/themes/"),
        "courses": ("코스안내", "/courses/"),
        "reservation": ("예약안내", "/reservation/"),
        "guide": ("이용가이드", "/guide/"),
        "reviews": ("후기", "/reviews/"),
        "support": ("고객센터", "/support/"),
    }
    url = meta["url"]
    if section in section_map:
        sec_label, sec_url = section_map[section]
        crumbs.append((sec_label, sec_url))
        if url != sec_url:
            crumbs.append((meta.get("nav_label", meta["h1"]), url))
        # 역 페이지는 지역별 안내 하위가 아닌 stations 하위
        if section == "stations" and url != sec_url:
            pass
    parts = []
    for i, (label, u) in enumerate(crumbs):
        if i == len(crumbs) - 1 and len(crumbs) > 1:
            parts.append(f"<span>{label}</span>")
        else:
            parts.append(f'<a href="{u}">{label}</a>')
    return " › ".join(parts)


def related_html(meta):
    rel = meta.get("related", "")
    if not rel:
        return ""
    links = []
    for token in rel.split("|"):
        token = token.strip()
        if not token:
            continue
        label, _, url = token.partition("=")
        links.append(f'<li><a href="{url.strip()}">{label.strip()}</a></li>')
    if not links:
        return ""
    return (
        '<nav class="related" aria-label="관련 안내"><h2>관련 안내</h2><ul>'
        + "".join(links)
        + "</ul></nav>"
    )


def build():
    report = []
    sitemap_urls = []
    files = sorted(os.listdir(CONTENT_DIR))
    for fname in files:
        if not fname.endswith(".md"):
            continue
        with open(os.path.join(CONTENT_DIR, fname), encoding="utf-8") as f:
            meta, body = parse_front_matter(f.read())
        url = meta["url"]
        body_html, faq_items = render_body(body)
        count = body_char_count(body_html)
        noindex = count < MIN_CHARS or meta.get("noindex") == "true"
        robots = '<meta name="robots" content="noindex, follow">\n' if noindex else ""
        schema = faq_schema(faq_items)
        if url == "/":
            schema = business_schema() + schema
        page = PAGE_TMPL.format(
            seo_title=html.escape(meta["seo_title"], quote=True),
            description=html.escape(meta["description"], quote=True),
            robots=robots,
            canonical=SITE_URL + url,
            schema=schema,
            brand=BRAND,
            phone=PHONE,
            phone_tel=PHONE_TEL,
            nav_items=nav_html(url),
            breadcrumb=breadcrumb_html(meta),
            h1=md_inline(meta["h1"]),
            body=body_html,
            related=related_html(meta),
        )
        out_path = os.path.join(OUT_DIR, url.lstrip("/"), "index.html")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page)
        if not noindex:
            sitemap_urls.append(url)
        flag = "noindex" if noindex else ("LONG" if count > MAX_CHARS else "ok")
        report.append((url, count, flag))

    # sitemap.xml
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in sorted(sitemap_urls):
        sm.append(f"  <url><loc>{SITE_URL}{url}</loc></url>")
    sm.append("</urlset>")
    with open(os.path.join(OUT_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(sm) + "\n")

    with open(os.path.join(OUT_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")

    print(f"{'URL':60} {'글자수':>6} 상태")
    for url, count, flag in report:
        print(f"{url:60} {count:>6} {flag}")
    print(f"\n총 {len(report)}페이지, index {len(sitemap_urls)}페이지")


if __name__ == "__main__":
    build()

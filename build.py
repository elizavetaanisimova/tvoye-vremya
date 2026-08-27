#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка статического сайта студии массажа «Твоё Время».

    python3 build.py

Пишет готовые HTML-файлы в корень проекта. Тексты и прайс лежат в content.py.
Результат работает без Node, без базы и без сервера приложений:
это обычные HTML, CSS, JS и картинки.
"""

import glob
import json
import os
import random
import re
from datetime import date

from content import (SITE, PROGRAMS, PICKER, PICKER_ALT, PRINCIPLES, REVIEWS,
                     FAQ_MAIN, SERVICE_PAGES, PAIR_EXAMPLES)

ROOT = os.path.dirname(os.path.abspath(__file__))
TODAY = date.today().isoformat()
D = SITE["domain"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def sprite():
    """Инлайн-спрайт из иконок Phosphor: ноль лишних запросов."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "assets/icons/*.svg"))):
        name = os.path.basename(f)[:-4]
        s = open(f, encoding="utf-8").read()
        vb = re.search(r'viewBox="([^"]+)"', s).group(1)
        inner = re.sub(r"(?s)^.*?<svg[^>]*>|</svg>\s*$", "", s).strip()
        out.append('<symbol id="i-%s" viewBox="%s">%s</symbol>' % (name, vb, inner))
    return ('<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false" '
            'style="position:absolute;width:0;height:0;overflow:hidden"><defs>'
            + "".join(out) + "</defs></svg>")


def hand_drawn_frame():
    """Рамка вокруг снимка в первом экране, проведённая как будто от руки.

    Прямоугольник со скруглениями, у которого каждая точка слегка сдвинута,
    а прямые участки разбиты на сегменты и сглажены в кривую. Зерно случайных
    чисел зафиксировано, поэтому при каждой сборке рамка получается одинаковой.
    """
    rnd = random.Random(11)
    W, H, R, J = 400.0, 520.0, 40.0, 7.0

    def j(v, k=1.0):
        return round(v + rnd.uniform(-J, J) * k, 1)

    def side(x1, y1, x2, y2, n=5):
        out = []
        for i in range(1, n + 1):
            t = i / (n + 1)
            out.append((j(x1 + (x2 - x1) * t), j(y1 + (y2 - y1) * t)))
        return out

    pts = [(j(R), j(0))]
    pts += side(R, 0, W - R, 0)
    pts += [(j(W - R), j(0)), (j(W, .5), j(R * .3, .5)), (j(W), j(R))]
    pts += side(W, R, W, H - R, 6)
    pts += [(j(W), j(H - R)), (j(W, .5), j(H - R * .3, .5)), (j(W - R), j(H))]
    pts += side(W - R, H, R, H)
    pts += [(j(R), j(H)), (j(0, .5), j(H - R * .3, .5)), (j(0), j(H - R))]
    pts += side(0, H - R, 0, R, 6)
    pts += [(j(0), j(R)), (j(0, .5), j(R * .3, .5))]

    d = ["M %s %s" % pts[0]]
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        d.append("Q %s %s %s %s" % (x0, y0, round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1)))
    d.append("Q %s %s %s %s" % (pts[-1][0], pts[-1][1], pts[0][0], pts[0][1]))
    d.append("Z")
    return " ".join(d)


FRAME_PATH = hand_drawn_frame()


def ic(name, cls=""):
    c = ("i " + cls).strip()
    return '<svg class="%s" aria-hidden="true"><use href="#i-%s"></use></svg>' % (c, name)


def prog_url(slug_page):
    return "/uslugi/%s/" % slug_page


def zapis_url(prog_key=None):
    """Внутренняя ссылка на страницу записи. Услугу передаём параметром,
    страница сама подставит её в форму."""
    return "/zapis/?u=%s" % prog_key if prog_key else "/zapis/"


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def price(n):
    return "%s&nbsp;р." % n


def services_json():
    """Карта «ключ программы -> что подставить в форму», её читает app.js."""
    page_of = {}
    for sp in SERVICE_PAGES:
        for k in sp["programs"]:
            page_of.setdefault(k, prog_url(sp["slug"]))
    data = {k: {"id": v["yid"], "name": v["name"], "dur": v["dur"], "mins": v["mins"],
                "price": v["price"], "covers": v["covers"],
                "page": page_of.get(k, "/uslugi/")}
            for k, v in PROGRAMS.items()}
    return ('<script id="tv-services" type="application/json">%s</script>'
            % json.dumps({"base": SITE["booking_url"], "alt": PICKER_ALT, "items": data},
                         ensure_ascii=False, separators=(",", ":")))


def picker_json():
    """Варианты подбора на главной. Собираются из content.py, чтобы тексты
    и цены не приходилось дублировать в JavaScript."""
    out = [{"key": key, "label": label, "prog": prog, "extra": extra, "why": why}
           for key, label, prog, extra, why in PICKER]
    return ('<script id="tv-picker" type="application/json">%s</script>'
            % json.dumps(out, ensure_ascii=False, separators=(",", ":")))


# ---------------------------------------------------------------------------
# schema.org
# ---------------------------------------------------------------------------
BUSINESS_ID = D + "/#studio"


def business_schema():
    return {
        "@type": "HealthAndBeautyBusiness",
        "@id": BUSINESS_ID,
        "name": SITE["name"],
        "alternateName": SITE["legal_name"],
        "description": "Студия массажа в Минске на Маяке Минска: классический массаж, "
                       "массаж лица, коррекция фигуры, спортивный и миофасциальный массаж.",
        "image": D + "/assets/img/hero-1280.jpg",
        "logo": D + "/favicon.svg",
        "url": D + "/",
        "telephone": SITE["phone"],
        "priceRange": "40-110 BYN",
        "currenciesAccepted": "BYN",
        "paymentAccepted": "Наличные, банковская карта",
        "areaServed": {"@type": "City", "name": "Минск"},
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "%s, %s" % (SITE["street"], SITE["room"]),
            "addressLocality": SITE["city"],
            "postalCode": SITE["postal"],
            "addressCountry": "BY",
        },
        "geo": {"@type": "GeoCoordinates", "latitude": SITE["lat"], "longitude": SITE["lon"]},
        "hasMap": SITE["yandex_map"],
        "sameAs": [SITE["instagram"], SITE["threads"], SITE["telegram"]],
        "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": days.split(),
             "opens": o, "closes": c}
            for days, o, c in SITE["hours"]
        ],
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": SITE["rating_value"],
            "bestRating": 5,
            "reviewCount": SITE["reviews_count"],
            "ratingCount": SITE["ratings_count"],
        },
        "review": [
            {"@type": "Review", "author": {"@type": "Person", "name": n},
             "reviewRating": {"@type": "Rating", "ratingValue": 5, "bestRating": 5},
             "reviewBody": t}
            for n, _tag, t in REVIEWS[:5]
        ],
    }


def offer_catalog():
    items, seen = [], set()
    for page in SERVICE_PAGES:
        for key in page["programs"]:
            p = PROGRAMS[key]
            if p["name"] in seen:
                continue
            seen.add(p["name"])
            items.append({
                "@type": "Offer",
                "priceCurrency": "BYN",
                "price": str(p["price"]),
                "url": D + prog_url(page["slug"]),
                "itemOffered": {
                    "@type": "Service",
                    "name": p["name"],
                    "description": p["desc"],
                    "serviceType": page["title"],
                },
            })
    return {"@type": "OfferCatalog", "name": "Программы студии «Твоё Время»",
            "itemListElement": items}


def faq_schema(pairs):
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in pairs
        ],
    }


def crumbs_schema(items):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": D + u}
            for i, (n, u) in enumerate(items)
        ],
    }


# ---------------------------------------------------------------------------
# каркас страницы
# ---------------------------------------------------------------------------
NAV = [
    ("Услуги", "/uslugi/"),
    ("Абонементы", "/abonementy/"),
    ("Отзывы", "/#otzyvy"),
    ("Контакты", "/kontakty/"),
]

MENU = [
    ("Услуги и цены", "/uslugi/"),
    ("Массаж спины и шеи", "/uslugi/massazh-spiny-i-shei/"),
    ("Общий массаж тела", "/uslugi/obshchiy-massazh/"),
    ("Массаж лица", "/uslugi/massazh-lica/"),
    ("Коррекция фигуры", "/uslugi/antitsellyulitnyy-massazh/"),
    ("Спорт и восстановление", "/uslugi/sportivnyy-massazh/"),
    ("Парный массаж", "/uslugi/parnyy-massazh/"),
    ("Signature, 90 минут", "/uslugi/signature/"),
    ("Абонементы и сертификаты", "/abonementy/"),
    ("Контакты", "/kontakty/"),
]


def head(title, desc, path, schema_nodes, og_image="/assets/img/hero-1280.jpg",
         hero_preload=""):
    graph = {"@context": "https://schema.org", "@graph": schema_nodes}
    return """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0E1310">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{domain}{path}">
<meta property="og:type" content="website">
<meta property="og:locale" content="ru_RU">
<meta property="og:site_name" content="{site}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{domain}{path}">
<meta property="og:image" content="{domain}{og}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/favicon.svg">
<link rel="preload" href="/assets/fonts/manrope-cyr.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/cormorant-cyr.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preconnect" href="https://n{yid}.yclients.com">
{hero_preload}
<link rel="stylesheet" href="/assets/css/fonts.css">
<link rel="stylesheet" href="/assets/css/style.css">
<script type="application/ld+json">{ld}</script>
</head>
<body>
{sprite}
<a class="skip" href="#main">Перейти к содержанию</a>
""".format(title=title, desc=desc, path=path, domain=D, site=SITE["name"], og=og_image,
           yid=SITE["yclients_id"], hero_preload=hero_preload,
           ld=json.dumps(graph, ensure_ascii=False, separators=(",", ":")),
           sprite=sprite())


def header():
    nav = "".join('<a href="%s">%s</a>' % (u, n) for n, u in NAV)
    menu = "".join('<a href="%s">%s</a>' % (u, n) for n, u in MENU)
    return """
<header class="hdr" id="hdr">
  <div class="hdr__in">
    <a class="brand" href="/" aria-label="Твоё Время, студия массажа в Минске, на главную">
      <span class="brand__mark" aria-hidden="true">
        <svg viewBox="0 0 40 40" focusable="false"><circle cx="20" cy="20" r="18.5" fill="none" stroke="currentColor" stroke-width="1"/><path d="M12 14h16M20 14v13.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
      </span>
      <span class="brand__txt">
        <span class="brand__name">Твоё Время</span>
        <span class="brand__sub">массаж и забота</span>
      </span>
    </a>
    <nav class="nav" aria-label="Основная навигация">{nav}</nav>
    <div class="hdr__act">
      <a class="hdr__tel" href="tel:{phone}">{phone_pretty}</a>
      <a class="btn btn--gold btn--sm" href="/zapis/">Записаться</a>
      <button class="burger" type="button" id="burger" aria-expanded="false" aria-controls="menu" aria-label="Открыть меню">
        {list_icon}
      </button>
    </div>
  </div>
</header>

<div class="menu" id="menu" hidden>
  <div class="menu__in">
    <button class="menu__x" type="button" id="menuClose" aria-label="Закрыть меню">{x_icon}</button>
    <nav class="menu__nav" aria-label="Меню">{menu}</nav>
    <div class="menu__foot">
      <a class="btn btn--gold" href="/zapis/">Записаться</a>
      <a class="menu__tel" href="tel:{phone}">{phone_pretty}</a>
    </div>
  </div>
</div>
<main id="main">
""".format(nav=nav, menu=menu, phone=SITE["phone"], phone_pretty=SITE["phone_pretty"],
           list_icon=ic("list"), x_icon=ic("x"))


def crumbs(items):
    """items: [(name, url), ...] последний элемент без ссылки."""
    parts = ['<a href="/">Главная</a>']
    for i, (n, u) in enumerate(items):
        last = i == len(items) - 1
        parts.append('<span class="crumbs__s" aria-hidden="true">%s</span>'
                     % ic("caret-right", "i--xs"))
        parts.append('<span aria-current="page">%s</span>' % n if last
                     else '<a href="%s">%s</a>' % (u, n))
    return ('<nav class="crumbs" aria-label="Хлебные крошки"><div class="wrap">%s</div></nav>'
            % "".join(parts))


def booking(anchor="zapis", heading="Записаться онлайн", tag="h2", full=False,
            lead="Форма показывает свободные окна на ближайшие дни и подтверждает визит сразу. "
                 "Это та же система, в которой работает студия, поэтому время всегда актуальное."):
    return """
<section class="sec sec--book" id="{anchor}">
  <div class="wrap">
    <div class="sec__head">
      <{tag}>{heading}</{tag}>
      <p class="lead">{lead}</p>
    </div>
    <div class="book{full}">
      <p class="book__pick" id="bookPick" hidden></p>
      <div class="book__frame" data-yclients="{url}">
        <noscript><a class="btn btn--gold" href="{url}" target="_blank" rel="noopener">Открыть форму записи</a></noscript>
      </div>
      <p class="book__alt">
        Не открывается форма?
        <a class="lnk" href="{url}" target="_blank" rel="noopener">Открыть в новом окне {ext}</a>
        <span>или напишите нам:</span>
        <a class="lnk" href="tel:{phone}">{phone_pretty}</a>
        <a class="lnk" href="{tg}" target="_blank" rel="noopener">Telegram</a>
      </p>
    </div>
  </div>
</section>
""".format(anchor=anchor, heading=heading, tag=tag, lead=lead, url=SITE["booking_url"],
           full=" book--full" if full else "", ext=ic("arrow-square-out", "i--sm"),
           phone=SITE["phone"], phone_pretty=SITE["phone_pretty"], tg=SITE["telegram"])


def book_cta(title="Записаться на массаж"):
    """Лёгкая альтернатива встроенному виджету: не тянет сторонний iframe
    на каждую страницу, но ведёт ровно в ту же форму записи."""
    return """
<section class="sec sec--bcta" id="zapis">
  <div class="wrap">
    <div class="bcta">
      <div class="bcta__a">
        <h2>{title}</h2>
        <p>Форма записи связана с расписанием студии: свободные окна там всегда актуальные,
        а подтверждение приходит сразу. Занимает меньше минуты.</p>
        <div class="bcta__act">
          <a class="btn btn--gold btn--lg" href="/zapis/">Записаться</a>
          <a class="btn btn--ghost btn--lg" href="{tg}" target="_blank" rel="noopener">Написать в Telegram</a>
        </div>
      </div>
      <ul class="bcta__b">
        <li>{c}Скидка 15% на первый визит</li>
        <li>{c}Выбор мастера и удобного времени</li>
        <li>{c}Отмена и перенос без звонков</li>
        <li>{c}Или просто позвоните: <a class="lnk" href="tel:{phone}">{phone_pretty}</a></li>
      </ul>
    </div>
  </div>
</section>""".format(title=title, tg=SITE["telegram"], phone=SITE["phone"],
                     phone_pretty=SITE["phone_pretty"], c=ic("check", "i--sm"))


def pair_cta():
    return """
<section class="sec sec--bcta" id="zapis">
  <div class="wrap">
    <div class="bcta">
      <div class="bcta__a">
        <h2>Забронировать парный сеанс</h2>
        <p>Нужны два свободных мастера в одно окно, поэтому такое время мы собираем вручную.
        Напишите, на какой день рассчитываете, и мы предложим варианты.</p>
        <div class="bcta__act">
          <a class="btn btn--gold btn--lg" href="{tg}" target="_blank" rel="noopener">Написать в Telegram</a>
          <a class="btn btn--ghost btn--lg" href="tel:{phone}">Позвонить</a>
        </div>
      </div>
      <ul class="bcta__b">
        <li>{c}Два мастера работают одновременно</li>
        <li>{c}Программы можно выбрать разные</li>
        <li>{c}Скидка 15% на первый визит</li>
        <li>{c}Идёт как подарочный сертификат</li>
      </ul>
    </div>
  </div>
</section>""".format(tg=SITE["telegram"], phone=SITE["phone"], c=ic("check", "i--sm"))


def masters_block():
    return """
<section class="sec sec--masters">
  <div class="wrap">
    <div class="two">
      <div class="two__a">
        <h2>Мастера</h2>
        <p>В студии работают Марина и Елена. Обеих в отзывах хвалят одинаково часто:
        за спокойствие, за то, что спрашивают про ощущения по ходу сеанса, и за то,
        что находят зажимы, о которых человек сам не сказал.</p>
        <p class="two__note">При записи можно выбрать конкретного мастера или довериться
        расписанию. Парный сеанс делают обе одновременно.</p>
      </div>
      <div class="two__b">
        <ul class="marks">
          <li>{m}Работаем в комфортной для вас силе и уточняем ощущения по ходу</li>
          <li>{m}Не оцениваем тело и не навязываем дополнительные услуги</li>
          <li>{m}После сеанса рассказываем, что делать дома</li>
          <li>{m}Чистое бельё, тёплое масло, приглушённый свет</li>
        </ul>
      </div>
    </div>
  </div>
</section>""".format(m=ic("caret-right", "i--xs"))


def footer(hide_bar=False, data=""):
    links = "".join('<a href="%s">%s</a>' % (u, n) for n, u in MENU[:8])
    return """
</main>
<footer class="ftr">
  <div class="wrap ftr__in">
    <div class="ftr__brand">
      <span class="ftr__name">Твоё Время</span>
      <span class="ftr__sub">{tagline}</span>
      <address class="ftr__addr">
        {city}, {street}, {room}<br>
        {hours}<br>
        <a href="tel:{phone}">{phone_pretty}</a>
      </address>
      <div class="ftr__soc">
        <a href="{ig}" target="_blank" rel="noopener" aria-label="Instagram студии">{ig_i}</a>
        <a href="{th}" target="_blank" rel="noopener" aria-label="Threads студии">{th_i}</a>
        <a href="{tg}" target="_blank" rel="noopener" aria-label="Telegram студии">{tg_i}</a>
        <a href="tel:{phone}" aria-label="Позвонить в студию">{ph_i}</a>
      </div>
    </div>
    <nav class="ftr__nav" aria-label="Навигация в подвале">{links}</nav>
    <p class="ftr__legal">
      Студия массажа «Твоё Время», Минск. Услуги носят оздоровительный и релаксационный характер,
      не являются медицинскими и не заменяют консультацию врача. Перед курсом при хронических
      заболеваниях проконсультируйтесь со специалистом.
    </p>
  </div>
</footer>

<div class="bar{bar_cls}" aria-label="Быстрые действия">
  <a class="bar__i" href="tel:{phone}">{ph_i}<span>Позвонить</span></a>
  <a class="bar__i" href="{tg}" target="_blank" rel="noopener">{tg_i}<span>Telegram</span></a>
  <a class="bar__i bar__i--gold" href="/zapis/">Записаться</a>
</div>

<div class="grain" aria-hidden="true"></div>
{data}
<script src="/assets/js/app.js" defer></script>
</body>
</html>
""".format(tagline=SITE["tagline"], city=SITE["city"], street=SITE["street"],
           room=SITE["room"], hours=SITE["hours_human"], phone=SITE["phone"],
           phone_pretty=SITE["phone_pretty"], links=links,
           bar_cls=" bar--off" if hide_bar else "", data=data,
           ig=SITE["instagram"], th=SITE["threads"], tg=SITE["telegram"],
           ig_i=ic("instagram-logo"), th_i=ic("threads-logo"),
           tg_i=ic("telegram-logo"), ph_i=ic("phone"))


# ---------------------------------------------------------------------------
# переиспользуемые блоки
# ---------------------------------------------------------------------------
def program_card(key, page_slug=None, featured=False):
    p = PROGRAMS[key]
    link = ('<a class="pcard__more" href="%s">Подробнее о программе</a>'
            % prog_url(page_slug)) if page_slug else ""
    return """
<article class="pcard{fx}">
  <div class="pcard__top">
    <h3 class="pcard__name">{name}</h3>
    <p class="pcard__meta">{clock}<span>{dur}</span></p>
  </div>
  <p class="pcard__desc">{desc}</p>
  <div class="pcard__foot">
    <span class="pcard__price">{price}</span>
    <a class="btn btn--gold btn--sm" href="{book}">Записаться</a>
  </div>
  {link}
</article>""".format(fx=" pcard--fx" if featured else "", name=p["name"], dur=p["dur"],
                     desc=p["desc"], price=price(p["price"]), clock=ic("clock", "i--sm"),
                     book=zapis_url(key), link=link)


def reviews_block(limit=None):
    """Отзывы с Яндекс Карт. Сводка рейтинга сверху, дальше сетка цитат."""
    items = REVIEWS[:limit] if limit else REVIEWS
    cards = []
    for name, tag, text in items:
        stars = "".join(ic("star") for _ in range(5))
        cards.append("""
<figure class="rev">
  <div class="stars" aria-label="Оценка 5 из 5">{stars}</div>
  <blockquote>«{text}»</blockquote>
  <figcaption>{name} <span>{tag}</span></figcaption>
</figure>""".format(stars=stars, text=text, name=name, tag=tag))

    summary = """
    <div class="rsum">
      <div class="rsum__n">{rating}</div>
      <div class="rsum__b">
        <div class="stars" aria-label="Средняя оценка 5 из 5">{stars}</div>
        <p>{count} {w1} и {ratings} {w2} на Яндекс Картах.
        Их оставляют гости после визита, мы ничего не удаляем и не пишем сами.</p>
        <a class="lnk" href="{map}" target="_blank" rel="noopener">Читать все отзывы {ext}</a>
      </div>
    </div>""".format(rating=SITE["rating"], stars="".join(ic("star") for _ in range(5)),
                     count=SITE["reviews_count"], ratings=SITE["ratings_count"],
                     w1=plural(SITE["reviews_count"], "отзыв", "отзыва", "отзывов"),
                     w2=plural(SITE["ratings_count"], "оценка", "оценки", "оценок"),
                     map=SITE["yandex_map"], ext=ic("arrow-up-right", "i--sm"))

    return """
<section class="sec sec--otzyvy" id="otzyvy">
  <div class="wrap">
    <div class="sec__head"><h2>Что говорят гости</h2></div>
    {summary}
    <div class="revs">{cards}</div>
  </div>
</section>""".format(summary=summary, cards="".join(cards))


def faq_block(pairs, heading="Частые вопросы"):
    items = "".join("""
<details class="q">
  <summary>{q}{plus}</summary>
  <div class="q__a"><p>{a}</p></div>
</details>""".format(q=q, a=a, plus=ic("plus", "q__ic")) for q, a in pairs)
    return """
<section class="sec sec--faq" id="faq">
  <div class="wrap">
    <div class="sec__head"><h2>{h}</h2></div>
    <div class="faq">{items}</div>
  </div>
</section>""".format(h=heading, items=items)


def contacts_block(with_map=True):
    mp = """
      <div class="kont__map">
        <div class="kont__frame" data-map="https://yandex.by/map-widget/v1/?ll={lon}%2C{lat}&z=17&mode=poi&poi%5Bpoint%5D={lon}%2C{lat}&poi%5Buri%5D=ymapsbm1%3A%2F%2Forg%3Foid%3D84278277004"></div>
        <a class="kont__maplink" href="{map}" target="_blank" rel="noopener">Открыть в Яндекс Картах {ext}</a>
      </div>""".format(lon=SITE["lon"], lat=SITE["lat"], map=SITE["yandex_map"],
                       ext=ic("arrow-up-right", "i--sm")) if with_map else ""
    return """
<section class="sec sec--kont" id="kontakty">
  <div class="wrap">
    <div class="kont">
      <div class="kont__info">
        <h2>Записаться в «Твоё Время»</h2>
        <p class="lead">Напишите нам, если хотите записаться или не знаете, какая процедура подойдёт.
        Мы спокойно сориентируем по массажу, длительности и ближайшему времени.</p>
        <dl class="facts">
          <div>
            <dt>{pin}Адрес</dt>
            <dd>{city}, {street}, {room}<br><span class="facts__mute">{landmark}</span></dd>
          </div>
          <div>
            <dt>{ph}Телефон</dt>
            <dd><a href="tel:{phone}">{phone_pretty}</a></dd>
          </div>
          <div>
            <dt>{cl}Время работы</dt>
            <dd>{hours}<br><span class="facts__mute">Свободные окна видно в форме записи</span></dd>
          </div>
          <div>
            <dt>{ch}Мессенджеры</dt>
            <dd><a href="{tg}" target="_blank" rel="noopener">Telegram</a>
                <a href="{ig}" target="_blank" rel="noopener">Instagram</a>
                <a href="{th}" target="_blank" rel="noopener">Threads</a></dd>
          </div>
        </dl>
        <div class="kont__cta">
          <a class="btn btn--gold" href="/zapis/">Записаться</a>
          <a class="btn btn--ghost" href="{tg}" target="_blank" rel="noopener">Написать в Telegram</a>
        </div>
      </div>
      {mp}
    </div>
  </div>
</section>""".format(city=SITE["city"], street=SITE["street"], room=SITE["room"],
                     landmark=SITE["landmark"], phone=SITE["phone"],
                     phone_pretty=SITE["phone_pretty"], tg=SITE["telegram"],
                     ig=SITE["instagram"], th=SITE["threads"], mp=mp,
                     pin=ic("map-pin", "i--sm"), ph=ic("phone", "i--sm"),
                     cl=ic("clock", "i--sm"), hours=SITE["hours_human"],
                     ch=ic("chat-circle-text", "i--sm"))


def cta_strip(text="Не уверены, что подойдёт? Опишите, что беспокоит, и мы подскажем программу."):
    return """
<section class="strip">
  <div class="wrap strip__in">
    <p>{text}</p>
    <div class="strip__act">
      <a class="btn btn--gold" href="/zapis/">Записаться</a>
      <a class="btn btn--ghost" href="{tg}" target="_blank" rel="noopener">Написать в Telegram</a>
    </div>
  </div>
</section>""".format(text=text, tg=SITE["telegram"])


# ---------------------------------------------------------------------------
# страницы
# ---------------------------------------------------------------------------
def page_home():
    chips = "".join(
        '<button class="chip" type="button" aria-pressed="false" data-key="%s">%s</button>'
        % (k, label) for k, label, _e, _p, _w in PICKER)

    principles = "".join("""
<li class="step step--{i}">{icon}<h3>{t}</h3><p>{d}</p></li>""".format(
        i=i + 1, icon=ic(icon, "i--lg"), t=t, d=d)
        for i, (icon, t, d) in enumerate(PRINCIPLES))

    cat_cards = []
    for sp in SERVICE_PAGES:
        cheapest = (min(PROGRAMS[k]["price"] for k in sp["programs"])
                    if sp["programs"] else sp["from_price"])
        lead = (PROGRAMS[sp["programs"][0]]["desc"].split(".")[0] + "."
                if sp["programs"]
                else "Два мастера работают одновременно, сеанс у обоих начинается в одну минуту.")
        cat_cards.append("""
<a class="scard" href="{url}">
  <h3>{title}</h3>
  <p>{lead}</p>
  <span class="scard__from">от {price}</span>
</a>""".format(url=prog_url(sp["slug"]), title=sp["title"].replace(" в Минске", ""),
               lead=lead, price=price(cheapest)))

    body = """
<section class="hero" id="top">
  <div class="hero__media">
    <div class="hero__photo">
      <svg class="hero__frame" viewBox="0 0 400 520" preserveAspectRatio="none" aria-hidden="true" focusable="false">
        <path d="{frame}" fill="none" stroke="currentColor" stroke-width="1.4"
              stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>
      </svg>
      <span class="hero__shot">
      <img src="/assets/img/hero-960.jpg"
           srcset="/assets/img/hero-640.jpg 640w,
                   /assets/img/hero-960.jpg 960w,
                   /assets/img/hero-1280.jpg 1280w"
           sizes="(min-width: 900px) 42vw, 100vw"
           width="3024" height="4032"
           alt="Кабинет студии массажа «Твоё Время» в Минске: застеленный массажный стол, соляная лампа и живые растения в тёплом свете."
           fetchpriority="high" decoding="async">
      </span>
    </div>
  </div>
  <div class="hero__copy">
    <h1 class="hero__h1">Массаж и забота о&nbsp;теле в&nbsp;Минске</h1>
    <p class="hero__p">Поможем снять напряжение, восстановиться после нагрузки и подобрать массаж под ваше состояние.</p>
    <div class="hero__cta">
      <a class="btn btn--gold btn--lg" href="/zapis/">Записаться</a>
      <a class="btn btn--ghost btn--lg" href="#podbor">Подобрать массаж</a>
    </div>
  </div>
</section>

<section class="band" aria-label="Коротко о студии">
  <div class="band__grid">
    <div class="band__it">{i1}<span>Скидка 15% на первый визит</span></div>
    <div class="band__it">{i2}<span>Маяк Минска, рядом с Dana&nbsp;Mall</span></div>
    <div class="band__it">{i3}<span>Запись онлайн за минуту</span></div>
    <div class="band__it">{i4}<span>Абонементы от 5 сеансов</span></div>
  </div>
</section>

<section class="sec sec--picker" id="podbor">
  <div class="wrap">
    <div class="sec__head">
      <h2>Не знаете, какой массаж выбрать?</h2>
      <p class="lead">Мы подбираем процедуру под ваше состояние: шея и спина, усталость, отёки, тяжесть в теле или коррекция фигуры. Отметьте всё, что беспокоит, можно выбрать несколько пунктов сразу.</p>
    </div>
    <div class="picker">
      <div class="picker__chips" role="group" aria-label="Что вас беспокоит, можно отметить несколько">{chips}</div>
      <div class="picker__panel" id="pickerPanel" aria-live="polite">
        <div class="picker__empty">
          {leaf}
          <p>Не нужно разбираться в названиях. Отметьте, что беспокоит, и мы подскажем.</p>
          <a class="lnk" href="{tg}" target="_blank" rel="noopener">Написать в Telegram {ext}</a>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="sec sec--uslugi">
  <div class="wrap">
    <div class="sec__head">
      <h2>Услуги и цены</h2>
      <p class="lead">Выберите направление или напишите нам — подскажем, какая процедура лучше подойдёт под ваш запрос. Цены в белорусских рублях за один сеанс, на первый визит скидка 15%.</p>
    </div>
    <div class="scards">{cats}</div>
    <p class="note"><a class="lnk" href="/uslugi/">Весь прайс на одной странице {ext}</a></p>
  </div>
</section>

<section class="sec sec--zabota" id="zabota">
  <div class="wrap">
    <div class="sec__head">
      <h2>Почему у нас спокойно</h2>
      <p class="lead">Пять вещей, из-за которых у нас спокойно даже тем, кто идёт на массаж впервые.</p>
    </div>
    <ol class="steps">{principles}</ol>
  </div>
</section>

<section class="sec sec--studio" id="studio">
  <div class="wrap">
    <div class="sec__head">
      <h2>Новое пространство. Теплый свет. Мягкость. Покой. Забота.</h2>
      <p class="lead">Студия массажа «Твоё Время» на Маяке Минска. Приглушённая музыка, чистое бельё и тёплое масло. Будем рады видеть вас на нашем новом, прекрасном месте.</p>
    </div>
  </div>
  <div class="gallery" role="group" tabindex="0" aria-label="Фотографии студии, прокручивается по горизонтали">
    <figure><img src="/assets/img/mood-curtains.jpg" width="240" height="426" alt="Зона отдыха студии массажа с мягкими шторами и приглушённым светом." loading="lazy" decoding="async"></figure>
    <figure><img src="/assets/img/mood-back.jpg" width="240" height="426" alt="Мастер выполняет массаж спины при свечах." loading="lazy" decoding="async"></figure>
    <figure><img src="/assets/img/mood-face.jpg" width="240" height="425" alt="Массаж лица в кабинете студии «Твоё Время»." loading="lazy" decoding="async"></figure>
    <figure><img src="/assets/img/mood-lounge.jpg" width="240" height="320" alt="Диван и сухоцветы в зоне ожидания студии." loading="lazy" decoding="async"></figure>
  </div>
</section>

{masters}
{reviews}
{booking}
{faq}
{contacts}
""".format(frame=FRAME_PATH, chips=chips, principles=principles, cats="".join(cat_cards),
           leaf=ic("leaf", "i--xl"), tg=SITE["telegram"], ext=ic("arrow-up-right", "i--sm"),
           i1=ic("sparkle"), i2=ic("map-pin"), i3=ic("calendar-check"), i4=ic("ticket"),
           masters=masters_block(), reviews=reviews_block(), booking=booking(),
           faq=faq_block(FAQ_MAIN), contacts=contacts_block())

    schema = [
        business_schema(),
        {"@type": "WebSite", "@id": D + "/#website", "url": D + "/", "name": SITE["name"],
         "inLanguage": "ru-BY", "publisher": {"@id": BUSINESS_ID}},
        offer_catalog(),
        faq_schema(FAQ_MAIN),
    ]
    preload = ('<link rel="preload" as="image" fetchpriority="high" '
               'href="/assets/img/hero-960.jpg" '
               'imagesrcset="/assets/img/hero-640.jpg 640w, '
               '/assets/img/hero-960.jpg 960w, '
               '/assets/img/hero-1280.jpg 1280w" '
               'imagesizes="(min-width: 900px) 42vw, 100vw">')
    return head(
        "Студия массажа «Твоё Время» в Минске | Маяк Минска, Петра Мстиславца 18",
        "Студия массажа в Минске на Маяке Минска. Классический массаж, массаж лица, "
        "коррекция фигуры, спортивный и миофасциальный массаж от 40 р. Онлайн-запись "
        "и скидка 15% на первый визит.",
        "/", schema, hero_preload=preload) + header() + body \
        + footer(data=services_json() + picker_json())


def page_uslugi():
    groups = []
    for sp in SERVICE_PAGES:
        if sp["programs"]:
            cards = "".join(program_card(k) for k in sp["programs"])
        else:
            cards = "".join("""
<article class="pcard">
  <div class="pcard__top">
    <h3 class="pcard__name">{n}</h3>
    <p class="pcard__meta">{clock}<span>{d}</span></p>
  </div>
  <p class="pcard__desc">Два мастера работают одновременно, сеанс у обоих начинается
  и заканчивается в одну минуту.</p>
  <div class="pcard__foot">
    <span class="pcard__price">{p}</span>
    <a class="btn btn--gold btn--sm" href="{tg}" target="_blank" rel="noopener">Забронировать</a>
  </div>
</article>""".format(n=n, d=d, p=price(v), clock=ic("clock", "i--sm"), tg=SITE["telegram"])
                for n, d, v in PAIR_EXAMPLES)
        groups.append("""
<section class="pgroup">
  <div class="pgroup__head">
    <h2><a href="{url}">{title}</a></h2>
    <p>{lead}</p>
  </div>
  <div class="pcards">{cards}</div>
</section>""".format(url=prog_url(sp["slug"]), title=sp["title"].replace(" в Минске", ""),
                     lead=sp["lead"], cards=cards))

    body = crumbs([("Услуги и цены", "/uslugi/")]) + """
<section class="sec sec--top">
  <div class="wrap">
    <div class="sec__head">
      <h1>Массаж в Минске: программы и цены</h1>
      <p class="lead">Десять программ, собранных под разные состояния: от двадцатиминутного знакомства
      до полутора часов Signature. Цены в белорусских рублях за сеанс, на первый визит скидка 15%.</p>
    </div>
    <div class="pgroups">{groups}</div>
  </div>
</section>
{strip}
{booking}
{contacts}
""".format(groups="".join(groups), strip=cta_strip(), booking=book_cta(),
           contacts=contacts_block())

    schema = [business_schema(), offer_catalog(),
              crumbs_schema([("Главная", "/"), ("Услуги и цены", "/uslugi/")])]
    return head(
        "Массаж в Минске: цены и программы | Студия «Твоё Время»",
        "Все программы массажа в Минске с ценами: спина и шея от 40 р., общий массаж 75 р., "
        "массаж лица 70 р., антицеллюлитный и лимфодренажный 75 р., Signature 110 р. "
        "Онлайн-запись.",
        "/uslugi/", schema) + header() + body + footer(data=services_json())


def page_service(sp):
    pair = sp.get("pair")
    if pair:
        rows = "".join("""
<li class="pair__r">
  <span class="pair__n">{n}</span>
  <span class="pair__d">{d}</span>
  <span class="pair__p">{p}</span>
</li>""".format(n=n, d=d, p=price(v)) for n, d, v in PAIR_EXAMPLES)
        cards = """
<div class="pair">
  <ul class="pair__list">{rows}</ul>
  <p class="pair__note">Стоимость складывается из двух выбранных программ, поэтому набрать
  можно любую пару из <a class="lnk" href="/uslugi/">прайса</a>. На первый визит скидка 15%.</p>
  <div class="pair__act">
    <a class="btn btn--gold btn--lg" href="{tg}" target="_blank" rel="noopener">Забронировать в Telegram</a>
    <a class="btn btn--ghost btn--lg" href="tel:{phone}">Позвонить</a>
  </div>
</div>""".format(rows=rows, tg=SITE["telegram"], phone=SITE["phone"])
    else:
        cards = '<div class="pcards pcards--top">%s</div>' % "".join(
            program_card(k) for k in sp["programs"])

    when = "".join('<li>%s%s</li>' % (ic("caret-right", "i--xs"), w) for w in sp["when"])
    how = "".join('<li class="how__i"><h3>{t}</h3><p>{d}</p></li>'.format(t=t, d=d)
                  for t, d in sp["how"])
    rel = "".join('<a class="rel__i" href="%s"><span>%s</span>%s</a>'
                  % (prog_url(s), next(x["title"].replace(" в Минске", "")
                                       for x in SERVICE_PAGES if x["slug"] == s),
                     ic("arrow-up-right", "i--sm"))
                  for s in sp["related"])

    body = crumbs([("Услуги и цены", "/uslugi/"),
                   (sp["title"].replace(" в Минске", ""), prog_url(sp["slug"]))]) + """
<section class="sec sec--top">
  <div class="wrap">
    <div class="sec__head">
      <h1>{h1}</h1>
      <p class="lead lead--big">{lead}</p>
    </div>
    {cards}
  </div>
</section>

<section class="sec sec--when">
  <div class="wrap">
    <div class="two">
      <div class="two__a">
        <h2>Когда стоит прийти</h2>
        <ul class="marks">{when}</ul>
      </div>
      <div class="two__b">
        <h2>Сколько нужно сеансов</h2>
        <p>{course}</p>
        <p class="two__note">На курс выгоднее взять <a class="lnk" href="/abonementy/">абонемент</a>:
        от 5 сеансов скидка 10%, от 10 сеансов скидка 15%.</p>
      </div>
    </div>
  </div>
</section>

<section class="sec sec--how">
  <div class="wrap">
    <div class="sec__head"><h2>Как проходит сеанс</h2></div>
    <ol class="how">{how}</ol>
  </div>
</section>

{booking}
{faq}

<section class="sec sec--rel">
  <div class="wrap">
    <div class="sec__head"><h2>Смотрите также</h2></div>
    <div class="rel">{rel}</div>
  </div>
</section>

{reviews}
{contacts}
""".format(h1=sp["h1"], lead=sp["lead"], cards=cards, when=when, course=sp["course"],
           how=how, rel=rel,
           booking=(pair_cta() if pair
                    else book_cta("Записаться: " + sp["title"].replace(" в Минске", "").lower())),
           faq=faq_block(sp["faq"]), reviews=reviews_block(limit=6),
           contacts=contacts_block(with_map=False))

    service_node = {
        "@type": "Service",
        "name": sp["title"],
        "serviceType": sp["title"],
        "description": sp["meta_desc"],
        "provider": {"@id": BUSINESS_ID},
        "areaServed": {"@type": "City", "name": "Минск"},
        "url": D + prog_url(sp["slug"]),
        "offers": ([{
            "@type": "Offer", "priceCurrency": "BYN", "price": str(v), "name": n,
            "url": D + prog_url(sp["slug"]), "availability": "https://schema.org/InStock",
        } for n, _d, v in PAIR_EXAMPLES] if pair else [{
            "@type": "Offer", "priceCurrency": "BYN", "price": str(PROGRAMS[k]["price"]),
            "name": PROGRAMS[k]["name"], "url": D + "/zapis/",
            "availability": "https://schema.org/InStock",
        } for k in sp["programs"]]),
    }
    schema = [business_schema(), service_node, faq_schema(sp["faq"]),
              crumbs_schema([("Главная", "/"), ("Услуги и цены", "/uslugi/"),
                             (sp["title"].replace(" в Минске", ""), prog_url(sp["slug"]))])]
    return head(sp["meta_title"], sp["meta_desc"], prog_url(sp["slug"]), schema) \
        + header() + body + footer(data=services_json())


def page_zapis():
    body = crumbs([("Онлайн-запись", "/zapis/")]) + booking(
        heading="Онлайн-запись на массаж в Минске", tag="h1", full=True,
        lead="Выберите программу, мастера и удобное время. Форма связана напрямую с расписанием "
             "студии, поэтому свободные окна здесь всегда актуальные, а подтверждение приходит сразу."
    ) + """
<section class="sec sec--help">
  <div class="wrap">
    <div class="sec__head"><h2>Если удобнее не через форму</h2></div>
    <div class="ways">
      <a class="way" href="tel:{phone}">{ph}<span class="way__t">Позвонить</span><span class="way__d">{phone_pretty}</span></a>
      <a class="way" href="{tg}" target="_blank" rel="noopener">{tg_i}<span class="way__t">Telegram</span><span class="way__d">Ответим и поможем выбрать программу</span></a>
      <a class="way" href="{ig}" target="_blank" rel="noopener">{ig_i}<span class="way__t">Instagram</span><span class="way__d">Пишите в Direct, там же фото студии</span></a>
      <a class="way" href="{th}" target="_blank" rel="noopener">{th_i}<span class="way__t">Threads</span><span class="way__d">Тоже читаем и отвечаем</span></a>
    </div>
    <p class="note">Не знаете, что выбрать? <a class="lnk" href="/#podbor">Пройдите короткий подбор</a>,
    он занимает меньше минуты и сразу покажет программу с ценой.</p>
  </div>
</section>
{faq}
{contacts}
""".format(phone=SITE["phone"], phone_pretty=SITE["phone_pretty"], tg=SITE["telegram"],
           ig=SITE["instagram"], th=SITE["threads"], ph=ic("phone", "i--lg"),
           tg_i=ic("telegram-logo", "i--lg"), ig_i=ic("instagram-logo", "i--lg"),
           th_i=ic("threads-logo", "i--lg"),
           faq=faq_block(FAQ_MAIN[3:], heading="Перед первым визитом"),
           contacts=contacts_block())

    schema = [business_schema(), faq_schema(FAQ_MAIN[3:]),
              crumbs_schema([("Главная", "/"), ("Онлайн-запись", "/zapis/")])]
    return head(
        "Онлайн-запись на массаж в Минске | Студия «Твоё Время»",
        "Запишитесь на массаж в Минске онлайн за минуту: выбор программы, мастера и времени. "
        "Студия «Твоё Время», ул. Петра Мстиславца, 18. Скидка 15% на первый визит.",
        "/zapis/", schema) + header() + body + footer(hide_bar=True, data=services_json())


def page_abonementy():
    body = crumbs([("Абонементы и сертификаты", "/abonementy/")]) + """
<section class="sec sec--top">
  <div class="wrap">
    <div class="sec__head">
      <h1>Абонементы и подарочные сертификаты</h1>
      <p class="lead lead--big">Для тех, кто хочет сделать массаж регулярной заботой о теле.
      Абонемент делает курс дешевле, а сертификат превращает его в спокойный и красивый
      подарок для тех, кому хочется отдыха, восстановления и немного времени для себя.</p>
    </div>

    <div class="duo">
      <article class="panel panel--abon">
        <h2>Абонемент</h2>
        <p class="panel__p">Для тех, кто хочет сделать массаж регулярной заботой о теле.
        Сеансы можно тратить на разные программы.</p>
        <div class="tiers">
          <div class="tier"><span class="tier__k">от 5 сеансов</span><span class="tier__v">−10%</span><span class="tier__p">от 180&nbsp;р.</span></div>
          <div class="tier"><span class="tier__k">от 10 сеансов</span><span class="tier__v">−15%</span><span class="tier__p">от 340&nbsp;р.</span></div>
        </div>
        <ul class="ticks">
          <li>{c}Срок действия — 3 месяца</li>
          <li>{c}Возможна оплата частями</li>
          <li>{c}Можно оформить в бумажном или электронном виде</li>
          <li>{c}Можно комбинировать разные программы</li>
        </ul>
      </article>

      <article class="panel panel--cert">
        {gift}
        <h2>Подарочные сертификаты</h2>
        <p class="panel__p">Спокойный и красивый подарок для тех, кому хочется отдыха,
        восстановления и немного времени для себя. Сертификат можно оформить на процедуру
        или сумму. Чаще всего дарят <a class="lnk" href="/uslugi/signature/">Signature
        на 90 минут</a>.</p>
        <a class="btn btn--gold" href="{tg}" target="_blank" rel="noopener">Оформить сертификат</a>
      </article>
    </div>
  </div>
</section>

<section class="sec sec--how">
  <div class="wrap">
    <div class="sec__head"><h2>Кому абонемент правда выгоден</h2></div>
    <ol class="how">
      <li class="how__i"><h3>Коррекция фигуры</h3><p>Антицеллюлитный интенсив и лимфодренаж работают
      курсом из 10 сеансов. На этом объёме скидка 15% экономит больше сотни рублей.</p></li>
      <li class="how__i"><h3>Курс для лица</h3><p>Заметный накопительный эффект по тонусу и отёчности
      даёт курс из 8 или 10 сеансов дважды в неделю.</p></li>
      <li class="how__i"><h3>Хроническая спина</h3><p>Если шея и поясница беспокоят давно, пять сеансов
      раз в неделю дают результат, который держится месяцами.</p></li>
      <li class="how__i"><h3>Регулярное восстановление</h3><p>Тем, кто тренируется, удобно держать
      абонемент и приходить раз в неделю, не думая об оплате каждый раз.</p></li>
    </ol>
  </div>
</section>

{strip}
{booking}
{contacts}
""".format(c=ic("check", "i--sm"), gift=ic("gift", "i--xl"), tg=SITE["telegram"],
           strip=cta_strip("Не знаете, какой абонемент подойдёт? Напишите, посчитаем вместе."),
           booking=book_cta(), contacts=contacts_block(with_map=False))

    schema = [business_schema(),
              crumbs_schema([("Главная", "/"), ("Абонементы и сертификаты", "/abonementy/")])]
    return head(
        "Абонементы и подарочные сертификаты на массаж в Минске | «Твоё Время»",
        "Абонемент на массаж в Минске: от 5 сеансов скидка 10%, от 10 сеансов 15%, "
        "срок действия 3 месяца, оплата частями. Подарочный сертификат на программу или на сумму.",
        "/abonementy/", schema) + header() + body + footer(data=services_json())


def page_kontakty():
    body = crumbs([("Контакты", "/kontakty/")]) + """
<section class="sec sec--top">
  <div class="wrap">
    <div class="sec__head">
      <h1>Контакты студии «Твоё Время»</h1>
      <p class="lead lead--big">Минск, улица Петра Мстиславца, 18, помещение 417.
      Это Маяк Минска: рядом Dana Mall и Национальная библиотека.</p>
    </div>
  </div>
</section>
{contacts}

<section class="sec sec--how">
  <div class="wrap">
    <div class="sec__head"><h2>Как добраться</h2></div>
    <ol class="how">
      <li class="how__i"><h3>На машине</h3><p>Ориентир Dana Mall. У дома есть парковка,
      вечером места обычно свободны.</p></li>
      <li class="how__i"><h3>На метро</h3><p>От станции «Восток» около 500 метров пешком,
      это минут семь в сторону Национальной библиотеки. Ближайшая остановка транспорта
      «Петра Мстиславца» в 340 метрах.</p></li>
      <li class="how__i"><h3>В доме</h3><p>Вход со стороны двора, помещение 417.
      Если не нашли с первого раза, позвоните, встретим.</p></li>
      <li class="how__i"><h3>Перед визитом</h3><p>Приходите за несколько минут до начала,
      чтобы не заходить в кабинет прямо с улицы и успеть выдохнуть.</p></li>
    </ol>
  </div>
</section>
{booking}
""".format(contacts=contacts_block(), booking=book_cta())

    schema = [business_schema(),
              crumbs_schema([("Главная", "/"), ("Контакты", "/kontakty/")])]
    return head(
        "Контакты студии массажа «Твоё Время» в Минске | Петра Мстиславца, 18",
        "Адрес студии массажа «Твоё Время»: Минск, ул. Петра Мстиславца, 18, помещение 417, "
        "Маяк Минска. Телефон +375 29 676-26-30, Telegram, онлайн-запись и карта проезда.",
        "/kontakty/", schema) + header() + body + footer(data=services_json())


# ---------------------------------------------------------------------------
# запись файлов
# ---------------------------------------------------------------------------
def write(rel_path, html):
    full = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(html)
    return rel_path


def main():
    pages = []
    pages.append(("/", write("index.html", page_home())))
    pages.append(("/uslugi/", write("uslugi/index.html", page_uslugi())))
    for sp in SERVICE_PAGES:
        pages.append((prog_url(sp["slug"]),
                      write("uslugi/%s/index.html" % sp["slug"], page_service(sp))))
    pages.append(("/zapis/", write("zapis/index.html", page_zapis())))
    pages.append(("/abonementy/", write("abonementy/index.html", page_abonementy())))
    pages.append(("/kontakty/", write("kontakty/index.html", page_kontakty())))

    prio = {"/": "1.0", "/uslugi/": "0.9", "/zapis/": "0.9"}
    urls = "".join(
        "\n  <url><loc>%s%s</loc><lastmod>%s</lastmod>"
        "<changefreq>monthly</changefreq><priority>%s</priority></url>"
        % (D, u, TODAY, prio.get(u, "0.8")) for u, _ in pages)
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s\n</urlset>\n' % urls)

    open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % D)

    p404 = head("Страница не найдена | Студия массажа «Твоё Время» в Минске",
                "Такой страницы нет. Посмотрите программы массажа и цены или запишитесь онлайн "
                "в студию «Твоё Время» на Маяке Минска.",
                "/404.html", [business_schema()])
    p404 = p404.replace("<title>", '<meta name="robots" content="noindex">\n<title>')
    write("404.html", p404 + header() + """
<section class="sec sec--top">
  <div class="wrap">
    <div class="sec__head">
      <h1>Такой страницы нет</h1>
      <p class="lead">Возможно, ссылка устарела. Посмотрите программы и цены или запишитесь онлайн.</p>
    </div>
    <div class="hero__cta">
      <a class="btn btn--gold btn--lg" href="/uslugi/">Программы и цены</a>
      <a class="btn btn--ghost btn--lg" href="/">На главную</a>
    </div>
  </div>
</section>
""" + footer())

    print("Собрано страниц: %d" % (len(pages) + 1))
    for u, f in pages:
        print("  %-42s %s" % (u, f))
    print("  sitemap.xml, robots.txt, 404.html")


if __name__ == "__main__":
    main()

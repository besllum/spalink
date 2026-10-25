#!/usr/bin/env python3
"""Erzeugt die statische Website in public/ aus data/ und den Originalfotos in ../medien.
Aufruf:  python3 build.py
"""
import json, re, os, html, shutil, unicodedata, hashlib
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
MEDIA = ROOT.parent / "medien"          # Originale (nicht im Repository)
OUT = ROOT / "public"
SITE = "https://spalink-sievers.de"
NAME = "SPALINK-SIEVERS LandschaftsArchitekten"
SIZES = (480, 960, 1600)
Image.MAX_IMAGE_PIXELS = None

E = html.escape
N = lambda s: unicodedata.normalize("NFC", s)

def slugify(s):
    s = N(s).lower()
    for a, b in (("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:80] or "x"

# ---------- Bilder ----------
_media_index = None
def media_path(rel):
    """Findet eine Originaldatei in ../medien (Unicode-tolerant)."""
    global _media_index
    if _media_index is None:
        _media_index = {N(str(p.relative_to(MEDIA))): p for p in MEDIA.rglob("*") if p.is_file()}
    r = _media_index.get(N(rel))
    if not r:  # WordPress-Zwischengröße (z. B. -300x225) -> Original
        r = _media_index.get(N(re.sub(r"-\d+x\d+(\.\w+)$", r"\1", rel)))
    return r

def img(rel, alt="", sizes="(max-width: 760px) 100vw, 50vw", cls="", eager=False):
    """Erzeugt WebP-Varianten und gibt ein <img> mit srcset zurück."""
    info = image_variants(rel)
    if not info:
        return ""
    srcset = ", ".join(f"/{u} {w}w" for u, w in info["v"])
    mid = info["v"][min(1, len(info["v"]) - 1)][0]
    return (f'<img src="/{mid}" srcset="{srcset}" sizes="{sizes}" width="{info["w"]}" height="{info["h"]}" '
            f'alt="{E(alt)}"{" class=%s" % cls if cls else ""} {"fetchpriority=high" if eager else "loading=lazy"} decoding="async">')

_cache = {}
def image_variants(rel):
    if rel in _cache:
        return _cache[rel]
    src = media_path(rel)
    if not src:
        print("  ! Bild fehlt:", rel); _cache[rel] = None; return None
    stem = Path(rel).with_suffix("")
    base = f"img/{stem.parent.as_posix()}/{slugify(stem.name)}"
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "transparency" in im.info or im.mode in ("P", "LA") else "RGB")
        W, H = im.size
        v = []
        for w in SIZES:
            if w > W and v:
                break
            tw = min(w, W)
            out = OUT / f"{base}-{tw}.webp"
            if not out.exists():
                out.parent.mkdir(parents=True, exist_ok=True)
                im.resize((tw, round(H * tw / W)), Image.LANCZOS).save(out, "WEBP", quality=80, method=5)
            v.append((f"{base}-{tw}.webp", tw))
    _cache[rel] = {"v": v, "w": W, "h": H}
    return _cache[rel]

def largest(rel):
    i = image_variants(rel)
    return "/" + i["v"][-1][0] if i else ""

# ---------- Seitenrahmen ----------
NAV = [("Aktuell", "/aktuell/"), ("Über uns", "/ueber-uns/"), ("Projekte", "/projekte/"),
       ("Presse", "/presse/"), ("Team", "/team/"), ("Kontakt", "/kontakt/")]

def subnav_presse(current):
    items = [("Presseberichte", "/presse/"), ("Veröffentlichungen", "/veroeffentlichungen/")]
    return '<nav class="subnav" aria-label="Presse">' + "".join(
        f'<a href="{u}"{" aria-current=page" if u == current else ""}>{n}</a>' for n, u in items) + "</nav>"

def layout(path, title, desc, body, active=None, og_image="", jsonld=None):
    full_title = title if ("SPALINK" in title and "SIEVERS" in title) else f"{title} | SPALINK-SIEVERS"
    if len(desc) < 70:  # zu kurze Beschreibungen ergänzen
        desc = (desc.rstrip(" .") + ". " if desc else "") + "SPALINK-SIEVERS LandschaftsArchitekten, Hannover – Freiraumplanung seit 1991."
    if len(desc) > 160:
        desc = desc[:157].rsplit(" ", 1)[0] + " …"
    body = re.sub(r'(<img [^>]*?)alt=""', lambda m: m.group(1) + f'alt="{E(title)}"', body)  # fehlende Alt-Texte
    nav = "".join(f'<li><a href="{u}"{" aria-current=page" if u == active else ""}>{E(n)}</a></li>' for n, u in NAV)
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    og = f'<meta property="og:image" content="{SITE}{og_image}">' if og_image else ""
    page = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(full_title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{SITE}{path}">
<meta property="og:type" content="website"><meta property="og:locale" content="de_DE"><meta property="og:site_name" content="{NAME}">
<meta property="og:title" content="{E(full_title)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{SITE}{path}">{og}
<link rel="preload" href="/assets/fonts/open-sans-latin-300-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/style.css?v={ASSET_V}">
<link rel="icon" href="/favicon.png" sizes="32x32"><link rel="icon" href="/icon-192.png" sizes="192x192"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
{ld}
</head>
<body>
<a class="skip" href="#inhalt">Zum Inhalt springen</a>
<header class="site-header">
 <div class="wrap">
  <a class="logo" href="/"><img src="/assets/logo.png" width="760" height="56" alt="{NAME}"></a>
  <button class="nav-toggle" aria-label="Menü" aria-expanded="false" aria-controls="nav"><span></span><span></span><span></span></button>
  <nav class="nav" id="nav" aria-label="Hauptmenü"><ul>{nav}</ul></nav>
 </div>
</header>
<main id="inhalt">
{body}
</main>
<footer class="site-footer">
 <div class="wrap">
  <div><strong>{NAME}</strong><br>Alte Herrenhäuser Str. 28 · 30419 Hannover<br>Telefon <a href="tel:+495119792590">0511 979 259-0</a> · <a href="mailto:info@spalink-sievers.de">info@spalink-sievers.de</a></div>
  <nav class="legal" aria-label="Rechtliches"><ul>
   <li><a href="/impressum/">Impressum</a></li>
   <li><a href="/datenschutz/">Datenschutzerklärung</a></li>
   <li><a href="/datenschutz/#cookies">Cookies</a></li>
   <li><a href="/datenschutz/#hosting">Hosting</a></li>
  </ul></nav>
  <p class="copy">© {YEAR} {NAME} · Diese Website setzt keine Cookies und verwendet kein Tracking.</p>
 </div>
</footer>
<script src="/assets/main.js?v={ASSET_V}" defer></script>
</body>
</html>"""
    write(path, page)

PAGES = []
def write(path, content):
    f = OUT / path.strip("/") / "index.html" if path.endswith("/") else OUT / path.strip("/")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")
    if path.endswith("/"):
        PAGES.append(path)

ORG = {"@context": "https://schema.org", "@type": "LandscapeArchitect" if False else "ProfessionalService",
       "name": NAME, "url": SITE + "/", "telephone": "+49 511 979259-0", "email": "info@spalink-sievers.de",
       "foundingDate": "1991",
       "address": {"@type": "PostalAddress", "streetAddress": "Alte Herrenhäuser Str. 28",
                   "postalCode": "30419", "addressLocality": "Hannover", "addressCountry": "DE"}}

# ---------- Inhalte aus dem alten Seitenbaukasten (WPBakery) ----------
WP = json.loads((ROOT / "data/wp-export.json").read_text())
MEDIA_BY_ID = {m["id"]: N(re.sub(r"^.*/wp-content/uploads/", "", m["url"])) for m in WP["media"]}
from urllib.parse import unquote
MEDIA_BY_ID = {k: unquote(v) for k, v in MEDIA_BY_ID.items()}

SLUG_MAP = {"uber-uns": "ueber-uns", "datenschutzerklaerung": "datenschutz", "spalink-sievers-landschaftsarchitekten": ""}

def fix_links(h):
    def doc(m):
        rel = unquote(m.group(1))
        src = media_path(rel)
        if src and src.suffix.lower() == ".pdf":
            dst = OUT / "dokumente" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists(): shutil.copy2(src, dst)
            return f'/dokumente/{rel}'
        return largest(rel) or m.group(0)
    h = re.sub(r'https?://(?:www\.)?spalink-sievers\.de/wp-content/uploads/([^"\'\s<>]+)', doc, h)
    h = re.sub(r'https?://(?:www\.)?spalink-sievers\.de/projects/([^"/]+)/?', lambda m: f"/projekte/{PROJECT_SLUG.get(m.group(1), m.group(1))}/", h)
    h = re.sub(r'https?://(?:www\.)?spalink-sievers\.de/([a-z0-9\-]+)/?(?=["#])', lambda m: f"/{SLUG_MAP.get(m.group(1), m.group(1))}/".replace("//", "/"), h)
    h = re.sub(r'https?://(?:www\.)?spalink-sievers\.de/?(?=")', "/", h)
    h = re.sub(r'\s(style|class)="[^"]*"', "", h)
    return h

def autop(t):
    t = t.replace("&nbsp;", " ").strip()
    if not t: return ""
    blocks = re.split(r"\n\s*\n", t)
    out = []
    for b in blocks:
        b = b.strip()
        if not b: continue
        if re.match(r"<(p|h\d|ul|ol|div|table|figure|blockquote)\b", b):
            out.append(re.sub(r"(?<!>)\n(?!<)", "<br>\n", b))
        else:
            out.append("<p>" + b.replace("\n", "<br>\n") + "</p>")
    return "\n".join(out)

TOKEN = re.compile(r"\[(/?)(vc_\w+)([^\]]*)\]")
def attrs(s):
    return dict(re.findall(r'(\w+)="([^"]*)"', s))

def parse_vc(raw):
    root = {"tag": "root", "a": {}, "kids": []}
    stack = [root]; pos = 0
    for m in TOKEN.finditer(raw):
        txt = raw[pos:m.start()]
        if txt.strip(): stack[-1]["kids"].append(txt)
        pos = m.end()
        close, tag, at = m.group(1), m.group(2), m.group(3)
        if close:
            while len(stack) > 1:
                n = stack.pop()
                if n["tag"] == tag: break
        else:
            node = {"tag": tag, "a": attrs(at), "kids": []}
            stack[-1]["kids"].append(node)
            if tag not in ("vc_single_image", "vc_empty_space", "vc_separator", "vc_video", "vc_btn", "vc_gallery"):
                stack.append(node)
    if raw[pos:].strip(): stack[-1]["kids"].append(raw[pos:])
    return root

FRAC = {"1/2": .5, "1/3": 1/3, "2/3": 2/3, "1/4": .25, "3/4": .75, "1/6": 1/6, "5/6": 5/6}
MAP_Q = "Alte+Herrenh%C3%A4user+Str.+28%2C+30419+Hannover"
MAP_BLOCK = ('<div class="map" data-src="https://www.google.com/maps?q=' + MAP_Q + '&amp;z=16&amp;output=embed">'
  '<div class="map-ph"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>'
  '<p><strong>Unser Büro auf der Karte</strong><br>Alte Herrenhäuser Str. 28 · 30419 Hannover-Herrenhausen</p>'
  '<button type="button" class="map-load">Karte laden</button>'
  '<p class="map-note">Beim Laden der Karte werden Daten (u. a. Ihre IP-Adresse) an Google übertragen. '
  'Mehr dazu in der <a href="/datenschutz/#google-maps">Datenschutzerklärung</a>. '
  'Oder: <a href="https://www.google.com/maps/search/?api=1&amp;query=' + MAP_Q + '" target="_blank" rel="noopener">in Google Maps öffnen</a>.</p></div></div>')

# Austausch einzelner Fotos ohne Änderung der Seiteninhalte (alt -> neu, Pfade in ../medien)
IMAGE_OVERRIDE = {
    "2026/10/Alina.jpg": "2026/10/team-alina-2026.jpg",
    "2025/12/timo.jpg": "2026/10/team-timo-2026.jpg",
    "2020/07/pucky3.jpg": "2020/07/pucky-quadrat.jpg",
}

def render_vc(node, alt=""):
    if isinstance(node, str):
        # Karten-Shortcode des alten Themes -> einfacher Link (keine eingebettete Karte = keine Cookies)
        node = re.sub(r"\[sth_googlemap[^\]]*\]\[/sth_googlemap\]|\[sth_googlemap[^\]]*\]",
                      "%%MAP%%", node)
        node = re.sub(r"\[/?sth_[^\]]*\]", "", node)  # übrige Theme-Shortcodes entfernen
        out = autop(fix_links(node))
        return re.sub(r"(<p>)?\s*%%MAP%%\s*(</p>|<br>)?", lambda m: MAP_BLOCK, out)
    t, a, kids = node["tag"], node["a"], node["kids"]
    inner = lambda: "".join(render_vc(k, alt) for k in kids)
    if t in ("root",): return inner()
    if t in ("vc_row", "vc_row_inner"): 
        c = inner().strip()
        return f'<div class="wp-row">{c}</div>' if c else ""
    if t in ("vc_column", "vc_column_inner"):
        c = inner().strip()
        return f'<div class="wp-col" style="--w:{FRAC.get(a.get("width"), 1):.4f}">{c}</div>' if c else ""
    if t == "vc_column_text": return f'<div class="prose">{inner()}</div>'
    if t == "vc_single_image":
        rel = MEDIA_BY_ID.get(int(a.get("image", 0) or 0))
        rel = IMAGE_OVERRIDE.get(rel, rel)
        return f"<figure>{img(rel, alt)}</figure>" if rel else ""
    if t == "vc_gallery":
        return "".join(f"<figure>{img(MEDIA_BY_ID[int(i)], alt)}</figure>" for i in a.get("images", "").split(",") if i.isdigit() and int(i) in MEDIA_BY_ID)
    if t == "vc_video":
        return f'<a class="video-link" href="{E(a.get("link",""))}" target="_blank" rel="noopener">▶ Video ansehen</a>'
    if t == "vc_btn":
        url = unquote(re.search(r"url:([^|]*)", a.get("link", "url:")).group(1))
        return f'<a class="btn" href="{E(fix_links(url))}">{E(a.get("title","Mehr"))}</a>'
    if t == "vc_separator": return "<hr>"
    if t == "vc_empty_space": return ""
    return inner()

def text_of(h):
    t = re.sub(r"\[[^\]]+\]", " ", h); t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

# ---------- Projekte ----------
PJ = json.loads((ROOT / "data/projekte.json").read_text())
PROJECTS = PJ["projects"]
PROJECT_SLUG = {"821": "ths-studentenwohnhaus-goettingen"}
for p in PROJECTS:
    p["url_slug"] = PROJECT_SLUG.get(p["slug"], p["slug"])

def project_desc(p):
    lines = [l for l in p["text"][1:] if not re.match(r"^(Bauherr|Architekt|Fertigstellung|Auftraggeber|Fotos|Visualisierung|GU)", l)]
    d = " ".join(lines) or ", ".join(p["tags"])
    d = f'{p["title"].title() if p["title"].isupper() else p["title"]}: {d}'
    return (d[:152] + "…") if len(d) > 155 else d

GROUPS = {
 "Wohnen & Wohnumfeld": ["Freianlagen im Geschosswohnungsbau", "Wohnumfeldverbesserung", "Mietergärten", "Barrierefreie Wohnungen im EG",
                         "Freianlagen für studentisches Wohnen", "Nachverdichtung im Bestand", "Energetische Sanierung", "UMGESTALTUNG VON HINTERHÖFEN"],
 "Spielplätze": ["Familienspielplatz", "Spielplatzsanierung"],
 "Kitas & Schulen": ["Außenanlagen Kindergärten", "Schulhöfe / Schulgärten"],
 "Plätze, Parks & Stadtumbau": ["Stadtplatzgestaltung", "Parkanlage", "Grünanlage", "Stadtumbau West", "Masterpläne/ Freiraumkonzept", "Friedhöfe"],
 "Denkmalschutz": ["Aussenanlagen an denkmalgeschützten Gebäuden"],
 "Haus- & Privatgärten": ["Hausgarten", "Gartengestaltung"],
 "Verwaltung & Gewerbe": ["Freianlagen von Verwaltungsgebäuden"],
}
GROUP_EXTRA = {"am-bailey-park-1-34-in-hameln": ["Wohnen & Wohnumfeld"],
               "freianlagen-von-verwaltungs-und-produktionsgebaeuden": ["Verwaltung & Gewerbe"],
               "alter-gueterbahnhof-goettingen": ["Plätze, Parks & Stadtumbau"]}
_TAG2GROUP = {t: g for g, ts in GROUPS.items() for t in ts}
def groups_of(p):
    gs = {_TAG2GROUP[t] for t in p["tags"] if t in _TAG2GROUP} | set(GROUP_EXTRA.get(p["slug"], []))
    return [g for g in GROUPS if g in gs]
def nice_tag(t):
    return {"UMGESTALTUNG VON HINTERHÖFEN": "Umgestaltung von Hinterhöfen", "Aussenanlagen an denkmalgeschützten Gebäuden": "Außenanlagen an denkmalgeschützten Gebäuden",
            "Masterpläne/ Freiraumkonzept": "Masterpläne / Freiraumkonzept"}.get(t, t)

def build_projects():
    for p in PROJECTS:
        p["groups"] = groups_of(p)
        assert p["groups"], "Projekt ohne Gruppe: " + p["slug"]
    terms = [g for g in GROUPS if any(g in p["groups"] for p in PROJECTS)]
    cards = []
    for p in PROJECTS:
        cards.append(f'<a class="card" href="/projekte/{p["url_slug"]}/" data-tags="{E("|".join(p["groups"]))}">'
                     f'<div class="ph">{img(p["thumb"] or p["images"][0], p["title"], "(max-width:600px) 100vw, 33vw")}'
                     f'<div class="ov"><h3>{E(p["title"])}</h3><p>{E(" · ".join(nice_tag(t) for t in p["tags"]))}</p><i></i></div></div></a>')
    filt = '<button type="button" data-tag="" aria-pressed="true">Alle</button>' + "".join(
        f'<button type="button" data-tag="{E(t)}" aria-pressed="false">{E(t)}</button>' for t in terms)
    body = f'''<div class="page"><div class="wrap">
<h1>Projekte</h1>
<p class="lead">Eine Auswahl unserer realisierten Freianlagen, Spielplätze, Plätze und Gärten – von Hannover bis Hamburg, Bremen, Göttingen und Würzburg.</p>
<div class="toolbar"><div class="filters" role="group" aria-label="Nach Kategorie filtern">{filt}</div>
<label class="sizer"><svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1" y="1" width="6" height="6"/><rect x="9" y="1" width="6" height="6"/><rect x="1" y="9" width="6" height="6"/><rect x="9" y="9" width="6" height="6"/></svg>
<span class="sr">Bildgröße</span><input type="range" min="2" max="6" step="1" value="3" aria-label="Projekte pro Zeile"><svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1" y="1" width="14" height="14"/></svg></label></div>
<div class="grid sized">{"".join(cards)}</div>
</div></div>'''
    layout("/projekte/", "Projekte", "Projekte von SPALINK-SIEVERS LandschaftsArchitekten: Freianlagen im Geschosswohnungsbau, Spielplätze, Kitas, Schulhöfe, Stadtplätze und Hausgärten.", body, "/projekte/",
           og_image=largest(PROJECTS[0]["thumb"]))
    for i, p in enumerate(PROJECTS):
        prev, nxt = PROJECTS[i - 1], PROJECTS[(i + 1) % len(PROJECTS)]
        imgs = [x for x in dict.fromkeys(p["images"])]
        ptitle = p["title"]
        gal = "".join('<button type="button" data-full="%s" aria-label="Bild %d vergrößern">%s</button>' % (largest(r), k + 1, img(r, "%s – %s, Foto %d" % (ptitle, nice_tag(p["tags"][0]) if p["tags"] else "Freianlage", k + 1), "(max-width:700px) 100vw, 33vw")) for k, r in enumerate(imgs))
        lines = p["text"][1:] if p["text"] and N(p["text"][0]).lower().replace("–", "-") == N(p["title"]).lower().replace("–", "-") else p["text"]
        facts = "".join(f"<p>{E(l)}</p>" for l in lines)
        tags = "".join(f'<li><a href="/projekte/?kategorie={E(_TAG2GROUP.get(t, p["groups"][0]))}">{E(nice_tag(t))}</a></li>' for t in p["tags"])
        hero = img(p["thumb"] or imgs[0], p["title"], "(max-width:860px) 100vw, 55vw", eager=True)
        body = f'''<div class="page"><div class="wrap">
<div class="project-head"><div>{hero}</div>
<div><h1>{E(p["title"])}</h1><ul class="tags">{tags}</ul><div class="facts">{facts}</div></div></div>
<div class="gallery">{gal}</div>
<nav class="pager" aria-label="Weitere Projekte"><a href="/projekte/{prev["url_slug"]}/">← {E(prev["title"])}</a><a href="/projekte/{nxt["url_slug"]}/">{E(nxt["title"])} →</a></nav>
</div></div>'''
        ld = {"@context": "https://schema.org", "@type": "CreativeWork", "name": p["title"], "description": project_desc(p),
              "creator": {"@type": "Organization", "name": NAME}, "keywords": ", ".join([nice_tag(t) for t in p["tags"]] + p["groups"]),
              "image": [SITE + largest(r) for r in imgs[:4] if largest(r)], "url": f'{SITE}/projekte/{p["url_slug"]}/'}
        layout(f'/projekte/{p["url_slug"]}/', p["title"], project_desc(p), body, "/projekte/", og_image=largest(p["thumb"] or imgs[0]), jsonld=ld)

# ---------- Aktuell & Presse ----------
PRESS_RE = re.compile(r"(Erschienen|Zeitung|[Mm]agazin|Heft|\bH\.\s?\d|Ausgabe|Architektenblatt|DAB regional|STADT und RAUM|Weser-?[Kk]urier|\bHAZ\b|Tageblatt|regionalSalzgitter|Wohnungswirtschaft|Mieterzeitung|Stadtanzeiger|DIE HARKE)")
DATE_RE = re.compile(r"^[\s\d./\-–,]*(\d{1,2}\.?\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)?\s*)?(19|20)?\d{2,4}[\s.:]*$", re.I)
YEAR_RE = re.compile(r"\b(20[0-3]\d|199\d)\b")
JUNK = {"spalink","sievers","johanna","johannah","landschaftsarchitekten","landschaftsarchitektur","hannover","scaled","kopie","copia","img","jpg","jpeg","png","web","final"}

def title_from_image(rel):
    stem = Path(rel).stem
    words = [w for w in re.split(r"[-_ ]+", stem) if w and not w.isdigit() and w.lower() not in JUNK and not re.match(r"^\d+x\d+$|^[a-z]?\d+[a-z]?$", w, re.I)]
    t = re.sub(r"^\d+", "", " ".join(words)).strip()
    if re.match(r"(?i)^(seiten aus|dwbn|bildschirmfoto|screenshot|dsc|whatsapp)", t): return ""
    return t[:1].upper() + t[1:] if len(t) >= 6 else ""

def short(t, n):
    if len(t) <= n: return t
    return t[:n].rsplit(" ", 1)[0].rstrip(" ,.:;–-") + " …"

def build_aktuell():
    raw = next(p for p in WP["pages"] if p["slug"] == "aktuell")["content"]["raw"]
    tree = parse_vc(raw)
    entries = []
    for row in tree["kids"]:
        if isinstance(row, str) or row["tag"] != "vc_row": continue
        s = json.dumps(row)
        if not re.search(r"vc_column_text|vc_single_image|vc_video|vc_btn", s): continue
        texts, images, extra = [], [], []
        def walk(n):
            if isinstance(n, str): texts.append(n); return
            if n["tag"] == "vc_single_image":
                r = MEDIA_BY_ID.get(int(n["a"].get("image", 0) or 0)); r and images.append(r)
            elif n["tag"] in ("vc_video", "vc_btn"): extra.append(render_vc(n))
            for k in n["kids"]: walk(k)
        walk(row)
        txt_html = autop(fix_links("\n\n".join(texts)))
        if not text_of(txt_html) and not images: continue
        # Zeilen bestimmen
        lines = [text_of(x) for x in re.split(r"<br>|</p>|\n", txt_html)]
        lines = [l for l in lines if l]
        date = ""
        title = ""
        consumed = 0
        if lines and DATE_RE.match(lines[0]) and len(lines[0]) < 30:
            date = lines[0].strip(" :"); consumed = 1
        if len(lines) > consumed:
            title = lines[consumed][:110]; consumed += 1
        if not title:
            title = next((t for t in (title_from_image(r) for r in images) if t), "")
        # die als Titel/Datum genutzten Zeilen nicht doppelt im Text zeigen
        body = txt_html
        for l in lines[:consumed]:
            body = re.sub(r"(<p>)?\s*" + re.escape(html.escape(l, quote=False)).replace("\\ ", "\\s+") + r"\s*(<br>\s*|</p>)?", "", body, count=1)
        body = body.replace("<p></p>", "").strip()
        alltext = " ".join(lines)
        y = YEAR_RE.search(date)
        year = int(y.group(1)) if y else next((int(r[:4]) for r in images if r[:4].isdigit() and r[:4] != "2017"), None)
        if year is None:
            y = YEAR_RE.search(alltext); year = int(y.group(1)) if y else None
        entries.append({"title": title, "date": date, "year": year,
                        "html": body + "".join(extra), "images": images, "plain": text_of(body),
                        "press": bool(PRESS_RE.search(alltext))})
    # Jahr fehlt -> vom vorherigen (neueren) Beitrag übernehmen; Upload-Jahr der Bilder als Rückfall
    last = None
    for e in entries:  # Beiträge stehen neueste zuerst: Jahr darf nicht größer als beim Vorgänger sein
        if e["year"] is None or (last and e["year"] > last):
            e["year"] = last
        last = e["year"]
    for e in entries:
        if not e["title"]:
            e["title"] = f'Bildbeitrag {e["year"]}' if e["year"] else "Bildbeitrag"
    cnt = {}
    for e in entries: cnt[e["title"]] = cnt.get(e["title"], 0) + 1
    for e in entries:
        if cnt[e["title"]] > 1 and not e["title"].startswith("Bildbeitrag"):
            e["title"] = f'{e["title"]} {e["date"] or e["year"] or ""}'.strip()
    seen = {}
    for e in entries:
        if e["title"] in seen:
            seen[e["title"]] += 1; e["title"] = f'{e["title"]} ({seen[e["title"]]})'
        else:
            seen[e["title"]] = 1
    used = set()
    for e in entries:
        base = slugify(e["title"])[:60]
        if e["title"].startswith("Bildbeitrag"): base = slugify(f'{e["title"]} {e["date"]}')[:60]
        s = base; k = 2
        while s in used: s = f"{base[:56]}-{k}"; k += 1
        used.add(s); e["slug"] = s
        e["section"] = "presse" if e["press"] else "aktuell"

    def post(e, h="h2", link=True):
        im = "".join(img(r, e["title"], "(max-width:760px) 100vw, 30vw") for r in e["images"][:6])
        url = f'/{e["section"]}/{e["slug"]}/'
        head = f'<{h}><a href="{url}">{E(e["title"])}</a></{h}>' if link else f"<{h}>{E(e['title'])}</{h}>"
        meta = f'<p class="meta">{E(e["date"] or str(e["year"] or ""))}</p>' if (e["date"] or e["year"]) else ""
        return f'<article class="post"><div>{meta}{head}<div class="prose">{e["html"]}</div></div><div class="imgs">{im}</div></article>'
    def tile(e):
        url = f'/{e["section"]}/{e["slug"]}/'
        meta = E(e["date"] or "")
        if e["images"]:
            return f'<a class="sq" href="{url}">{img(e["images"][0], e["title"], "(max-width:600px) 50vw, 220px")}<span><small>{meta}</small>{E(short(e["title"], 80))}</span></a>'
        return f'<a class="sq noimg" href="{url}"><span><small>{meta}</small>{E(short(e["title"], 90))}</span></a>'
    def by_year(items):
        out, cur = [], None
        for e in items:
            if e["year"] != cur:
                if cur is not None: out.append("</div>")
                cur = e["year"]; out.append(f'<h3 class="year">{cur or "Ohne Datum"}</h3><div class="squares">')
            out.append(tile(e))
        if items: out.append("</div>")
        return "".join(out)

    news = [e for e in entries if not e["press"]]
    # Oben groß: alle Beiträge des aktuellen Jahres (gibt es noch keine, die des neuesten Jahres)
    top_year = YEAR if any(e["year"] == YEAR for e in news) else max((e["year"] or 0) for e in news)
    top = [e for e in news if e["year"] == top_year]
    rest = [e for e in news if e["year"] != top_year]
    press = [e for e in entries if e["press"]]
    body = f'''<div class="page"><div class="wrap"><h1>Aktuell</h1>
<p class="lead">Neuigkeiten aus dem Büro – Eröffnungen, Vorträge, Exkursionen. Presseberichte über unsere Projekte finden Sie unter <a href="/presse/">Presse</a>.</p>
{"".join(post(e) for e in top)}
<div class="section-head"><h2>Ältere Beiträge</h2></div>{by_year(rest)}</div></div>'''
    layout("/aktuell/", "Aktuell", "Neuigkeiten aus dem Büro SPALINK-SIEVERS LandschaftsArchitekten in Hannover: Eröffnungen, Vorträge, Exkursionen und Termine.", body, "/aktuell/")
    body = f'''<div class="page"><div class="wrap"><h1>Presse</h1>{subnav_presse("/presse/")}
<p class="lead">Berichte über unsere Projekte in Zeitungen, Fachzeitschriften und Mitgliedermagazinen.<br>Eigene Fachbeiträge finden Sie unter <a href="/veroeffentlichungen/">Veröffentlichungen</a>.</p>
{by_year(press)}</div></div>'''
    layout("/presse/", "Presse", "Presseberichte über Projekte von SPALINK-SIEVERS LandschaftsArchitekten in Zeitungen, Fachzeitschriften und Magazinen.", body, "/presse/")
    for e in entries:
        d = e["plain"][:150] + ("…" if len(e["plain"]) > 150 else "")
        if len(d) < 60: d = f'{e["title"]}{": " + d if d else ""}'  # kurze Texte mit Titel eindeutig machen
        back = '<a href="/presse/">← Alle Presseberichte</a>' if e["press"] else '<a href="/aktuell/">← Alle Beiträge</a>'
        body = f'<div class="page"><div class="wrap">{post(e, "h1", False)}<nav class="pager">{back}</nav></div></div>'
        layout(f'/{e["section"]}/{e["slug"]}/', e["title"], d or e["title"], body, "/presse/" if e["press"] else "/aktuell/", og_image=largest(e["images"][0]) if e["images"] else "")
    return news


# ---------- Feste Seiten ----------
STATIC = {
 "uber-uns": ("/ueber-uns/", "Über uns", "Das Büro SPALINK-SIEVERS LandschaftsArchitekten in Hannover: seit 1991 Freiraumplanung für Wohnungsbau, Spielplätze, Schulen, Plätze und Gärten.", "/ueber-uns/"),
 "team": ("/team/", "Team", "Das Team von SPALINK-SIEVERS LandschaftsArchitekten in Hannover – Landschaftsarchitektinnen, Landschaftsarchitekten und Architekt.", "/team/"),
 "kontakt": ("/kontakt/", "Kontakt", "Kontakt zu SPALINK-SIEVERS LandschaftsArchitekten, Alte Herrenhäuser Str. 28, 30419 Hannover, Telefon 0511 979 259-0.", "/kontakt/"),
 "johanna-sievers": ("/johanna-sievers/", "Johanna Sievers", "Dipl.-Ing. Johanna Sievers, Landschaftsarchitektin BDLA – Gründerin von SPALINK-SIEVERS LandschaftsArchitekten in Hannover.", "/ueber-uns/"),
 "wettbewerbe": ("/wettbewerbe/", "Wettbewerbe", "Wettbewerbe und Auszeichnungen von SPALINK-SIEVERS LandschaftsArchitekten.", "/ueber-uns/"),
 "preisgericht": ("/preisgericht/", "Preisgericht", "Mitwirkung von Johanna Sievers als Fachpreisrichterin in Preisgerichten und Jurys.", "/ueber-uns/"),
 "veroeffentlichungen": ("/veroeffentlichungen/", "Veröffentlichungen", "Veröffentlichungen von SPALINK-SIEVERS LandschaftsArchitekten zu Freiraumplanung, Wohnumfeld und Klimaanpassung.", "/presse/"),
 "impressum": ("/impressum/", "Impressum", "Impressum von SPALINK-SIEVERS LandschaftsArchitekten.", None),
 "datenschutzerklaerung": ("/datenschutz/", "Datenschutz", "Datenschutzerklärung von SPALINK-SIEVERS LandschaftsArchitekten.", None),
}
LEGAL_EXTRA = """
<h2 id="hosting">Hosting</h2>
<div class="prose"><p>Diese Website wird bei der IONOS SE, Elgendorfer Str. 57, 56410 Montabaur, Deutschland, gehostet. Beim Aufruf der Website verarbeitet der Hoster die oben unter „Beim Besuch der Website“ genannten Zugriffsdaten (Server-Logfiles) in unserem Auftrag. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO; unser berechtigtes Interesse liegt in der sicheren und zuverlässigen Bereitstellung der Website. Mit dem Hoster besteht ein Vertrag zur Auftragsverarbeitung nach Art. 28 DSGVO.</p></div>
<h2 id="cookies">Cookies</h2>
<div class="prose"><p>Diese Website selbst setzt keine Cookies und verwendet keine Analyse- oder Tracking-Dienste. Schriften werden von unserem eigenen Server geladen; beim Seitenaufruf werden keine Inhalte von Drittanbietern nachgeladen. Einzige Ausnahme ist die Karte auf der Kontaktseite: Sie wird nur geladen, wenn Sie dies ausdrücklich per Klick wünschen (siehe <a href="#google-maps">Google Maps</a>). Ein Cookie-Banner ist daher nicht erforderlich.</p></div>
<h2 id="google-maps">Google Maps (nur nach Ihrer Zustimmung)</h2>
<div class="prose"><p>Auf der Kontaktseite können Sie eine Karte von Google Maps anzeigen lassen. Anbieter ist die Google Ireland Limited, Gordon House, Barrow Street, Dublin 4, Irland. Die Karte wird erst geladen, wenn Sie auf „Karte laden“ klicken. Erst dann werden Daten wie Ihre IP-Adresse an Google übertragen; dabei kann eine Übermittlung in die USA nicht ausgeschlossen werden, und Google kann Cookies setzen. Rechtsgrundlage ist Ihre Einwilligung (Art. 6 Abs. 1 lit. a DSGVO, § 25 Abs. 1 TDDDG), die Sie durch den Klick erteilen. Die Einwilligung gilt nur für den jeweiligen Seitenaufruf; beim nächsten Besuch wird die Karte nicht automatisch geladen. Weitere Informationen: <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">Datenschutzerklärung von Google</a>.</p></div>
<h2 id="externe-links">Links zu anderen Websites</h2>
<div class="prose"><p>Einige Seiten enthalten Links zu externen Angeboten (z. B. Instagram oder YouTube). Erst wenn Sie einen solchen Link anklicken, verlassen Sie unsere Website; für die Datenverarbeitung auf diesen Seiten ist der jeweilige Anbieter verantwortlich.</p></div>
"""
def build_static():
    for p in WP["pages"]:
        if p["slug"] not in STATIC: continue
        path, title, desc, active = STATIC[p["slug"]]
        content = render_vc(parse_vc(p["content"]["raw"]), title)
        if p["slug"] == "kontakt":  # Impressum/Datenschutz stehen im Footer
            content = re.sub(r"<p>(?:(?!</p>).)*/impressum/(?:(?!</p>).)*/datenschutz/(?:(?!</p>).)*</p>", "", content, flags=re.S)
        if p["slug"] == "impressum":
            content = content.replace("§ 5 Telemediengesetz (TMG)", "§ 5 Digitale-Dienste-Gesetz (DDG)")
        if p["slug"] == "datenschutzerklaerung":
            content += LEGAL_EXTRA
        extra = {'team': ' team', 'kontakt': ' kontakt'}.get(p["slug"], '')
        h1 = "Presse" if p["slug"] == "veroeffentlichungen" else title
        sub = subnav_presse("/veroeffentlichungen/") if p["slug"] == "veroeffentlichungen" else ""
        body = f'<div class="page"><div class="wrap content{extra}"><h1>{E(h1)}</h1>{sub}{content}</div></div>'
        layout(path, title, desc, body, active, jsonld=ORG if p["slug"] in ("kontakt", "uber-uns") else None)

# ---------- Startseite ----------
HERO = [  # Start mit Bild 1 (Frühherbst), danach Reihenfolge der Jahreszeiten
    "2017/01/Slider_Herbst_2026-scaled.jpg",                                  # Frühherbst (erste gelbe Blätter)
    "2017/01/spalink-sievers-herbst-hannover-herrenhausen-scaled.jpg",        # Herbst (Laub orange)
    "2017/01/pink-hannover-herrenhausen-spalink-sievers-Kopie-1-scaled.jpg",  # Winter (Raureif)
    "2017/01/spalink-sievers-herbst-hannover-scaled.jpg",                     # Vorfrühling (kahle Bäume)
    "2017/01/2023-hannover-spalink-sievers-landschaftsarchitekten-aussenanlagen-scaled.jpg",  # Frühling
    "2017/06/2-hannover-spalink-sievers-herbst-2022-3-garten-scaled.jpg",     # Sommer
]
def build_home(entries):
    slides = "".join(img(r, "Freianlagen von SPALINK-SIEVERS LandschaftsArchitekten in Hannover", "100vw", cls="on" if i == 0 else "", eager=i == 0) for i, r in enumerate(HERO))
    dots = "".join(f'<button type="button" aria-label="Bild {i+1}" aria-current="{str(i==0).lower()}"></button>' for i in range(len(HERO)))
    cards = "".join(f'<a class="card" href="/projekte/{p["url_slug"]}/"><div class="ph">{img(p["thumb"] or p["images"][0], p["title"], "(max-width:600px) 100vw, 33vw")}<div class="ov"><h3>{E(p["title"])}</h3><p>{E(" · ".join(nice_tag(t) for t in p["tags"]))}</p><i></i></div></div></a>' for p in PROJECTS[:6])
    news = "".join(f'<li><a href="/aktuell/{e["slug"]}/">{E(e["title"])}</a></li>' for e in entries[:4])
    body = f'''<section class="hero" aria-label="Bilder aus unseren Projekten">{slides}<div class="hero-dots">{dots}</div></section>
<div class="page"><div class="wrap">
<div class="intro"><h1>Landschafts&shy;architektur in Hannover – seit 1991</h1>
<div><p class="lead">SPALINK-SIEVERS LandschaftsArchitekten plant Freianlagen, die im Alltag funktionieren: Wohnumfeld und Innenhöfe im Geschosswohnungsbau, Spielplätze, Außenanlagen von Kindergärten und Schulen, Stadtplätze, öffentliche Grünanlagen und private Hausgärten.</p>
<p><a href="/ueber-uns/">Mehr über das Büro</a> · <a href="/kontakt/">Kontakt</a></p></div></div>
<div class="section-head"><h2>Aktuelle Projekte</h2><a class="more" href="/projekte/">Alle Projekte →</a></div>
<div class="grid">{cards}</div>
<div class="section-head"><h2>Aktuell</h2><a class="more" href="/aktuell/">Alle Beiträge →</a></div>
<ul>{news}</ul>
</div></div>'''
    layout("/", "SPALINK- SIEVERS LandschaftsArchitekten Hannover",
           "Auftragsspektrum: u.a. private Hausgärten, Stadtplätze, Spielplätze, Schulhöfe, Außenanlagen von Kindergärten, Verwaltungsgebäuden, öffentlichen Grünanlagen, Parks.",
           body, None, og_image=largest(HERO[0]),
           jsonld=[ORG, {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/"}])

# ---------- Umleitungen, Sitemap, Hosting-Dateien ----------
def build_meta():
    redirects = [("/uber-uns/", "/ueber-uns/"), ("/datenschutzerklaerung/", "/datenschutz/"), ("/preise-und-ausstellungen/", "/ueber-uns/"),
                 ("/spalink-sievers-landschaftsarchitekten/", "/"), ("/projects/821/", f"/projekte/{PROJECT_SLUG['821']}/")]
    ht = ["# Weiterleitungen alter WordPress-Adressen (IONOS / Apache)", "RewriteEngine On",
          "RewriteCond %{HTTPS} off", "RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]"]
    ht += [f"RewriteRule ^{a.strip('/')}/?$ {b} [L,R=301]" for a, b in redirects]
    ht += ["RewriteRule ^projects/([^/]+)/?$ /projekte/$1/ [L,R=301]",
           "RewriteRule ^wp-content/uploads/(.*\\.pdf)$ /dokumente/$1 [L,R=301,NC]",
           "", "ErrorDocument 404 /404.html",
           "<IfModule mod_expires.c>", " ExpiresActive On", ' ExpiresByType image/webp "access plus 1 year"',
           ' ExpiresByType font/woff2 "access plus 1 year"', ' ExpiresByType text/css "access plus 1 month"',
           ' ExpiresByType application/javascript "access plus 1 month"', "</IfModule>",
           "AddType font/woff2 .woff2", "AddType image/webp .webp"]
    (OUT / ".htaccess").write_text("\n".join(ht) + "\n")
    vercel = {"buildCommand": "", "outputDirectory": "public", "framework": None, "cleanUrls": False, "trailingSlash": True,
              "redirects": [{"source": a, "destination": b, "permanent": True} for a, b in redirects] +
                           [{"source": "/projects/:slug/", "destination": "/projekte/:slug/", "permanent": True}],
              "headers": [{"source": "/(.*)", "headers": [{"key": "X-Robots-Tag", "value": "noindex, nofollow"}]}]}
    (ROOT / "vercel.json").write_text(json.dumps(vercel, indent=2))
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    today = datetime.date.today().isoformat()
    urls = "".join(f"<url><loc>{SITE}{p}</loc><lastmod>{today}</lastmod></url>" for p in sorted(set(PAGES)) if p != "/404.html")
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    body = '<div class="page"><div class="wrap"><h1>Seite nicht gefunden</h1><p>Diese Seite gibt es nicht (mehr). <a href="/">Zur Startseite</a> · <a href="/projekte/">Projekte</a></p></div></div>'
    layout("/404.html", "Seite nicht gefunden", "Seite nicht gefunden.", body)

def assets():
    global ASSET_V
    dst = OUT / "assets"
    shutil.copytree(ROOT / "src/assets", dst, dirs_exist_ok=True)
    h = hashlib.md5((ROOT / "src/assets/style.css").read_bytes() + (ROOT / "src/assets/main.js").read_bytes()).hexdigest()[:8]
    ASSET_V = h
    logo = media_path("2017/06/Logo_SPALINK-SIEVERS-LandschaftsArchitekten-300-dpi-Kopie.png")
    with Image.open(logo) as im:
        im = im.convert("RGBA"); w = 760
        im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(dst / "logo.png", optimize=True)
        global LOGO_H; LOGO_H = round(im.height * w / im.width)
    icon = media_path("2017/06/cropped-icon.png")
    if icon:  # bisheriges Website-Symbol (wie in der Google-Suche) weiterverwenden
        with Image.open(icon) as ic:
            ic = ic.convert("RGBA")
            for name, size in (("favicon.png", 32), ("icon-192.png", 192), ("apple-touch-icon.png", 180)):
                ic.resize((size, size), Image.LANCZOS).save(OUT / name)

ASSET_V = "1"
import datetime
YEAR = datetime.date.today().year
if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    try:  # alte Seiten entfernen (Bilder bleiben als Cache); ohne Löschrecht werden sie einfach überschrieben
        for f in OUT.glob("**/index.html"): f.unlink()
        for d in sorted(OUT.glob("**/"), reverse=True):
            if d != OUT and not any(d.iterdir()): d.rmdir()
    except PermissionError:
        print("  Hinweis: alte Seiten nicht gelöscht (keine Löschberechtigung) – werden überschrieben")
    assets()
    build_projects()
    entries = build_aktuell()
    build_static()
    build_home(entries)
    build_meta()
    print(f"Fertig: {len(PAGES)} Seiten, {len(entries)} Aktuell-Beiträge, {len(PROJECTS)} Projekte")

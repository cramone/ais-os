"""Regenerate fonts-inline.css — offline Tabler (subset to used icons) + Manrope, as data-URI woff2.
Run only when the set of icons used across screens/ changes. Needs internet (downloads fonts).
    python subset-fonts.py
Output: fonts-inline.css (consumed by prototype.js). Requires: fonttools, brotli  (pip install fonttools brotli)
"""
import re, glob, base64, subprocess, os, tempfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SCREENS = os.path.join(HERE, "screens")
TMP = tempfile.gettempdir()
BS = chr(92)
URLS = {
    "tabler.woff2": "https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.24.0/dist/fonts/tabler-icons.woff2",
    "tabler.css":   "https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.24.0/dist/tabler-icons.min.css",
    "manrope.woff2":"https://cdn.jsdelivr.net/fontsource/fonts/manrope:vf@latest/latin-wght-normal.woff2",
}
def fetch(name):
    p = os.path.join(TMP, name)
    urllib.request.urlretrieve(URLS[name], p)
    return p

tb_woff = fetch("tabler.woff2"); css_p = fetch("tabler.css"); mr_woff = fetch("manrope.woff2")

names = set()
for f in glob.glob(SCREENS + "/*.html"):
    for m in re.findall(r'ti-([a-z0-9]+(?:-[a-z0-9]+)*)', open(f, encoding="utf-8").read()):
        names.add(m)
css = open(css_p, encoding="utf-8").read()
pat = re.compile(r'\.ti-([a-z0-9-]+):+before\s*\{\s*content:\s*"' + BS + BS + r'([0-9a-fA-F]+)"')
cp = {m.group(1): m.group(2) for m in pat.finditer(css)}
used = {n: cp[n] for n in names if n in cp}
print("icons used:", len(names), "mapped:", len(used), "unmapped:", sorted(n for n in names if n not in cp))

unicodes = ",".join("U+" + c for c in sorted(set(used.values())))
sub = os.path.join(TMP, "tabler-sub.woff2")
subprocess.run(["pyftsubset", tb_woff, "--unicodes=" + unicodes, "--output-file=" + sub,
    "--flavor=woff2", "--no-hinting", "--desubroutinize", "--drop-tables+=GSUB,GPOS,GDEF", "--no-layout-closure"], check=True)

tb = base64.b64encode(open(sub, "rb").read()).decode()
mr = base64.b64encode(open(mr_woff, "rb").read()).decode()
icon_rules = "".join('.ti-' + n + ':before{content:"' + BS + c + '"}' for n, c in sorted(used.items()))
out = (
    "@font-face{font-family:'tabler-icons';font-style:normal;font-weight:400;src:url(data:font/woff2;base64," + tb + ") format('woff2')}"
    "@font-face{font-family:'Manrope';font-style:normal;font-weight:400 800;font-display:swap;src:url(data:font/woff2;base64," + mr + ") format('woff2')}"
    '.ti{font-family:"tabler-icons"!important;font-style:normal;font-weight:400!important;font-variant:normal;text-transform:none;line-height:1;-webkit-font-smoothing:antialiased;display:inline-block}'
    + icon_rules
)
open(os.path.join(HERE, "fonts-inline.css"), "w", encoding="utf-8").write(out)
print("wrote fonts-inline.css:", round(len(out) / 1024), "KB  (tabler subset", os.path.getsize(sub), "b )")

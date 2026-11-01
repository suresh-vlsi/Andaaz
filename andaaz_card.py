import argparse
from html.parser import HTMLParser
import io
import os
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "work" / "python_packages"))

env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == "SARVAM_API_KEY":
            os.environ.setdefault("SARVAM_API_KEY", value.strip().strip("\"'"))
            break

api_key = os.environ.get("SARVAM_API_KEY")
if not api_key:
    raise SystemExit("Set SARVAM_API_KEY in the environment or add it to .env")

from sarvamai import SarvamAI


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script"}:
            self.ignored_depth += 1
            return
        if self.ignored_depth:
            return
        if tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"style", "script"}:
            self.ignored_depth = max(0, self.ignored_depth - 1)
            return
        if self.ignored_depth:
            return
        if tag in {"p", "div", "li", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignored_depth:
            self.parts.append(data)

parser = argparse.ArgumentParser(description="చేతిరాత తెలుగు వంటకార్డును చదవండి")
parser.add_argument("card", type=Path, help="PNG, JPG, JPEG లేదా PDF కార్డు ఫైల్")
args = parser.parse_args()
if not args.card.is_file():
    raise SystemExit(f"కార్డు ఫైల్ కనిపించలేదు: {args.card}")

mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".pdf": "application/pdf"}
mime_type = mime_types.get(args.card.suffix.lower())
if not mime_type:
    raise SystemExit("PNG, JPG, JPEG లేదా PDF ఫైల్ ఇవ్వండి.")

client = SarvamAI(api_subscription_key=api_key)
with args.card.open("rb") as card_file:
    job = client.doc_ai.parse(
        file=[(args.card.name, card_file, mime_type)],
        language="te-IN",
        content_type="handwritten",
    )

terminal = {"completed", "partially_completed", "failed", "rejected"}
while True:
    status = client.doc_ai.get_status(job_id=job.job_id)
    state = status.status.lower()
    if state in terminal:
        break
    time.sleep(2)

if state not in {"completed", "partially_completed"}:
    raise SystemExit(f"కార్డు చదవడం పూర్తికాలేదు. స్థితి: {status.status}")

download = client.doc_ai.get_download_url(job_id=job.job_id)
request = urllib.request.Request(download.url, headers=download.headers or {})
with urllib.request.urlopen(request) as response:
    output_bytes = response.read()

try:
    with zipfile.ZipFile(io.BytesIO(output_bytes)) as output_zip:
        html_files = [name for name in output_zip.namelist() if name.lower().endswith((".html", ".htm"))]
        html = "\n\n".join(output_zip.read(name).decode("utf-8", errors="replace") for name in html_files)
except zipfile.BadZipFile:
    html = output_bytes.decode("utf-8", errors="replace")

extractor = TextOnly()
extractor.feed(html)
text = "\n".join(line.strip() for line in "".join(extractor.parts).splitlines() if line.strip())
if text.startswith("Document\n"):
    text = text[len("Document\n"):]
if not text:
    raise SystemExit("కార్డు నుంచి చదవగలిగే వచనం రాలేదు.")

output_file = args.card.with_name(f"{args.card.stem}.recipe.txt")
output_file.write_text(text + "\n", encoding="utf-8")
print(text)
print(f"\nతెలుగు వంటకం సేవ్ అయింది: {output_file.name}")

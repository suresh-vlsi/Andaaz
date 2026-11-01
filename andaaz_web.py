import json
import os
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).parent
MAX_UPLOAD_BYTES = 30 * 1024 * 1024
UI_STRINGS = {
    "brand": "Family recipes",
    "tagline": "Tell your recipe as you cook, and keep it for your family.",
    "audioTitle": "Record a recipe while you cook",
    "audioHint": "Speak naturally. The audio is sent to Sarvam to prepare your recipe.",
    "record": "Start recording",
    "stop": "Stop",
    "chooseAudio": "Choose audio file",
    "processAudio": "Make recipe",
    "cardTitle": "Read a handwritten recipe card",
    "cardHint": "Choose a JPG, PNG, or PDF card.",
    "chooseCard": "Choose card file",
    "processCard": "Read card",
    "busy": "Working…",
    "recordReady": "Recording is ready. Make your recipe now.",
    "recording": "Recording…",
    "micError": "Allow microphone access or choose an audio file.",
    "audioProcessing": "Listening and preparing your recipe…",
    "cardProcessing": "Reading the card…",
    "done": "Done. Review the amounts, edit, and save.",
    "error": "Could not process the file. Check it and try again.",
    "translationError": "Could not change the interface language. Try again.",
    "outputTitle": "Recipe — review and edit",
    "save": "Save on this device",
    "download": "Download file",
    "archiveTitle": "My recipe archive",
    "archiveEmpty": "No recipes saved yet.",
    "archiveNote": "Saved recipes stay in this browser.",
    "saved": "Saved in this browser.",
}
LANGUAGES = {
    "en-IN": "English", "hi-IN": "हिन्दी — Hindi", "bn-IN": "বাংলা — Bengali",
    "ta-IN": "தமிழ் — Tamil", "te-IN": "తెలుగు — Telugu", "mr-IN": "मराठी — Marathi",
    "gu-IN": "ગુજરાતી — Gujarati", "kn-IN": "ಕನ್ನಡ — Kannada", "ml-IN": "മലയാളം — Malayalam",
    "od-IN": "ଓଡ଼ିଆ — Odia", "pa-IN": "ਪੰਜਾਬੀ — Punjabi", "as-IN": "অসমীয়া — Assamese",
    "brx-IN": "Bodo", "doi-IN": "डोगरी — Dogri", "kok-IN": "कोंकणी — Konkani",
    "ks-IN": "کٲشُر — Kashmiri", "mai-IN": "मैथिली — Maithili", "mni-IN": "Meiteilon — Manipuri",
    "ne-IN": "नेपाली — Nepali", "sa-IN": "संस्कृतम् — Sanskrit", "sat-IN": "ᱥᱟᱱᱛᱟᱲᱤ — Santali",
    "sd-IN": "سنڌي — Sindhi", "ur-IN": "اردو — Urdu",
}
UI_CACHE = {}


def translate_ui(code):
    if code in UI_CACHE:
        return UI_CACHE[code]
    if code not in LANGUAGES:
        raise ValueError("Unsupported language")

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
        raise RuntimeError("Sarvam key is not configured")

    from sarvamai import SarvamAI

    client = SarvamAI(api_subscription_key=api_key)
    keys = list(UI_STRINGS)
    response = client.text.translate(
        input="\n".join(UI_STRINGS[key] for key in keys),
        source_language_code="en-IN",
        target_language_code=code,
        model="sarvam-translate:v1",
    )
    lines = [line.strip() for line in response.translated_text.splitlines() if line.strip()]
    if len(lines) != len(keys):
        raise RuntimeError("Translation did not preserve the UI label list")
    translated = dict(zip(keys, lines))
    UI_CACHE[code] = translated
    return translated

PAGE = r'''<!doctype html>
<html lang="te">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Andaaz — అమ్మ వంటలు</title>
<script src="config.js"></script>
<style>
:root{font-family:system-ui,"Nirmala UI","Noto Sans Telugu",sans-serif;color:#28231e;background:#faf7f0}*{box-sizing:border-box}body{margin:0}header{background:#713f2b;color:#fff;padding:24px max(20px,calc((100vw - 820px)/2));display:flex;justify-content:space-between;align-items:center;gap:20px}h1{margin:0;font-size:28px}header p{margin:6px 0 0;opacity:.88}.language-picker{color:#28231e;border:0;border-radius:9px;padding:10px;font:inherit;max-width:220px}main{max-width:820px;margin:24px auto;padding:0 16px}.card{background:white;border:1px solid #e9dfd2;border-radius:16px;padding:20px;margin:16px 0;box-shadow:0 3px 12px #44250e0a}h2{font-size:19px;margin:0 0 12px}p{line-height:1.6}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}button,.filebutton{border:0;border-radius:10px;padding:11px 15px;background:#713f2b;color:white;font:inherit;cursor:pointer}button.secondary{background:#eee5dc;color:#3e3028}button:disabled{opacity:.5;cursor:wait}.file-picker{position:relative;display:inline-flex;align-items:center;border:1px solid #ddd;border-radius:10px;padding:10px 14px;min-height:46px;overflow:hidden;cursor:pointer}.file-picker input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer}small,.hint{color:#675f57}#result{width:100%;min-height:260px;margin-top:12px;border:1px solid #ded4ca;border-radius:10px;padding:12px;font:15px/1.65 ui-monospace,Consolas,monospace;white-space:pre-wrap}#status{min-height:24px;margin:10px 0;color:#713f2b}.archive-item{display:block;width:100%;text-align:left;margin:8px 0;background:#f4eee7;color:#302923}.archive-item small{display:block}.hidden{display:none}@media(max-width:560px){header{align-items:flex-start;flex-direction:column}.language-picker{max-width:100%}}
</style>
</head>
<body>
<header><div><h1>Andaaz <span data-ui="brand">అమ్మ వంటలు</span></h1><p data-ui="tagline" lang="te">వంట చెబితే చాలు — మీ కుటుంబ వంటకం భద్రంగా రాసుకుందాం.</p></div><select id="uiLanguage" class="language-picker" aria-label="Language"></select></header>
<main>
<section class="card">
<h2 data-ui="audioTitle" lang="te">వంట చెబుతూ రికార్డ్ చేయండి</h2>
<p class="hint" data-ui="audioHint" lang="te">తెలుగులో మాట్లాడండి. ఆడియో మీ కంప్యూటర్‌లో ఉంటుంది; ప్రాసెస్ చేయడానికి Sarvam APIకి పంపబడుతుంది.</p>
<div class="row"><button id="record" data-ui="record">రికార్డ్ ప్రారంభించు</button><button id="stop" class="secondary" data-ui="stop" disabled>ఆపు</button><label class="file-picker"><span data-ui="chooseAudio">ఆడియో ఫైల్ ఎంచుకోండి</span><input id="audioFile" type="file" accept="audio/*" aria-label="ఆడియో ఫైల్ ఎంచుకోండి"></label><button id="processAudio" data-ui="processAudio" disabled>రెసిపీ తయారు చేయి</button></div>
</section>
<section class="card">
<h2 data-ui="cardTitle" lang="te">చేతిరాత వంటకార్డు చదవండి</h2>
<p class="hint" data-ui="cardHint" lang="te">JPG, PNG లేదా PDF కార్డు ఎంచుకోండి.</p>
<div class="row"><label class="file-picker"><span data-ui="chooseCard">వంటకార్డు ఫైల్ ఎంచుకోండి</span><input id="cardFile" type="file" accept=".jpg,.jpeg,.png,.pdf,application/pdf" aria-label="వంటకార్డు ఫైల్ ఎంచుకోండి"></label><button id="processCard" data-ui="processCard" disabled>కార్డు చదువు</button></div>
</section>
<div id="status" role="status" aria-live="polite" lang="te"></div>
<section id="outputCard" class="card hidden"><h2 data-ui="outputTitle" lang="te">వంటకం — సరిచేసి సేవ్ చేసుకోండి</h2><textarea id="result" lang="te" spellcheck="false"></textarea><div class="row"><button id="save" data-ui="save">ఈ పరికరంలో సేవ్ చేయి</button><button id="download" class="secondary" data-ui="download">ఫైల్‌గా దించుకోండి</button></div></section>
<section class="card"><h2 data-ui="archiveTitle" lang="te">నా వంటకాల భాండాగారం</h2><div id="archive"><p class="hint" data-ui="archiveEmpty" lang="te">ఇంకా వంటకాలు సేవ్ కాలేదు.</p></div><small data-ui="archiveNote" lang="te">సేవ్ చేసిన వంటకాలు ఈ బ్రౌజర్‌లోనే ఉంటాయి.</small></section>
</main>
<script>
const $=id=>document.getElementById(id);let audio=null,card=null,stream=null,recorder=null,chunks=[],lastKind="audio";const API_BASE=(window.ANDAAZ_API_BASE||"").replace(/\/$/,"");
const TE={brand:"అమ్మ వంటలు",tagline:"వంట చెబితే చాలు — మీ కుటుంబ వంటకం భద్రంగా రాసుకుందాం.",audioTitle:"వంట చెబుతూ రికార్డ్ చేయండి",audioHint:"తెలుగులో మాట్లాడండి. వంటకం ప్రస్తుతం తెలుగులోనే ప్రాసెస్ అవుతుంది.",record:"రికార్డ్ ప్రారంభించు",stop:"ఆపు",chooseAudio:"ఆడియో ఫైల్ ఎంచుకోండి",processAudio:"రెసిపీ తయారు చేయి",cardTitle:"చేతిరాత వంటకార్డు చదవండి",cardHint:"JPG, PNG లేదా PDF కార్డు ఎంచుకోండి.",chooseCard:"వంటకార్డు ఫైల్ ఎంచుకోండి",processCard:"కార్డు చదువు",busy:"పని జరుగుతోంది…",recordReady:"రికార్డింగ్ సిద్ధంగా ఉంది. ఇప్పుడు రెసిపీ తయారు చేయండి.",recording:"రికార్డింగ్ జరుగుతోంది…",micError:"మైక్రోఫోన్ అనుమతి ఇవ్వండి లేదా ఆడియో ఫైల్ ఎంచుకోండి.",audioProcessing:"ఆడియో వింటున్నాం, రెసిపీ తయారవుతోంది…",cardProcessing:"కార్డు చదువుతున్నాం…",done:"పూర్తయింది. మోతాదులు చూసి సరిచేసి సేవ్ చేసుకోండి.",error:"ఫైల్ ప్రాసెస్ కాలేదు. తనిఖీ చేసి మళ్లీ ప్రయత్నించండి.",translationError:"భాష మార్చలేకపోయాం. మళ్లీ ప్రయత్నించండి.",outputTitle:"వంటకం — సరిచేసి సేవ్ చేసుకోండి",save:"ఈ పరికరంలో సేవ్ చేయి",download:"ఫైల్‌గా దించుకోండి",archiveTitle:"నా వంటకాల భాండాగారం",archiveEmpty:"ఇంకా వంటకాలు సేవ్ కాలేదు.",archiveNote:"సేవ్ చేసిన వంటకాలు ఈ బ్రౌజర్‌లోనే ఉంటాయి.",saved:"ఈ బ్రౌజర్‌లో వంటకం సేవ్ అయింది."};
const EN={brand:"Family recipes",tagline:"Tell your recipe as you cook, and keep it for your family.",audioTitle:"Record a recipe while you cook",audioHint:"Speak naturally in Telugu. Recipe processing currently supports Telugu.",record:"Start recording",stop:"Stop",chooseAudio:"Choose audio file",processAudio:"Make recipe",cardTitle:"Read a handwritten recipe card",cardHint:"Choose a JPG, PNG, or PDF card.",chooseCard:"Choose card file",processCard:"Read card",busy:"Working…",recordReady:"Recording is ready. Make your recipe now.",recording:"Recording…",micError:"Allow microphone access or choose an audio file.",audioProcessing:"Listening and preparing your recipe…",cardProcessing:"Reading the card…",done:"Done. Review the amounts, edit, and save.",error:"Could not process the file. Check it and try again.",translationError:"Could not change the interface language. Try again.",outputTitle:"Recipe — review and edit",save:"Save on this device",download:"Download file",archiveTitle:"My recipe archive",archiveEmpty:"No recipes saved yet.",archiveNote:"Saved recipes stay in this browser.",saved:"Saved in this browser."};
let activeStrings=TE,activeLanguage="te-IN";
function msg(key){return activeStrings[key]||TE[key]||key}function status(key){$("status").textContent=msg(key)}
function applyStrings(strings,code){activeStrings=strings;activeLanguage=code;document.documentElement.lang=code;document.documentElement.dir=["ur-IN","ks-IN"].includes(code)?"rtl":"ltr";document.querySelectorAll("[data-ui]").forEach(el=>{const key=el.dataset.ui;if(strings[key])el.textContent=strings[key]});$("audioFile").setAttribute("aria-label",msg("chooseAudio"));$("cardFile").setAttribute("aria-label",msg("chooseCard"));drawArchive()}
const languageOptions=[["te-IN","తెలుగు — Telugu"],["en-IN","English"],["hi-IN","हिन्दी — Hindi"],["bn-IN","বাংলা — Bengali"],["ta-IN","தமிழ் — Tamil"],["mr-IN","मराठी — Marathi"],["gu-IN","ગુજરાતી — Gujarati"],["kn-IN","ಕನ್ನಡ — Kannada"],["ml-IN","മലയാളം — Malayalam"],["od-IN","ଓଡ଼ିଆ — Odia"],["pa-IN","ਪੰਜਾਬੀ — Punjabi"],["as-IN","অসমীয়া — Assamese"],["brx-IN","Bodo"],["doi-IN","डोगरी — Dogri"],["kok-IN","कोंकणी — Konkani"],["ks-IN","کٲشُر — Kashmiri"],["mai-IN","मैथिली — Maithili"],["mni-IN","Meiteilon — Manipuri"],["ne-IN","नेपाली — Nepali"],["sa-IN","संस्कृतम् — Sanskrit"],["sat-IN","ᱥᱟᱱᱛᱟᱲᱤ — Santali"],["sd-IN","سنڌي — Sindhi"],["ur-IN","اردو — Urdu"]];
languageOptions.forEach(([code,name])=>{const option=document.createElement("option");option.value=code;option.textContent=name;$("uiLanguage").append(option)});
function busy(button,on,label){button.disabled=on;if(on){button.dataset.label=button.textContent;button.textContent=label}else if(button.dataset.label){button.textContent=button.dataset.label;delete button.dataset.label}}
async function changeLanguage(code){try{if(code==="te-IN"){applyStrings(TE,code)}else if(code==="en-IN"){applyStrings(EN,code)}else{const cached=localStorage.getItem("andaaz-ui-"+code);let strings=cached?JSON.parse(cached):null;if(!strings){status(msg("busy"));const response=await fetch(`${API_BASE}/api/ui-language?code=${encodeURIComponent(code)}`,{method:"POST"});const data=await response.json();if(!response.ok)throw new Error();strings=data.translations;localStorage.setItem("andaaz-ui-"+code,JSON.stringify(strings))}applyStrings(strings,code)}localStorage.setItem("andaaz-ui-language",code)}catch(e){$("uiLanguage").value=activeLanguage;status(msg("translationError"))}}
$("uiLanguage").value=localStorage.getItem("andaaz-ui-language")||"te-IN";$("uiLanguage").addEventListener("change",e=>changeLanguage(e.target.value));changeLanguage($("uiLanguage").value);
$("audioFile").addEventListener("change",e=>{audio=e.target.files[0]||null;$("processAudio").disabled=!audio});$("cardFile").addEventListener("change",e=>{card=e.target.files[0]||null;$("processCard").disabled=!card});
$("record").onclick=async()=>{try{stream=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];const mime=["audio/webm;codecs=opus","audio/webm","audio/mp4"].find(x=>MediaRecorder.isTypeSupported(x));recorder=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};recorder.onstop=()=>{const blob=new Blob(chunks,{type:recorder.mimeType||"audio/webm"});const ext=blob.type.includes("mp4")?"m4a":"webm";audio=new File([blob],`andaaz-recording.${ext}`,{type:blob.type});$("processAudio").disabled=false;stream.getTracks().forEach(t=>t.stop());status("recordReady")};recorder.start();$("record").disabled=true;$("stop").disabled=false;status("recording")}catch(e){status("micError")}};
$("stop").onclick=()=>{if(recorder&&recorder.state!=="inactive"){recorder.stop();$("record").disabled=false;$("stop").disabled=true}};
async function sendFile(file,kind,button){if(!file)return;busy(button,true,msg("busy"));status(kind==="audio"?"audioProcessing":"cardProcessing");try{const response=await fetch(`${API_BASE}/api/${kind}?name=${encodeURIComponent(file.name)}`,{method:"POST",headers:{"Content-Type":file.type||"application/octet-stream"},body:file});const data=await response.json();if(!response.ok)throw new Error();lastKind=kind;$("result").value=kind==="audio"?JSON.stringify(data.recipe,null,2):data.text;$("outputCard").classList.remove("hidden");status("done");window.scrollTo({top:$("outputCard").offsetTop,behavior:"smooth"})}catch(e){status("error")}finally{busy(button,false)}}
$("processAudio").onclick=()=>sendFile(audio,"audio",$("processAudio"));$("processCard").onclick=()=>sendFile(card,"card",$("processCard"));
function readArchive(){try{return JSON.parse(localStorage.getItem("andaaz-recipes")||"[]")}catch{return []}}
function drawArchive(){const list=readArchive(),box=$("archive");box.replaceChildren();if(!list.length){const p=document.createElement("p");p.className="hint";p.dataset.ui="archiveEmpty";p.textContent=msg("archiveEmpty");box.append(p);return}list.forEach(item=>{const b=document.createElement("button");b.className="archive-item";b.textContent=item.title;const s=document.createElement("small");s.textContent=new Date(item.savedAt).toLocaleString(activeLanguage);b.append(s);b.onclick=()=>{$("result").value=item.content;lastKind=item.kind;$("outputCard").classList.remove("hidden");window.scrollTo({top:$("outputCard").offsetTop,behavior:"smooth"})};box.append(b)})}
$("save").onclick=()=>{const content=$("result").value.trim();if(!content)return;let title=lastKind==="card"?content.split("\n")[0]:"తెలుగు వంటకం";if(lastKind==="audio"){try{title=JSON.parse(content).recipe_name||title}catch{}}const list=readArchive();list.unshift({title,content,kind:lastKind,savedAt:new Date().toISOString()});localStorage.setItem("andaaz-recipes",JSON.stringify(list.slice(0,100)));drawArchive();status("saved")};
$("download").onclick=()=>{const blob=new Blob([$("result").value],{type:"text/plain;charset=utf-8"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=lastKind==="card"?"recipe.txt":"recipe.json";a.click();URL.revokeObjectURL(url)};drawArchive();
</script>
</body></html>'''


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, data, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        origin = self.headers.get("Origin")
        allowed_origin = os.environ.get("ANDAAZ_ALLOWED_ORIGIN", "https://suresh-vlsi.github.io")
        if origin == allowed_origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload, status=200):
        self.send_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/config.js":
            api_base = json.dumps(os.environ.get("ANDAAZ_API_BASE", ""))
            self.send_bytes(f"window.ANDAAZ_API_BASE = {api_base};".encode("utf-8"), "application/javascript; charset=utf-8")
        elif path == "/":
            self.send_bytes(PAGE.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(204)
        origin = self.headers.get("Origin")
        allowed_origin = os.environ.get("ANDAAZ_ALLOWED_ORIGIN", "https://suresh-vlsi.github.io")
        if origin == allowed_origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Vary", "Origin")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        route = urlsplit(self.path)
        if route.path == "/api/ui-language":
            code = parse_qs(route.query).get("code", [""])[0]
            try:
                return self.send_json({"translations": translate_ui(code)})
            except ValueError:
                return self.send_json({"error": "Unsupported language"}, 400)
            except Exception:
                return self.send_json({"error": "Could not translate interface"}, 502)
        kind = route.path.removeprefix("/api/")
        if kind not in {"audio", "card"}:
            return self.send_json({"error": "Not found"}, 404)
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > MAX_UPLOAD_BYTES:
                return self.send_json({"error": "ఫైల్ ఖాళీగా ఉంది లేదా 30 MB కంటే పెద్దది."}, 413)
            name = parse_qs(route.query).get("name", ["upload"])[0]
            suffix = Path(name).suffix.lower()
            allowed = {".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".flac", ".aac", ".png", ".jpg", ".jpeg", ".pdf"}
            if suffix not in allowed:
                return self.send_json({"error": "ఈ ఫైల్ ఫార్మాట్ మద్దతు లేదు."}, 415)
            if kind == "card" and suffix not in {".png", ".jpg", ".jpeg", ".pdf"}:
                return self.send_json({"error": "కార్డుకు PNG, JPG లేదా PDF ఎంచుకోండి."}, 415)
            if kind == "audio" and suffix not in {".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".flac", ".aac"}:
                return self.send_json({"error": "ఆడియో ఫైల్ ఎంచుకోండి."}, 415)

            body = self.rfile.read(size)
            script = ROOT / ("andaaz_recipe.py" if kind == "audio" else "andaaz_card.py")
            with tempfile.TemporaryDirectory(prefix="andaaz-") as temp:
                upload = Path(temp) / ("recording" + suffix)
                upload.write_bytes(body)
                env = os.environ.copy()
                env["PYTHONUTF8"] = "1"
                completed = subprocess.run(
                    [sys.executable, str(script), str(upload)],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=240,
                )
                if completed.returncode:
                    detail = completed.stderr.strip().splitlines()[-1:] or ["ప్రాసెసింగ్ విఫలమైంది."]
                    return self.send_json({"error": detail[0]}, 502)
                if kind == "audio":
                    recipe = json.loads(completed.stdout)
                    return self.send_json({"recipe": recipe})
                text = completed.stdout.split("\n\nతెలుగు వంటకం సేవ్ అయింది:", 1)[0].strip()
                return self.send_json({"text": text})
        except subprocess.TimeoutExpired:
            return self.send_json({"error": "ప్రాసెసింగ్ ఎక్కువ సమయం తీసుకుంది. మళ్లీ ప్రయత్నించండి."}, 504)
        except Exception:
            return self.send_json({"error": "ప్రాసెస్ చేయలేకపోయాం. ఫైల్ ఫార్మాట్ తనిఖీ చేసి మళ్లీ ప్రయత్నించండి."}, 500)

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    print(f"Andaaz is running at http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()

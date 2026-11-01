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
    "brand": "Recipes",
    "tagline": "Tell your recipe as you cook. Keep the original alive.",
    "interfaceLanguageLabel": "Interface language",
    "audioTitle": "Record a recipe while you cook",
    "audioHint": "Choose the language spoken in your audio or written on your card.",
    "recipeLanguageLabel": "Audio/card language",
    "recipeLanguageHint": "Select the language spoken in your audio or written on the card. This is separate from the website language.",
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
<style>:root{color-scheme:light;--ink:#0b2342;--muted:#536d8b;--blue:#1769ff;--blue-dark:#0b3d9e;--ice:#e4f7ff;--line:rgba(81,142,205,.2);--glass:rgba(255,255,255,.72);font-family:"Aptos","Segoe UI","Nirmala UI","Noto Sans Telugu",system-ui,sans-serif;color:var(--ink);background:#eef7ff}*{box-sizing:border-box}html{min-height:100%;background:#eef7ff}body{margin:0;min-height:100vh;background:radial-gradient(ellipse at 5% 38%,rgba(91,190,255,.18),transparent 33%),radial-gradient(ellipse at 98% 70%,rgba(95,133,255,.14),transparent 32%),linear-gradient(145deg,#f6fcff 0%,#edf6ff 48%,#f6fbff 100%);background-attachment:fixed}body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.2;background-image:radial-gradient(rgba(28,89,150,.23) .7px,transparent .7px);background-size:22px 22px;mask-image:linear-gradient(to bottom,transparent,black 38%,transparent 94%)}.hero{position:relative;overflow:hidden;isolation:isolate;color:white;background:radial-gradient(ellipse at 78% 5%,rgba(86,194,255,.38),transparent 32%),linear-gradient(118deg,#071a36 0%,#103d86 52%,#1677de 100%);padding:30px 24px 42px;box-shadow:0 20px 55px rgba(12,54,112,.2)}.hero:after{content:"";position:absolute;inset:auto -8% -72% 28%;height:270px;border:1px solid rgba(190,235,255,.19);border-radius:50%;transform:rotate(-9deg);z-index:-1}.hero-inner{position:relative;z-index:2;max-width:1080px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:28px}.hero-copy{max-width:720px}.eyebrow{margin:0 0 12px;font-size:11px;font-weight:800;letter-spacing:.2em;color:#a8e8ff}.hero h1{margin:0;font-size:clamp(31px,4.3vw,49px);line-height:1.12;letter-spacing:-.04em;color:#fff}.hero h1 span{color:#b9efff}.hero-tagline{margin:12px 0 0;max-width:650px;line-height:1.6;color:rgba(239,249,255,.86);font-size:16px}.hero-orb{position:absolute;z-index:-1;border-radius:50%;filter:blur(1px);pointer-events:none}.orb-one{width:320px;height:320px;right:11%;top:-220px;background:rgba(112,225,255,.12);border:1px solid rgba(220,250,255,.16)}.orb-two{width:170px;height:170px;right:34%;bottom:-140px;background:rgba(116,170,255,.16);border:1px solid rgba(220,250,255,.15)}.locale-control{min-width:205px;padding:13px 15px 15px;border:1px solid rgba(220,245,255,.32);border-radius:17px;background:rgba(222,243,255,.12);backdrop-filter:blur(18px);box-shadow:inset 0 1px rgba(255,255,255,.22)}.locale-control label{display:block;margin:0 0 8px;font-size:11px;font-weight:750;letter-spacing:.08em;text-transform:uppercase;color:#c8f2ff}.language-picker{display:block;width:100%;max-width:100%;min-height:44px;padding:10px 38px 10px 13px;border:1px solid rgba(112,158,204,.28);border-radius:12px;background:rgba(255,255,255,.88);color:#102b4b;font:inherit;outline:none;box-shadow:0 3px 12px rgba(17,67,125,.06);transition:border-color .18s,box-shadow .18s,background .18s}.language-picker:focus{border-color:#41aaff;box-shadow:0 0 0 4px rgba(82,173,255,.2)}main{position:relative;max-width:1080px;margin:26px auto 60px;padding:0 22px}.page-intro{display:flex;align-items:center;justify-content:space-between;margin:0 4px 14px}.intro-mark{display:flex;align-items:center;gap:9px;color:#476887;font-size:10px;font-weight:800;letter-spacing:.18em}.intro-mark span{width:8px;height:8px;border-radius:50%;background:#29a8ff;box-shadow:0 0 0 5px rgba(52,164,255,.13),0 0 16px rgba(24,123,255,.45)}.tool-grid{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(280px,.75fr);gap:18px;align-items:stretch}.card{position:relative;padding:24px 25px;margin:18px 0;border:1px solid rgba(93,151,204,.2);border-radius:22px;background:linear-gradient(138deg,rgba(255,255,255,.82),rgba(236,248,255,.68));backdrop-filter:blur(22px);box-shadow:0 12px 35px rgba(31,83,135,.08),inset 0 1px rgba(255,255,255,.95);transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease}.tool-grid .card{margin:0;min-height:100%}.tool-card:hover{transform:translateY(-3px);border-color:rgba(66,151,240,.36);box-shadow:0 18px 42px rgba(31,83,135,.13),inset 0 1px rgba(255,255,255,.98)}h2{display:flex;align-items:center;gap:12px;margin:0 0 10px;color:#102b4d;font-size:20px;letter-spacing:-.025em;line-height:1.35}.audio-card h2:before,.document-card h2:before{display:grid;place-items:center;flex:none;width:38px;height:38px;border:1px solid rgba(70,157,241,.18);border-radius:13px;background:linear-gradient(145deg,#e9f8ff,#dceeff);color:#1465db;font-size:19px;box-shadow:0 5px 14px rgba(55,132,208,.1)}.audio-card h2:before{content:"◉"}.document-card h2:before{content:"▧"}p{line-height:1.65}.hint{margin:6px 0 14px;color:var(--muted);font-size:14px}.recipe-language{margin:18px 0 16px;padding:14px;border:1px solid rgba(82,150,207,.17);border-radius:16px;background:linear-gradient(120deg,rgba(230,248,255,.77),rgba(247,252,255,.66))}.recipe-language label{display:block;margin-bottom:8px;color:#244a72;font-size:12px;font-weight:800;letter-spacing:.04em}.recipe-language .language-picker{max-width:390px}.recipe-language .hint{margin:9px 0 0;font-size:12px}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:15px}button,.filebutton{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:10px 16px;border:1px solid transparent;border-radius:12px;background:linear-gradient(135deg,#1b6dff,#278df2);color:white;font:inherit;font-size:14px;font-weight:700;cursor:pointer;box-shadow:0 7px 16px rgba(26,103,225,.2);transition:transform .16s ease,filter .16s ease,box-shadow .16s ease}button:hover:not(:disabled),.file-picker:hover{transform:translateY(-1px);filter:saturate(1.08);box-shadow:0 10px 22px rgba(26,103,225,.25)}button:active:not(:disabled){transform:translateY(0)}button.secondary{border-color:rgba(84,140,191,.2);background:rgba(226,241,252,.78);color:#1b4a7d;box-shadow:none}button:disabled{opacity:.48;cursor:not-allowed;filter:saturate(.55);box-shadow:none}.file-picker{position:relative;display:inline-flex;align-items:center;min-height:44px;padding:9px 14px;overflow:hidden;border:1px solid rgba(79,143,199,.25);border-radius:12px;background:rgba(255,255,255,.82);color:#1b4a7d;font-size:14px;font-weight:650;cursor:pointer;transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease}.file-picker input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer}.file-picker:focus-within{outline:3px solid rgba(66,160,255,.25);border-color:#48a5fa}#status{min-height:24px;margin:16px 4px;color:#175ab3;font-size:14px;font-weight:650}#outputCard{border-color:rgba(51,136,220,.25)}#result{display:block;width:100%;min-height:260px;margin:12px 0;border:1px solid rgba(83,142,195,.24);border-radius:15px;padding:15px;background:rgba(251,254,255,.82);color:#123453;font:16px/1.9 "Noto Sans Telugu","Nirmala UI","Gautami","Segoe UI",sans-serif;white-space:pre-wrap;box-shadow:inset 0 2px 8px rgba(33,87,139,.04);outline:none}#result:focus{border-color:#3c9cf1;box-shadow:0 0 0 4px rgba(72,167,255,.13)}#archive{margin:8px 0}.archive-item{display:block;width:100%;margin:8px 0;padding:13px 15px;border:1px solid rgba(91,145,190,.14);border-radius:14px;background:rgba(239,248,255,.78);color:#173d65;text-align:left;box-shadow:none}.archive-item:hover{border-color:rgba(61,143,224,.38);background:rgba(228,245,255,.96)}.archive-item small{display:block;margin-top:4px;color:#68809b}small{color:#68809b}.card>small{display:block;margin-top:14px}.hidden{display:none}button:focus-visible,.file-picker:focus-within,.language-picker:focus-visible{outline:3px solid rgba(39,145,255,.28);outline-offset:2px}@media(max-width:820px){.tool-grid{grid-template-columns:1fr}.tool-grid .card{min-height:0}.tool-card{padding:22px}}@media(max-width:620px){.hero{padding:24px 18px 30px}.hero-inner{align-items:stretch;flex-direction:column;gap:18px}.hero h1{font-size:34px}.hero-tagline{font-size:14px}.locale-control{width:100%;max-width:none}.page-intro{margin:0 3px 12px}.intro-mark{font-size:9px;letter-spacing:.13em}main{margin-top:18px;padding:0 14px}.card{padding:19px 17px;border-radius:18px}.row{gap:8px}.row button,.row .file-picker{flex:1 1 auto}.recipe-language{padding:12px}.recipe-language .language-picker{max-width:100%}}@media(prefers-reduced-motion:reduce){*,*:before,*:after{scroll-behavior:auto!important;transition:none!important}}</style>
</head>
<body>
<header class="hero"><div class="hero-inner"><div class="hero-copy"><h1>Andaaz <span data-ui="brand">అమ్మ వంటలు</span></h1><p class="hero-tagline" data-ui="tagline" lang="te">వంట చెబితే చాలు. అసలైన రుచిని భద్రంగా ఉంచండి.</p></div><div class="locale-control"><label for="uiLanguage" data-ui="interfaceLanguageLabel">Interface language</label><select id="uiLanguage" class="language-picker" aria-label="Interface language"></select></div></div><div class="hero-orb orb-one"></div><div class="hero-orb orb-two"></div></header>
<main>
<div class="tool-grid">
<section class="card tool-card audio-card">
<h2 data-ui="audioTitle" lang="te">వంట చెబుతూ రికార్డ్ చేయండి</h2>
<p class="hint" data-ui="audioHint" lang="te">మీ ఆడియో లేదా వంటకార్డులో ఉన్న భాషను ఎంచుకోండి.</p>
<div class="recipe-language"><label for="recipeLanguage" data-ui="recipeLanguageLabel">ఆడియో/కార్డు భాష</label><select id="recipeLanguage" class="language-picker" aria-label="Audio/card language"></select><p class="hint" data-ui="recipeLanguageHint">ఆడియోలో మాట్లాడిన లేదా కార్డుపై ఉన్న భాషను ఎంచుకోండి. ఇది వెబ్‌సైట్ భాషకు వేరు.</p></div>
<div class="row"><button id="record" data-ui="record">రికార్డ్ ప్రారంభించు</button><button id="stop" class="secondary" data-ui="stop" disabled>ఆపు</button><label class="file-picker"><span data-ui="chooseAudio">ఆడియో ఫైల్ ఎంచుకోండి</span><input id="audioFile" type="file" accept="audio/*" aria-label="ఆడియో ఫైల్ ఎంచుకోండి"></label><button id="processAudio" data-ui="processAudio" disabled>రెసిపీ తయారు చేయి</button></div>
</section>
<section class="card tool-card document-card">
<h2 data-ui="cardTitle" lang="te">చేతిరాత వంటకార్డు చదవండి</h2>
<p class="hint" data-ui="cardHint" lang="te">JPG, PNG లేదా PDF కార్డు ఎంచుకోండి.</p>
<div class="row"><label class="file-picker"><span data-ui="chooseCard">వంటకార్డు ఫైల్ ఎంచుకోండి</span><input id="cardFile" type="file" accept=".jpg,.jpeg,.png,.pdf,application/pdf" aria-label="వంటకార్డు ఫైల్ ఎంచుకోండి"></label><button id="processCard" data-ui="processCard" disabled>కార్డు చదువు</button></div>
</section>
</div>
<div id="status" role="status" aria-live="polite" lang="te"></div>
<section id="outputCard" class="card hidden"><h2 data-ui="outputTitle" lang="te">వంటకం — సరిచేసి సేవ్ చేసుకోండి</h2><textarea id="result" lang="te" spellcheck="false"></textarea><div class="row"><button id="save" data-ui="save">ఈ పరికరంలో సేవ్ చేయి</button><button id="download" class="secondary" data-ui="download">ఫైల్‌గా దించుకోండి</button></div></section>
<section class="card"><h2 data-ui="archiveTitle" lang="te">నా వంటకాల భాండాగారం</h2><div id="archive"><p class="hint" data-ui="archiveEmpty" lang="te">ఇంకా వంటకాలు సేవ్ కాలేదు.</p></div><small data-ui="archiveNote" lang="te">సేవ్ చేసిన వంటకాలు ఈ బ్రౌజర్‌లోనే ఉంటాయి.</small></section>
</main>
<script>
const $=id=>document.getElementById(id);let audio=null,card=null,stream=null,recorder=null,chunks=[],lastKind="audio";const API_BASE=(window.ANDAAZ_API_BASE||"").replace(/\/$/,"");
const TE={brand:"అమ్మ వంటలు",interfaceLanguageLabel:"వెబ్‌సైట్ భాష",tagline:"వంట చెబితే చాలు. అసలైన రుచిని భద్రంగా ఉంచండి.",audioTitle:"వంట చెబుతూ రికార్డ్ చేయండి",audioHint:"మీ ఆడియో లేదా వంటకార్డులో ఉన్న భాషను ఎంచుకోండి.",recipeLanguageLabel:"ఆడియో/కార్డు భాష",recipeLanguageHint:"ఆడియోలో మాట్లాడిన లేదా కార్డుపై ఉన్న భాషను ఎంచుకోండి. ఇది వెబ్‌సైట్ భాషకు వేరు.",record:"రికార్డ్ ప్రారంభించు",stop:"ఆపు",chooseAudio:"ఆడియో ఫైల్ ఎంచుకోండి",processAudio:"రెసిపీ తయారు చేయి",cardTitle:"చేతిరాత వంటకార్డు చదవండి",cardHint:"JPG, PNG లేదా PDF కార్డు ఎంచుకోండి.",chooseCard:"వంటకార్డు ఫైల్ ఎంచుకోండి",processCard:"కార్డు చదువు",busy:"పని జరుగుతోంది…",recordReady:"రికార్డింగ్ సిద్ధంగా ఉంది. ఇప్పుడు రెసిపీ తయారు చేయండి.",recording:"రికార్డింగ్ జరుగుతోంది…",micError:"మైక్రోఫోన్ అనుమతి ఇవ్వండి లేదా ఆడియో ఫైల్ ఎంచుకోండి.",audioProcessing:"ఆడియో వింటున్నాం, రెసిపీ తయారవుతోంది…",cardProcessing:"కార్డు చదువుతున్నాం…",done:"పూర్తయింది. మోతాదులు చూసి సరిచేసి సేవ్ చేసుకోండి.",error:"ఫైల్ ప్రాసెస్ కాలేదు. తనిఖీ చేసి మళ్లీ ప్రయత్నించండి.",translationError:"భాష మార్చలేకపోయాం. మళ్లీ ప్రయత్నించండి.",outputTitle:"వంటకం — సరిచేసి సేవ్ చేసుకోండి",save:"ఈ పరికరంలో సేవ్ చేయి",download:"ఫైల్‌గా దించుకోండి",archiveTitle:"నా వంటకాల భాండాగారం",archiveEmpty:"ఇంకా వంటకాలు సేవ్ కాలేదు.",archiveNote:"సేవ్ చేసిన వంటకాలు ఈ బ్రౌజర్‌లోనే ఉంటాయి.",saved:"ఈ బ్రౌజర్‌లో వంటకం సేవ్ అయింది."};
const EN={brand:"Recipes",interfaceLanguageLabel:"Interface language",tagline:"Tell your recipe as you cook. Keep the original alive.",audioTitle:"Record a recipe while you cook",audioHint:"Choose the language spoken in your audio or written on your card.",recipeLanguageLabel:"Audio/card language",recipeLanguageHint:"Select the language spoken in your audio or written on the card. This is separate from the website language.",record:"Start recording",stop:"Stop",chooseAudio:"Choose audio file",processAudio:"Make recipe",cardTitle:"Read a handwritten recipe card",cardHint:"Choose a JPG, PNG, or PDF card.",chooseCard:"Choose card file",processCard:"Read card",busy:"Working…",recordReady:"Recording is ready. Make your recipe now.",recording:"Recording…",micError:"Allow microphone access or choose an audio file.",audioProcessing:"Listening and preparing your recipe…",cardProcessing:"Reading the card…",done:"Done. Review the amounts, edit, and save.",error:"Could not process the file. Check it and try again.",translationError:"Could not change the interface language. Try again.",outputTitle:"Recipe — review and edit",save:"Save on this device",download:"Download file",archiveTitle:"My recipe archive",archiveEmpty:"No recipes saved yet.",archiveNote:"Saved recipes stay in this browser.",saved:"Saved in this browser."};
let activeStrings=TE,activeLanguage="te-IN";
function msg(key){return activeStrings[key]||TE[key]||key}function status(key){$("status").textContent=msg(key)}
function applyStrings(strings,code){activeStrings=strings;activeLanguage=code;document.documentElement.lang=code;document.documentElement.dir=["ur-IN","ks-IN"].includes(code)?"rtl":"ltr";document.querySelectorAll("[data-ui]").forEach(el=>{const key=el.dataset.ui;if(strings[key])el.textContent=strings[key]});$("audioFile").setAttribute("aria-label",msg("chooseAudio"));$("cardFile").setAttribute("aria-label",msg("chooseCard"));$("recipeLanguage").setAttribute("aria-label",msg("recipeLanguageLabel"));drawArchive()}
const languageOptions=[["te-IN","తెలుగు — Telugu"],["en-IN","English"],["hi-IN","हिन्दी — Hindi"],["bn-IN","বাংলা — Bengali"],["ta-IN","தமிழ் — Tamil"],["mr-IN","मराठी — Marathi"],["gu-IN","ગુજરાતી — Gujarati"],["kn-IN","ಕನ್ನಡ — Kannada"],["ml-IN","മലയാളം — Malayalam"],["od-IN","ଓଡ଼ିଆ — Odia"],["pa-IN","ਪੰਜਾਬੀ — Punjabi"],["as-IN","অসমীয়া — Assamese"],["brx-IN","Bodo"],["doi-IN","डोगरी — Dogri"],["kok-IN","कोंकणी — Konkani"],["ks-IN","کٲشُر — Kashmiri"],["mai-IN","मैथिली — Maithili"],["mni-IN","Meiteilon — Manipuri"],["ne-IN","नेपाली — Nepali"],["sa-IN","संस्कृतम् — Sanskrit"],["sat-IN","ᱥᱟᱱᱛᱟᱲᱤ — Santali"],["sd-IN","سنڌي — Sindhi"],["ur-IN","اردو — Urdu"]];
languageOptions.forEach(([code,name])=>{const option=document.createElement("option");option.value=code;option.textContent=name;$("uiLanguage").append(option);const recipeOption=document.createElement("option");recipeOption.value=code;recipeOption.textContent=name;$("recipeLanguage").append(recipeOption)});
function busy(button,on,label){button.disabled=on;if(on){button.dataset.label=button.textContent;button.textContent=label}else if(button.dataset.label){button.textContent=button.dataset.label;delete button.dataset.label}}
async function changeLanguage(code){try{if(code==="te-IN"){applyStrings(TE,code)}else if(code==="en-IN"){applyStrings(EN,code)}else{const cached=localStorage.getItem("andaaz-ui-"+code);let strings=cached?JSON.parse(cached):null;if(!strings){status(msg("busy"));const response=await fetch(`${API_BASE}/api/ui-language?code=${encodeURIComponent(code)}`,{method:"POST"});const data=await response.json();if(!response.ok)throw new Error();strings=data.translations;localStorage.setItem("andaaz-ui-"+code,JSON.stringify(strings))}applyStrings(strings,code)}localStorage.setItem("andaaz-ui-language",code)}catch(e){$("uiLanguage").value=activeLanguage;status(msg("translationError"))}}
$("uiLanguage").value=localStorage.getItem("andaaz-ui-language")||"te-IN";$("uiLanguage").addEventListener("change",e=>changeLanguage(e.target.value));changeLanguage($("uiLanguage").value);$("recipeLanguage").value=localStorage.getItem("andaaz-recipe-language")||"te-IN";$("recipeLanguage").addEventListener("change",e=>localStorage.setItem("andaaz-recipe-language",e.target.value));
$("audioFile").addEventListener("change",e=>{audio=e.target.files[0]||null;$("processAudio").disabled=!audio});$("cardFile").addEventListener("change",e=>{card=e.target.files[0]||null;$("processCard").disabled=!card});
$("record").onclick=async()=>{try{stream=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];const mime=["audio/webm;codecs=opus","audio/webm","audio/mp4"].find(x=>MediaRecorder.isTypeSupported(x));recorder=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};recorder.onstop=()=>{const blob=new Blob(chunks,{type:recorder.mimeType||"audio/webm"});const ext=blob.type.includes("mp4")?"m4a":"webm";audio=new File([blob],`andaaz-recording.${ext}`,{type:blob.type});$("processAudio").disabled=false;stream.getTracks().forEach(t=>t.stop());status("recordReady")};recorder.start();$("record").disabled=true;$("stop").disabled=false;status("recording")}catch(e){status("micError")}};
$("stop").onclick=()=>{if(recorder&&recorder.state!=="inactive"){recorder.stop();$("record").disabled=false;$("stop").disabled=true}};
async function sendFile(file,kind,button){if(!file)return;busy(button,true,msg("busy"));status(kind==="audio"?"audioProcessing":"cardProcessing");try{const response=await fetch(`${API_BASE}/api/${kind}?name=${encodeURIComponent(file.name)}&language=${encodeURIComponent($("recipeLanguage").value)}`,{method:"POST",headers:{"Content-Type":file.type||"application/octet-stream"},body:file});const data=await response.json();if(!response.ok)throw new Error();lastKind=kind;$("result").value=kind==="audio"?JSON.stringify(data.recipe,null,2):data.text;$("outputCard").classList.remove("hidden");status("done");window.scrollTo({top:$("outputCard").offsetTop,behavior:"smooth"})}catch(e){status("error")}finally{busy(button,false)}}
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
        language_code = parse_qs(route.query).get("language", ["te-IN"])[0]
        if language_code not in LANGUAGES:
            return self.send_json({"error": "Unsupported recipe language"}, 400)
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
                    [sys.executable, str(script), str(upload), "--language-code", language_code],
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

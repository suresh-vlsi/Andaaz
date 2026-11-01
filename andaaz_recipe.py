import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "work" / "python_packages"))

# Load a local .env when present; hosted services provide the key as an environment variable.
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

CONFIDENCE = {"type": "string", "enum": ["ఎక్కువ", "మధ్యస్థం", "తక్కువ"]}
SCHEMA = {
    "type": "object",
    "properties": {
        "recipe_name": {"type": "string"},
        "measurement_assumptions": {"type": "array", "items": {"type": "string"}},
        "ingredients": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ingredient": {"type": "string"},
                    "original_amount": {"type": "string"},
                    "quantity_confidence": CONFIDENCE,
                    "estimated_min_grams": {"type": ["number", "null"]},
                    "estimated_max_grams": {"type": ["number", "null"]},
                    "conversion_confidence": CONFIDENCE,
                    "conversion_reason": {"type": "string"},
                },
                "required": [
                    "ingredient", "original_amount", "quantity_confidence",
                    "estimated_min_grams", "estimated_max_grams",
                    "conversion_confidence", "conversion_reason",
                ],
                "additionalProperties": False,
            },
        },
        "steps": {"type": "array", "items": {"type": "string"}},
        "questions_for_cook": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["recipe_name", "measurement_assumptions", "ingredients", "steps", "questions_for_cook"],
    "additionalProperties": False,
}

SUPPORTED_LANGUAGE_CODES = (
    "as-IN", "bn-IN", "brx-IN", "doi-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN",
    "kok-IN", "ks-IN", "mai-IN", "ml-IN", "mni-IN", "mr-IN", "ne-IN", "od-IN",
    "pa-IN", "sa-IN", "sat-IN", "sd-IN", "ta-IN", "te-IN", "ur-IN",
)
parser = argparse.ArgumentParser(description="Turn a spoken recipe into a structured recipe")
parser.add_argument("audio", type=Path, help="వంట వివరణ ఉన్న ఆడియో ఫైల్")
parser.add_argument("--language-code", default="te-IN", choices=SUPPORTED_LANGUAGE_CODES, help="Recipe language (default: te-IN)")
args = parser.parse_args()
if not args.audio.is_file():
    raise SystemExit(f"ఆడియో ఫైల్ కనిపించలేదు: {args.audio}")

client = SarvamAI(api_subscription_key=api_key)
with args.audio.open("rb") as audio_file:
    transcript = client.speech_to_text.transcribe(
        file=audio_file,
        model="saaras:v4",
        language_code=args.language_code,
        mode="transcribe",
    ).transcript

if args.language_code == "te-IN":
    system_prompt = (
        "మీరు ఆడియోలో చెప్పిన వంటకాన్ని శుభ్రమైన, సహజమైన, సంప్రదాయ తెలుగులో క్రమబద్ధీకరించే వంటల సంపాదకులు. తెలుగు లిపిలోనే రాయండి; ఇంగ్లీష్ పదాలను తెలుగు ఉచ్చారణలా రాయకండి; పదక్షర అనువాదం చేయకండి. పదార్థాల పేర్లు, అసలు మోతాదులు, సంఖ్యలు, భిన్నాలు (ఉదా. ¾, ¼), దశల క్రమం ట్రాన్స్క్రిప్ట్‌లో ఉన్నట్టే కాపాడండి. ట్రాన్స్క్రిప్ట్‌లో లేని పదార్థాలు లేదా దశలు కల్పించకండి. సాధారణ తెలుగు వంట పదాల సరైన స్పెల్లింగ్ వాడండి: హైదరాబాదీ, చికెన్, బాస్మతి బియ్యం, పెరుగు, అల్లం వెల్లుల్లి ముద్ద, పసుపు, బిర్యానీ మసాలా, నిమ్మరసం, వేయించిన ఉల్లిపాయలు, పుదీనా, కొత్తిమీర, పచ్చిమిర్చి, నెయ్యి, కుంకుమపువ్వు, యాలకులు, లవంగాలు, దాల్చిన చెక్క, బిర్యానీ ఆకు, షాజీరా, దమ్. "
        "మాటల్లోని పదార్థాలు, క్రమం, అసలు మోతాదులను కాపాడండి. confidence అంటే మోతాదు వినికిడి లేదా గ్రాముల మార్పిడి నమ్మకం. "
        "1 కప్పు = 240 మి.లీ., పెద్ద చెంచా = 15 మి.లీ., చిన్న చెంచా = 5 మి.లీ. అని భావించి, "
        "వంటకుడి పాత్రల కొలతలు నిర్ధారించలేదని measurement_assumptions లో చెప్పండి. నీటికి 1 మి.లీ. సుమారు 1 గ్రాము. "
        "'కొంచెం', 'సరిపడా', 'రుచికి' వంటి అస్పష్ట మోతాదులకు గ్రాములు ఊహించవద్దు; null పెట్టండి. "
        "confidence ఫీల్డుల్లో ఎక్కువ, మధ్యస్థం, తక్కువ మాత్రమే వాడండి. కొత్త పదార్థాలు లేదా దశలు చేర్చవద్దు."
    )
    user_prompt = f"ఈ తెలుగు వంట మాటలను రెసిపీగా క్రమబద్ధీకరించండి:\n\n{transcript}"
else:
    english_transcript = transcript
    if args.language_code != "en-IN":
        parts = textwrap.wrap(transcript, width=1800, break_long_words=False, break_on_hyphens=False) or [transcript]
        english_transcript = " ".join(
            client.text.translate(
                input=part,
                source_language_code=args.language_code,
                target_language_code="en-IN",
                model="sarvam-translate:v1",
            ).translated_text
            for part in parts
        )
    system_prompt = (
        "Create a faithful family recipe from the English translation. Return recipe text in English. "
        "Use the original transcript to copy original_amount phrases exactly where possible. Preserve ingredients "
        "and step order; do not invent ingredients or steps. quantity_confidence means the amount was heard clearly; "
        "conversion_confidence means how confidently it converts to grams. These are different. Assume 1 cup=240 ml, "
        "tablespoon=15 ml, teaspoon=5 ml, and state these assumptions. Water is about 1 g/ml. Never invent grams for "
        "vague amounts such as a little or to taste; use null and low conversion confidence. Ask only useful questions. "
        "For confidence fields use only the schema values: ఎక్కువ, మధ్యస్థం, తక్కువ."
    )
    user_prompt = (
        f"Original transcript ({args.language_code}; preserve original-language amount phrases):\n{transcript}\n\n"
        f"English translation for understanding:\n{english_transcript}"
    )

result = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {"name": "family_recipe", "strict": True, "schema": SCHEMA},
    },
)
recipe = json.loads(result.choices[0].message.content)

# Keep the recognized words visible so the family can audit the recipe fields.
recipe = {"spoken_transcript": transcript, **recipe}
if args.language_code == "te-IN":
    recipe["measurement_assumptions"] = [
        "అంచనా ప్రమాణాలు: 1 కప్పు = 240 మి.లీ., పెద్ద చెంచా = 15 మి.లీ., చిన్న చెంచా = 5 మి.లీ.",
        "వంటకుడి సొంత కప్పు లేదా చెంచా ఈ ప్రమాణాలతో సమానమని నిర్ధారించలేదు.",
    ]
else:
    recipe["measurement_assumptions"].extend([
        "Assumptions used: 1 cup = 240 ml, 1 tablespoon = 15 ml, and 1 teaspoon = 5 ml.",
        "The cook's own cup and spoon sizes have not been confirmed to match these standards.",
    ])

# Apply simple unit conversions deterministically so the model cannot return
# inconsistent arithmetic for common measures.
TELUGU_COUNTS = {
    "ఒకటి": 1,
    "ఒక": 1,
    "రెండు": 2,
    "మూడు": 3,
    "నాలుగు": 4,
    "ఐదు": 5,
    "ఆరు": 6,
    "ఏడు": 7,
    "ఎనిమిది": 8,
    "తొమ్మిది": 9,
    "పది": 10,
}

def count_in(text):
    for word, number in TELUGU_COUNTS.items():
        if word in text:
            return number
    return None

for item in recipe["ingredients"] if args.language_code == "te-IN" else []:
    name = item["ingredient"]
    amount = item["original_amount"]
    count = count_in(amount)

    # A 240 ml cup of water weighs approximately 240 g.
    if count is not None and "కప్పు" in amount and ("నీరు" in name or "నీళ్ళు" in name or "నీళ్లు" in name):
        grams = count * 240
        item["estimated_min_grams"] = grams
        item["estimated_max_grams"] = grams
        item["conversion_confidence"] = "ఎక్కువ"
        item["conversion_reason"] = "240 మి.లీ. కప్పు ప్రమాణం ప్రకారం నీటి బరువు సుమారు అదే గ్రాములుగా ఉంటుంది."

    # A Telugu "spoon" can mean a 5 ml teaspoon or a 15 ml tablespoon.
    elif count is not None and "చెంచా" in amount and "నూనె" in name:
        item["estimated_min_grams"] = round(count * 5 * 0.91, 1)
        item["estimated_max_grams"] = round(count * 15 * 0.91, 1)
        item["conversion_confidence"] = "మధ్యస్థం"
        item["conversion_reason"] = "చిన్న లేదా పెద్ద చెంచా కావచ్చని, నూనె సాంద్రత సుమారు 0.91 గ్రా/మి.లీ. అని భావించి పరిధి ఇచ్చాను."
        assumption = "నూనెకు సుమారు 0.91 గ్రా/మి.లీ. సాంద్రతను అంచనాగా వాడాను."
        if assumption not in recipe["measurement_assumptions"]:
            recipe["measurement_assumptions"].append(assumption)

    elif count is not None and ("ఉల్లిపాయ" in name or "టమాట" in name):
        item["estimated_min_grams"] = None
        item["estimated_max_grams"] = None
        item["conversion_confidence"] = "తక్కువ"
        item["conversion_reason"] = "సంఖ్య తెలిసింది; కానీ కూరగాయల పరిమాణం (చిన్నది, మధ్యస్థం లేదా పెద్దది) తెలియదు."

    # If the model returned only the ingredient name, it likely dropped the
    # spoken amount. Recover a nearby shared Telugu amount phrase when present.
    if amount.strip() == name.strip():
        nearby_phrases = ["రుచికి సరిపడా", "సరిపడా", "కొంచెం", "చిటికెడు", "అందాజుగా"]
        ingredient_at = transcript.find(name)
        matches = []
        if ingredient_at >= 0:
            for phrase in nearby_phrases:
                phrase_at = transcript.find(phrase)
                while phrase_at >= 0:
                    distance = max(0, ingredient_at - (phrase_at + len(phrase)), phrase_at - (ingredient_at + len(name)))
                    if distance <= 40:
                        matches.append((distance, phrase))
                    phrase_at = transcript.find(phrase, phrase_at + 1)

        if matches:
            shared_amount = min(matches)[1]
            item["original_amount"] = shared_amount
            item["quantity_confidence"] = "ఎక్కువ"
            item["conversion_confidence"] = "తక్కువ"
            item["estimated_min_grams"] = None
            item["estimated_max_grams"] = None
            item["conversion_reason"] = "ఈ మోతాదు మాట ట్రాన్స్క్రిప్ట్‌లో ఈ పదార్థానికి సమీపంగా చెప్పబడింది; గ్రాములుగా మార్చడానికి సరిపడా సమాచారం లేదు."
        else:
            item["quantity_confidence"] = "తక్కువ"
            item["conversion_confidence"] = "తక్కువ"
            item["estimated_min_grams"] = None
            item["estimated_max_grams"] = None
            item["conversion_reason"] = "మూల ట్రాన్స్క్రిప్ట్‌లో ఈ పదార్థానికి మోతాదు స్పష్టంగా గుర్తించబడలేదు."

if args.language_code == "te-IN":
    # Keep the existing Telugu-specific unit handling and present confidence labels in Telugu.
    for item in recipe["ingredients"]:
        for field in ("quantity_confidence", "conversion_confidence"):
            item[field] = {"high": "ఎక్కువ", "medium": "మధ్యస్థం", "low": "తక్కువ"}.get(item[field], item[field])
else:
    # Translate generated text to the selected recipe language. The source transcript
    # and quoted amount phrases stay untouched so the family can audit what was said.
    for item in recipe["ingredients"]:
        for field in ("quantity_confidence", "conversion_confidence"):
            item[field] = {"ఎక్కువ": "high", "మధ్యస్థం": "medium", "తక్కువ": "low"}.get(item[field], item[field])

    if args.language_code == "en-IN":
        print(json.dumps(recipe, ensure_ascii=False, indent=2))
        raise SystemExit(0)

    fields = []

    def collect(node, path=()):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str) and key not in {"spoken_transcript", "original_amount"}:
                    fields.append((path + (key,), value))
                else:
                    collect(value, path + (key,))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                if isinstance(value, str):
                    fields.append((path + (index,), value))
                else:
                    collect(value, path + (index,))

    def assign(path, value):
        parent = recipe
        for part in path[:-1]:
            parent = parent[part]
        parent[path[-1]] = value

    def translate_group(group):
        response = client.text.translate(
            input="\n".join(value for _, value in group),
            source_language_code="en-IN",
            target_language_code=args.language_code,
            model="sarvam-translate:v1",
        )
        translated = response.translated_text.splitlines()
        if len(translated) != len(group):
            if len(group) == 1:
                translated = [response.translated_text]
            else:
                for path, value in group:
                    single = client.text.translate(
                        input=value,
                        source_language_code="en-IN",
                        target_language_code=args.language_code,
                        model="sarvam-translate:v1",
                    ).translated_text
                    assign(path, single.strip())
                return
        for (path, _), value in zip(group, translated):
            assign(path, value.strip())

    collect(recipe)
    group, size = [], 0
    for entry in fields:
        path, value = entry
        if len(value) > 1900:
            if group:
                translate_group(group)
                group, size = [], 0
            translate_group([entry])
        elif group and size + len(value) + 1 > 1900:
            translate_group(group)
            group, size = [entry], len(value) + 1
        else:
            group.append(entry)
            size += len(value) + 1
    if group:
        translate_group(group)

print(json.dumps(recipe, ensure_ascii=False, indent=2))




import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "work" / "python_packages"))

# Load the project's .env without adding another dependency.
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    name, separator, value = line.partition("=")
    if separator and name.strip() == "SARVAM_API_KEY":
        os.environ.setdefault("SARVAM_API_KEY", value.strip().strip("\"'"))
        break

api_key = os.environ.get("SARVAM_API_KEY")
if not api_key:
    raise SystemExit("Add your Sarvam API key to .env as SARVAM_API_KEY=your_key")

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

parser = argparse.ArgumentParser(description="తెలుగు వంట ఆడియోను రెసిపీగా మార్చండి")
parser.add_argument("audio", type=Path, help="వంట వివరణ ఉన్న ఆడియో ఫైల్")
args = parser.parse_args()
if not args.audio.is_file():
    raise SystemExit(f"ఆడియో ఫైల్ కనిపించలేదు: {args.audio}")

client = SarvamAI(api_subscription_key=api_key)
with args.audio.open("rb") as audio_file:
    transcript = client.speech_to_text.transcribe(
        file=audio_file,
        model="saaras:v4",
        language_code="te-IN",
        mode="transcribe",
    ).transcript

result = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[
        {
            "role": "system",
            "content": (
                "మీరు తెలుగు కుటుంబ వంటకాల లేఖకులు. సమాధానంలోని అన్ని వాక్యాలు తెలుగులోనే రాయండి. "
                "వంటకుడు చెప్పిన పదార్థాలు, క్రమం, అసలు మోతాదు మాటలను అలాగే కాపాడండి. "
                "quantity_confidence అంటే మోతాదు మాటలను సరిగ్గా విన్నామా అన్న నమ్మకం; "
                "conversion_confidence అంటే వాటిని గ్రాములుగా మార్చిన నమ్మకం. ఇవి వేర్వేరుగా నిర్ణయించండి. "
                "అంచనాలకు స్పష్టమైన సాధారణ ప్రమాణాలు వాడండి: ఒక కప్పు = 240 మి.లీ., పెద్ద చెంచా = 15 మి.లీ., "
                "చిన్న చెంచా = 5 మి.లీ. ఇవి వంటకుడి సొంత పాత్రల కొలతలు కావు కాబట్టి "
                "measurement_assumptions లో పేర్కొనండి. నీటికి 1 మి.లీ. సుమారు 1 గ్రాము. "
                "బియ్యం వంటి పదార్థాలకు గ్రాముల మార్పిడి మారవచ్చు; ఒక ఖచ్చితమైన సంఖ్యకు బదులు "
                "సమంజసమైన పరిధి మాత్రమే ఇవ్వండి, మధ్యస్థం లేదా తక్కువ conversion_confidence ఇవ్వండి. "
                "చెంచా చిన్నదా పెద్దదా తెలియకపోతే విస్తృత పరిధి ఇవ్వగలిగితే ఇవ్వండి, లేకపోతే గ్రాముల ఫీల్డులను null చేయండి. "
                "'కొంచెం', 'సరిపడా', 'రుచికి' వంటి మాటలకు గ్రాముల సంఖ్య ఊహించవద్దు; null పెట్టి తక్కువ "
                "conversion_confidence ఇవ్వండి. వాటిని quantity_confidence తక్కువగా పరిగణிக்க వద్దు, "
                "మాట స్పష్టంగా వినిపిస్తే ఎక్కువ ఇవ్వండి. conversion_reason లో అంచనా లేదా null కారణాన్ని "
                "తెలుగులో వివరించండి. అవసరమైన స్పష్టీకరణలనే questions_for_cook లో అడగండి; "
                "రుచికి సరిపడా అన్నవాటికి ఖచ్చితమైన గ్రాములు అడగవద్దు. కొత్త పదార్థాలు లేదా దశలు చేర్చవద్దు."
            ),
        },
        {"role": "user", "content": f"ఈ తెలుగు వంట మాటలను రెసిపీగా క్రమబద్ధీకరించండి:\n\n{transcript}"},
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {"name": "telugu_recipe", "strict": True, "schema": SCHEMA},
    },
)

recipe = json.loads(result.choices[0].message.content)

# Keep the recognized words visible so the family can audit the recipe fields.
recipe = {"spoken_transcript": transcript, **recipe}
recipe["measurement_assumptions"] = [
    "ఈ స్క్రిప్ట్ అంచనా ప్రమాణాలు: 1 కప్పు = 240 మి.లీ., పెద్ద చెంచా = 15 మి.లీ., చిన్న చెంచా = 5 మి.లీ.",
    "వంటకుడి సొంత కప్పు లేదా చెంచా ఈ ప్రమాణాలతో సమానమని నిర్ధారించలేదు.",
]

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

for item in recipe["ingredients"]:
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

print(json.dumps(recipe, ensure_ascii=False, indent=2))




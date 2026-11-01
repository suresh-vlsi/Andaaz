import os
import sys
from pathlib import Path

# Load the project's .env without adding a dotenv dependency.
env_file = Path(__file__).with_name(".env")
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        if separator and name.strip() == "SARVAM_API_KEY":
            os.environ.setdefault("SARVAM_API_KEY", value.strip().strip("\"'"))
            break

sys.path.insert(0, str(Path(__file__).parent / "work" / "python_packages"))
api_key = os.environ.get("SARVAM_API_KEY")
if not api_key:
    raise SystemExit("Add your Sarvam API key to .env as SARVAM_API_KEY=your_key")

from sarvamai import SarvamAI

client = SarvamAI(api_subscription_key=api_key)
response = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[{"role": "user", "content": "Say hello in one short sentence."}],
)
print(response.choices[0].message.content)

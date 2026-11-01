# Andaaz — family recipes, remembered

Andaaz helps families preserve recipes shared by feel. It can turn spoken Indic-language cooking instructions into a structured recipe, read a handwritten recipe card, and keep saved recipes in the visitor's browser.

## Live website

**[Open Andaaz](https://suresh-vlsi.github.io/Andaaz/)**

The public interface is hosted on GitHub Pages. The Sarvam-powered features require the separate API service described below.

## What this project includes

- Audio recording or upload for spoken recipes.
- Speech transcription in 22 Indian languages plus English with Sarvam Speech to Text (`saaras:v4`).
- Recipe structuring with Sarvam Chat Completions (`sarvam-105b-conversations`), including original measures, estimated gram ranges, confidence notes, and cooking steps. For languages outside the chat model's direct coverage, Andaaz translates the transcript to English for structuring and translates recipe text back to the selected language.
- Handwritten recipe-card reading in 22 Indian languages plus English with Sarvam Document AI.
- A language selector for the interface, translated with Sarvam Text Translate (`sarvam-translate:v1`) into supported Indic languages.
- Recipe review, editing, download, and a browser-local recipe archive.
- A static GitHub Pages frontend and a Python API backend deployment configuration for Render.

The interface language and recipe language can be selected independently. Speech recognition, handwritten card reading, and recipe output support 22 Indian languages plus English. Review translations and measurement estimates before cooking. Saved recipes remain in the current browser and are not uploaded to a family cloud archive.

## Run locally

1. Install the dependency: `py -m pip install -r requirements.txt`
2. Create a `.env` file in the project directory and add your key:

   ```text
   SARVAM_API_KEY=your_key_here
   ```

3. Start the local web server: `py andaaz_web.py`
4. Open `http://127.0.0.1:8000` in a browser.

Keep `.env` private. It is ignored by Git; never add the API key to frontend files or commit it.

## Deployment

GitHub Actions publishes the static site from `docs/` to GitHub Pages when changes are pushed to `main`. Sarvam requests are handled by the separate Render service. To enable that functionality publicly, deploy the Blueprint in `render.yaml` and configure `SARVAM_API_KEY` as a Render secret.

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment details.

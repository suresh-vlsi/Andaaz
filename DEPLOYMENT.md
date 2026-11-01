# Andaaz deployment

GitHub Pages hosts the Telugu-first web interface from `docs/`. Sarvam API calls run on a separate Render Python service. The API key is configured only in the Render environment; never place it in `docs/config.js` or commit `.env`.

## Publish the Pages site

1. In the GitHub repository, open **Settings → Pages** and choose **GitHub Actions** as the build and deployment source.
2. Push to `main` (or run the Pages workflow manually). The site URL is `https://suresh-vlsi.github.io/Andaaz/`.

## Start the API backend

1. In Render, choose **New → Blueprint** and connect `suresh-vlsi/Andaaz`.
2. Render reads `render.yaml` and asks for `SARVAM_API_KEY`. Enter it in Render's secret field; do not commit it.
3. Deploy the service named `andaaz-api-suresh-vlsi`. The Pages frontend is configured to call `https://andaaz-api-suresh-vlsi.onrender.com`.

The free Render service sleeps after inactivity and may take a little time to wake for its first request. Its filesystem is temporary; Andaaz stores saved recipes in each visitor's browser, not on the server.

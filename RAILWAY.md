# Deploy on Railway

This repo is a **Streamlit** app. Railway is the **hosting platform** (public URL for demos). You do not replace Streamlit with Railway; Railway runs `streamlit run app.py` inside a container.

## Prerequisites

- GitHub repo connected to Railway (or deploy from this directory with Railway CLI).
- **API_KEY** for [data.gov.in](https://data.gov.in/) set in Railway: **Project → Variables** → add `API_KEY` (same name as your local `.env`). Never commit `.env`.

## Deploy (GitHub)

1. Push this repo to GitHub.
2. [Railway](https://railway.app/) → **New Project** → **Deploy from GitHub** → select the repo.
3. Railway will detect the **Dockerfile** and build it.
4. Under **Variables**, add:
   - `API_KEY` = your data.gov.in API key
5. **Settings → Networking → Generate Domain** (or attach a custom domain).
6. Open the generated URL — the app should load.

## Deploy (CLI)

```bash
railway login
railway init
railway up
```

Set `API_KEY` in the Railway dashboard for the project.

## Notes

- **Port**: The Dockerfile uses `$PORT` (Railway sets this automatically).
- **Build context**: Only `app.py`, `main.py`, `requirements.txt`, and `src/` are copied into the image (see `.dockerignore`).
- **Optional entry**: `main.py` is included if you want to change the Dockerfile `CMD` to run `main.py` instead of `app.py`.

## If you truly want “not Streamlit”

That would mean rewriting the UI (e.g. FastAPI + HTML/React). Railway still works; it is unrelated to Streamlit vs other frameworks.

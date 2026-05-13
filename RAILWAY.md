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
- **Config as code**: Root [`railway.toml`](railway.toml) sets `builder = "DOCKERFILE"` so Railway uses this image (not Railpack/Nixpacks guessing).
- **Build context**: Only `app.py`, `main.py`, `requirements.txt`, and `src/` are copied into the image (see `.dockerignore`).
- **Optional entry**: `main.py` is included if you want to change the Dockerfile `CMD` to run `main.py` instead of `app.py`.

## “Application failed to respond” (Railway error page)

That page means the **edge proxy could not get a healthy HTTP response** from your container. Common causes:

1. **Process crashed on startup** — Open **Deployments → latest deploy → View logs** (build + deploy). Look for `ModuleNotFoundError`, `Traceback`, or exit code non-zero.
2. **Wrong start command in dashboard** — In the Railway service, **Settings → Deploy → Custom Start Command** should be **empty** so the **Dockerfile `CMD`** runs (Streamlit on `$PORT` and `0.0.0.0`). If you set something like `python app.py`, remove it.
3. **Headless matplotlib** — The app sets `matplotlib.use("Agg")` before `pyplot` so charts work on Linux servers without a display.
4. **Cold start** — First request after sleep can take 30–60s; refresh once or check logs until you see `You can now view your Streamlit app`.

After fixing, **Redeploy** from the latest commit.

## If you truly want “not Streamlit”

That would mean rewriting the UI (e.g. FastAPI + HTML/React). Railway still works; it is unrelated to Streamlit vs other frameworks.

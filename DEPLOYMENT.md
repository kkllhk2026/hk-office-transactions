# Deployment Guide

This project ships with config for several common Python hosting platforms.
Pick the one that matches your situation.

---

## Quick reference

| File | Used by | Purpose |
|---|---|---|
| `requirements.txt` | All platforms | Python dependencies (with version floors, not exact pins) |
| `.python-version` | Railway (Railpack), pyenv, asdf | Pins Python to 3.12 |
| `runtime.txt` | Streamlit Cloud, Heroku-style buildpacks | Pins Python to 3.12 |
| `railway.json` | Railway (Railpack) | Build + start command + healthcheck |
| `Procfile` | Heroku, Render, Fly.io (sometimes) | Start command |
| `.streamlit/config.toml` | Streamlit itself | Server + theme config |

---

## Railway

The `railway.json` file is configured for Railway's Railpack builder.

**Step-by-step:**

1. Push the project to GitHub
2. In Railway, **New Project → Deploy from GitHub repo**
3. Railway auto-detects Python, reads `railway.json`, builds with Railpack
4. After build, Railway exposes a public URL
5. (Optional) Add `OPENAI_API_KEY` as a service variable for LLM summaries

**If the build fails with "exit code 1 on pip install":**

Set the env var `RAILPACK_PYTHON_VERSION=3.12` on the Railway service.
This overrides Railpack's default of 3.13.

**If the deploy starts but you get a 502:**

Check that the start command is using `$PORT` (Railway-injected) and
`--server.address=0.0.0.0`. Both are in `railway.json`.

---

## Streamlit Community Cloud (free)

The `runtime.txt` file pins Python 3.12. Streamlit Cloud reads it.

**Step-by-step:**

1. Push the project to GitHub (must be public, or use a Streamlit team plan)
2. Go to https://share.streamlit.io
3. Click **New app** → pick your repo → main file is `app.py`
4. (Optional) Add `OPENAI_API_KEY` in **App settings → Secrets** like:
   ```
   OPENAI_API_KEY = "sk-..."
   ```
5. Deploy. First boot takes ~3 minutes.

**Note on scrapers:** Streamlit Cloud's egress IPs are US-based and many
HK news sites geo-fence aggressively. RSS feeds work fine; HTML scraping
of Centaline / SCMP may fail with 403. For real production scraping,
prefer a VPS in HK or Singapore.

---

## Render / Fly.io / Heroku

`Procfile` and `runtime.txt` cover these.

```bash
# Render: connect repo via dashboard, it auto-detects
# Fly.io:
fly launch --no-deploy
fly secrets set OPENAI_API_KEY=sk-...
fly deploy
# Heroku:
heroku create hk-office-tracker
heroku config:set OPENAI_API_KEY=sk-...
git push heroku main
```

---

## Local development

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Visit http://localhost:8501.

---

## Docker (optional)

Not shipped by default, but the project is Dockerizable. A minimal Dockerfile:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## Why Python 3.12 and not 3.13?

The original v0.1 requirements pinned Python 3.13 implicitly via Railway's
default. Several dependencies in the original list (`newspaper3k`, the
old `numpy 1.26.4` and `pandas 2.2.2` pins) don't have wheels for 3.13:

- `newspaper3k` is unmaintained since 2020 and breaks on `lxml` ≥5
  (which removed `lxml.html.clean` to a separate package)
- `numpy 1.x` has no 3.13 wheels
- `streamlit 1.36` predates 3.13 support

The current `requirements.txt` has been updated to:
- Replace `newspaper3k` with `trafilatura` (actively maintained, 3.13 OK)
- Use version floors (`>=`) instead of exact pins, so the resolver picks
  current versions on each Python target
- Add `lxml_html_clean` explicitly so any code path that uses it works

Both 3.12 and 3.13 should work with the current requirements. We default
to 3.12 because it has the longest tail of compatible third-party wheels.

---

## Troubleshooting

**Build error: "lxml.html.clean module is now a separate project"**
You're on an old `requirements.txt`. Pull the latest and confirm it lists
`lxml_html_clean>=0.4`.

**App starts but pages are blank / `streamlit run` works but no output**
Likely a Python 3.13 + old Streamlit issue (the `_TypedDictMeta.__new__()`
error). Either pin Python 3.12 (already done) or upgrade Streamlit to
≥1.40 (already done).

**Build is slow (>5 min) on Railway**
Normal for first build — Streamlit + pandas + numpy + lxml have to compile.
Subsequent builds use Railpack's layer cache and should be ~1 min.

**Scrapers return 0 results**
Most likely the source site changed its HTML. Check `logs/app_*.log`,
update CSS selectors in `config/sources.yaml`, redeploy. Or use the
manual CSV upload path (Settings page).

# K-Water Guard AI Chatbot Setup

The dashboard can show a chatbot button, but the real AI call must run on a backend. Do not put an OpenAI API key inside `index.html`, GitHub Pages, or Google Sites.

## How It Works

1. Dashboard user asks a question.
2. Browser sends the question to your backend URL from `Config.CHATBOT_API_URL`.
3. Backend reads the latest CSV/dashboard context.
4. Backend calls the OpenAI API using a secret server-side API key.
5. Backend returns JSON:

```json
{"answer": "Your answer here"}
```

## Dashboard Configuration

In `Claude.py`:

```python
CHATBOT_ENABLED = True
CHATBOT_API_URL = "https://your-backend-domain.com/api/chat"
```

Keep `CHATBOT_API_URL` empty until the backend is deployed. The widget will still appear, but it will explain that the backend is not connected yet.

## Local AI Backend

`Claude.py` can now run a secure local chatbot proxy. The dashboard talks to this proxy, and the proxy talks to your local OpenAI-compatible AI server. This keeps the API key out of dashboard HTML and browser JavaScript.

PowerShell setup for the current terminal:

```powershell
$env:LOCAL_OPENAI_BASE_URL = "https://your-ngrok-or-local-ai-url"
$env:LOCAL_OPENAI_API_KEY = "paste-your-key-here"
$env:CHATBOT_API_URL = "http://127.0.0.1:8765/api/chat"
```

Start the chatbot backend in one terminal:

```powershell
python Claude.py --serve-chatbot
```

Generate or refresh the dashboard in another terminal with the same `CHATBOT_API_URL` value:

```powershell
python Claude.py
```

Open the generated dashboard and use **Ask AI**. Keep the backend terminal open while chatting.

## Recommended Backend Options

- Vercel serverless function
- Render Flask/FastAPI app
- Cloudflare Worker
- Google Cloud Run

## Important Security Rule

Never expose your OpenAI API key in:

- GitHub Pages
- Google Sites
- `index.html`
- frontend JavaScript

Only the backend should know the API key.

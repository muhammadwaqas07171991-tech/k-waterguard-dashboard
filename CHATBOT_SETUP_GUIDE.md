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

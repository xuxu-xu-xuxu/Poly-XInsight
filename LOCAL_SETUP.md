# Local setup

This workspace is configured for Docker Desktop, an NVIDIA GPU, and DeepSeek.

1. Edit `.env` and replace `LLM_API_KEY=your-deepseek-api-key-here` with a real DeepSeek API key.
2. Start the stack:

```powershell
docker compose up -d --build
```

3. Open the app:

- Frontend: http://localhost:3001 on this machine (`FRONTEND_PORT=3001` because port 3000 is already used by `open-webui`)
- Backend health: http://localhost:8080/api/health
- BGE health: http://localhost:8000/health

The first BGE-M3 startup can take a long time because it may download `BAAI/bge-m3` into `%USERPROFILE%\.cache\huggingface`.

The default `HF_ENDPOINT` is `https://huggingface.co` because it was reachable during setup. You can change it in `.env` if your network needs a mirror.

If the BGE service has GPU/FP16 trouble on the GTX 1080 Ti, set this in `.env` and restart:

```env
BGE_USE_FP16=false
```

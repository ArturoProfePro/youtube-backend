
docker compose up -d               
make migrate
uv run youtube/apps/parser/run.py
make dev

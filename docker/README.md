# Hat Stack Docker

Containerized Hat Stack for ephemeral pipeline runs and persistent MCP server.

## Build

```bash
docker compose -f docker/docker-compose.hat-stack.yml build
```

## Pipeline (one-shot review)

```bash
# Review from stdin
git diff main | docker compose -f docker/docker-compose.hat-stack.yml \
  --profile pipeline run --rm hat-stack-pipeline --diff -

# Review from file
docker compose -f docker/docker-compose.hat-stack.yml \
  --profile pipeline run --rm hat-stack-pipeline \
  --diff /path/to/changes.patch --hats black,blue,purple

# Task runner
docker compose -f docker/docker-compose.hat-stack.yml \
  --profile pipeline run --rm hat-stack-pipeline \
  python scripts/hats_task_runner.py --task generate_code --prompt "Build auth module"
```

## MCP Server (persistent)

```bash
# Start
docker compose -f docker/docker-compose.hat-stack.yml --profile mcp up -d

# View logs
docker logs hat-stack-mcp

# Stop
docker compose -f docker/docker-compose.hat-stack.yml --profile mcp down
```

## Gremlin Overnight Run

```bash
docker compose -f docker/docker-compose.hat-stack.yml \
  --profile gremlin run --rm hat-stack-gremlin
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_LOCAL_URL` | `http://host.docker.internal:11434` | Local Ollama server |
| `OLLAMA_CLOUD_URL` | `https://ollama.com` | Ollama Cloud API |
| `OLLAMA_API_KEY` | (empty) | Cloud API key (optional for local-only) |

## Container Names

| Name | Purpose | Lifecycle |
|------|---------|-----------|
| `hat-stack-mcp` | MCP server (stdio transport) | Persistent |
| `hat-stack-pipeline` | Review/task runner | Ephemeral |
| `hat-stack-gremlin` | Overnight Gremlin loop | Ephemeral |
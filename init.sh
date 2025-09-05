#!/bin/bash


docker compose -p warehouse down -v || true
docker rm -f redis || true

docker build -t warehouse-fastapi-app:latest -f Dockerfile.fastapi .
docker build -t warehouse-mcp:latest      -f Dockerfile.mcp .

docker compose -p warehouse up -d redis fastapi-app

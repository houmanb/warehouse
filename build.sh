#!/bin/bash

docker build --no-cache --pull -t warehouse-fastapi-app:latest -f Dockerfile.fastapi .
docker build --no-cache --pull -t warehouse-mcp:latest      -f Dockerfile.mcp .

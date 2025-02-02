#!/bin/bash
# shellcheck disable=SC2164
cd VFS_VNZ/
echo "Stop container"
docker-compose stop vfs_trpl_bot
docker-compose rm vfs_trpl_bot
docker rmi ilastouski/vfs_trpl_bot:latest
echo "Pull image"
docker pull ilastouski/vfs_trpl_bot:latest
echo "Start vfs_trpl_bot container"
docker-compose up -d --no-deps vfs_trpl_bot
echo "Finish deploying!"
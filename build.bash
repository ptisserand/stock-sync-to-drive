#!/bin/bash -e

PROG_NAME=$(basename ${0})
PROG_DIR=$(dirname $(readlink -f ${0}))


IMAGE_NAME="ptisserand/stock-sync-to-drive"

TAG_DATE="$(date +%Y%m%d)"

git rev-parse HEAD > ${PROG_DIR}/web/static/revision

docker build -t "${IMAGE_NAME}:${TAG_DATE}" .
docker tag "${IMAGE_NAME}:${TAG_DATE}" "${IMAGE_NAME}:latest"
echo "DONE"
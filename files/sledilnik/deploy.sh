#!/bin/bash

# deploy script for green/blue docker-compsoe deploy

DEPLOY_ENV=prod

# compare images, switch deploy if newer image exists
CURRENT_IMAGE=$(docker images docker.pkg.github.com/treker-mk/website/web | grep latest | awk '{print $3}')
docker-compose pull
NEW_IMAGE=$(docker images docker.pkg.github.com/treker-mk/website/web | grep latest | awk '{print $3}')

if [ "$NEW_IMAGE" = "$CURRENT_IMAGE" ]; then
  echo "No new image available"
  exit 0
else
  echo "New image available, starting deploy"
fi


if [ $(docker ps -f name=prod_blue -q) ]
then
    NEW="green"
    OLD="blue"
else
    NEW="blue"
    OLD="green"
fi

echo "Starting "$NEW" container"
docker-compose --project-name=${DEPLOY_ENV}_${NEW} up -d

echo "Waiting..."
sleep 5s

echo "Stopping "$OLD" container"
docker-compose --project-name=${DEPLOY_ENV}_$OLD stop

#!/bin/bash

DEPLOY_ENV=prod

function deploy() {
  SHA=$(curl -s https://api.github.com/repos/sledilnik/website/commits/master | jq .sha)

  echo "Master SHA is $SHA"

  if [ $(docker ps -f name=prod_blue -q) ]
  then
      NEW="green"
      OLD="blue"
  else
      NEW="blue"
      OLD="green"
  fi

  docker-compose pull

  echo "Starting "$NEW" container"
  docker-compose --project-name=${DEPLOY_ENV}_${NEW} up -d

  echo "Waiting..."
  sleep 5s

  echo "Stopping "$OLD" container"
  docker-compose --project-name=${DEPLOY_ENV}_$OLD stop
}

while true; do
  deploy
  sleep 300
done
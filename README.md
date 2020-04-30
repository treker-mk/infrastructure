# Infrastructure

## Provision tarefik (loadbalancer)
```
ansible-playbook -i inventory traefik.yml
```

## Provison sledilnik webserver
```
ansible-playbook -i inventory sledilnik.yml
```

## Edit secrets

```
ansible-vault edit inventory/host_vars/web1/vault.yml
```

## Deployment (quick)

Open byobu (screen)

Preview deploy (`pr-deploy.py`):
```
cd /opt/sledilnik
while true; do ./pr-deploy.py; sleep 60; done
```

Production deploy (`deploy.sh`):
```
cd /opt/sledilnik
while true; do ./deploy.sh; sleep 60; done
```


## Deployment (in depth)

### Production

Production is deployed via docker-compose file (not much config). 
It is using blue/green deploys for zero downtime. 

So basic work done by deploy.sh is to check if there is new docker imaga available. If there is no new image available, just sleep for next minute. 
If it is available, start new container using different project name

This part check which deployment is currently running (green or blue)
```
if [ $(docker ps -f name=prod_blue -q) ]
then
    NEW="green"
    OLD="blue"
else
    NEW="blue"
    OLD="green"
fi
```

Then start container that was not running with new image
```
echo "Starting "$NEW" container"
docker-compose --project-name=${DEPLOY_ENV}_${NEW} up -d
```

Wait for some time

Then stop old deploy
```
echo "Stopping "$OLD" container"
docker-compose --project-name=${DEPLOY_ENV}_$OLD stop
```

### Preview

Preview deploy is done by python script, that checks GH for open PR. If PR is open and has `deploy-preview` label, then script tries to pull corresponding docker image )(having tag `pr-###`). If image exists, then container is run with some flags and labels (remove=True, so it is removed when stopped, also routing labels for tarefik are set).

At same time, for every running preview container, corresponsing PR on GH is checked if it is still open and having `deploy-preview` label. If not, container is stopped.



* https://docs.traefik.io/
* https://docs.docker.com/compose/compose-file/
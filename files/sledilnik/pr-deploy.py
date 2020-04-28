#!/usr/bin/env python3

"""
  Script to check for new PR on repo and deploy apropriate container, if exists
"""

import os
import time
import github
import docker
import CloudFlare
import json
import requests
import logging

logging.basicConfig(
  format='%(asctime)s %(levelname)-8s %(message)s',
  level=logging.INFO,
  datefmt='%Y-%m-%d %H:%M:%S',
  )

logger = logging.getLogger('main')


GH_ORG = "sledilnik"
GH_REPO = "website"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ZONE_ID = '18d0b046b0c0fba45ed566930b832106'

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

if not GITHUB_TOKEN:
  raise Exception("No GITHUB_TOKEN")

g = github.Github(GITHUB_TOKEN)
cf = CloudFlare.CloudFlare()

dclient = docker.from_env()

repo = g.get_repo("{}/{}".format(GH_ORG, GH_REPO))

def delete_pr_zone(num):
  try:
    record = cf.zones.dns_records.get(ZONE_ID, params={'name': 'pr-{}.sledilnik.org'.format(num)})[0]
    cf.zones.dns_records.delete(ZONE_ID, record["id"])
  except IndexError:
    pass

def add_pr_zone(num):
  try:
    cf.zones.dns_records.get(ZONE_ID, params={'name': 'pr-{}.sledilnik.org'.format(num)})[0]
  except IndexError:
    record = {'name':'pr-{}.sledilnik.org'.format(num), 'type':'CNAME', 'content':"web1.sledilnik.org", "proxied": True}
    cf.zones.dns_records.post(ZONE_ID, data=record)

def start(num):
  try:
    image = "docker.pkg.github.com/sledilnik/website/web"
    tag = "pr-{}".format(num)
    container_name = "preview_{}".format(tag)
    
    # try to pull new image, if not exists, return
    try:
      image_id = dclient.images.pull(image, tag=tag).id
    except docker.errors.NotFound:
      return


    # try to stop existing container, if exists
    try:
      container = dclient.containers.get(container_name)
      container_image_id = container.image.id
    except docker.errors.NotFound:
      container = None
      container_image_id = None

    if container_image_id != image_id:
      if container:
        logger.info("Restarting container for PR-{}".format(num))
        container.stop()
      else:
        logger.info("Starting container for PR-{}".format(num))

      labels = {
        "traefik.enable": "true",
        "traefik.port": "80",
        "traefik.http.routers.sledilnik-{}.rule".format(tag): "HostRegexp(`{}.sledilnik.org`)".format(tag),
        "traefik.http.routers.sledilnik-{}.tls".format(tag): "true",
      }
      dclient.containers.run("{}:{}".format(image, tag), name=container_name, auto_remove=True, network="lb_traefik", labels=labels, detach=True)
    
      if SLACK_WEBHOOK_URL:
        slack_data = {
          "text": "Preview deploy availabe",
          "attachments": [
              {
                  "text": "URL: https://pr-{}.sledilnik.org".format(num)
              },
              {
                  "text": "PR: https://github.com/sledilnik/website/pull/{}".format(num)
              }
          ]
        }
        requests.post(
          SLACK_WEBHOOK_URL, data=json.dumps(slack_data),
          headers={'Content-Type': 'application/json'}
        )
  except docker.errors.NotFound:
    logger.info("No docker image for PR-{} found".format(num))
  except docker.errors.APIError:
    pass

def pr_open(pr):
  if not pr:
    return False
  return pr.state == 'open' and 'deploy-preview' in map(lambda l: l.name, pr.labels)


if __name__ == "__main__":
  logger.info("Checking for deployable PR")
  container_prefix = 'preview_pr-'
  for container in dclient.containers.list(filters={'name': container_prefix}):
    pr_num = int(container.name.lstrip(container_prefix))
    if not pr_open(repo.get_pull(pr_num)):
      logger.info("PR-{} is closed, stopping container", pr_num)
      container.stop()
      delete_pr_zone(pr_num)
    

  for pr in repo.get_pulls(state='open', sort='created'):
    pr_num = pr.number
    if pr_open(pr):
      start(pr_num)
      add_pr_zone(pr_num)
    else:
      logger.info("Skipping PR-{}".format(pr_num))
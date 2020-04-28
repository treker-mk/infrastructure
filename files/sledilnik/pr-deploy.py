#!/usr/bin/env python3
import os
import time
import github
import docker
import CloudFlare

GH_ORG = "sledilnik"
GH_REPO = "website"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ZONE_ID = '18d0b046b0c0fba45ed566930b832106'

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
  print("Starting container for PR-{}".format(num))
  try:
    image = "docker.pkg.github.com/sledilnik/website/web"
    tag = "pr-{}".format(num)
    dclient.images.pull(image, tag=tag)
    labels = {
      "traefik.enable": "true",
      "traefik.port": "80",
      "traefik.http.routers.sledilnik-preview.rule": "HostRegexp(`{}.sledilnik.org`)".format(tag),
      "traefik.http.routers.sledilnik-preview.tls": "true",
    }
    dclient.containers.run("{}:{}".format(image, tag), name="preview_{}".format(tag), auto_remove=True, network="lb_traefik", labels=labels, detach=True)
  except docker.errors.NotFound:
    print("No docker image for PR-{} found".format(num))
  except docker.errors.APIError:
    pass

def pr_open(pr):
  if not pr:
    return False
  return pr.state == 'open' and 'deploy-preview' in map(lambda l: l.name, pr.labels)

if __name__ == "__main__":
  print("Checking for deployable PR")
  container_prefix = 'preview_pr-'
  for container in dclient.containers.list(filters={'name': container_prefix}):
    pr_num = int(container.name.lstrip(container_prefix))
    if not pr_open(repo.get_pull(pr_num)):
      print("PR-{} is closed, stopping container", pr_num)
      container.stop()
      delete_pr_zone(pr_num)
    

  for pr in repo.get_pulls(state='open', sort='created'):
    pr_num = pr.number
    if pr_open(pr):
      start(pr_num)
      add_pr_zone(pr_num)
    else:
      print("Skipping PR-{}".format(pr_num))
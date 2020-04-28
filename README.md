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
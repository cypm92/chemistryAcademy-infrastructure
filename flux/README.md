# Flux CD

Flux observa exclusivamente `main` de `cypm92/chemistryAcademy-infrastructure`
y aplica `kubernetes/clusters/production` mediante Kustomize. El manifiesto
que define esta sincronización vive en:

`kubernetes/clusters/production/flux-system/gotk-sync.yaml`.

Los controladores se instalan con el playbook Ansible `playbooks/flux.yml` y
la clave SSH de solo lectura se guarda como Secret dentro del clúster. No hay
credenciales en este repositorio.

Una publicación en GHCR no cambia el clúster por sí misma. Solo se despliega
una imagen cuando un manifiesto con su etiqueta inmutable llega a `main`.

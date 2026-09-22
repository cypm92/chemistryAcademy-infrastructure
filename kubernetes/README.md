# Kubernetes

Los manifiestos se organizarán con Kustomize:

- `base/`: recursos reutilizables sin secretos ni datos de dominio.
- `clusters/production/`: composición de producción y referencias a imágenes inmutables.

Los secretos se añaden cifrados mediante SOPS con la extensión `.sops.yaml`.
Flux descifra únicamente los campos `data` y `stringData` al sincronizar el
clúster. Nunca se añade una clave privada ni un manifiesto en claro a Git.

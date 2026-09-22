# Kubernetes

Los manifiestos se organizarán con Kustomize:

- `base/`: recursos reutilizables sin secretos ni datos de dominio.
- `clusters/production/`: composición de producción y referencias a imágenes inmutables.

Los secretos se añadirán cifrados mediante SOPS cuando Flux esté configurado.

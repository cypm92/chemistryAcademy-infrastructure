# Kubernetes

Los manifiestos se organizarán con Kustomize:

- `base/`: recursos reutilizables sin secretos ni datos de dominio.
- `apps/production/`: base operativa de Be Ciencia: PostgreSQL, API, archivos y
  frontend, aún sin activar en el clúster.
- `clusters/production/`: composición de producción y referencias a imágenes inmutables.

Los secretos se añaden cifrados mediante SOPS con la extensión `.sops.yaml`.
Flux descifra únicamente los campos `data` y `stringData` al sincronizar el
clúster. Nunca se añade una clave privada ni un manifiesto en claro a Git.

`apps/production/` se prepara antes de activarse expresamente desde
`clusters/production/`. Esta separación evita que una infraestructura a medio
configurar cree Pods con imágenes o secretos de ejemplo. Para activarla hacen
falta los dos Secrets reales cifrados con SOPS, etiquetas de imagen inmutables
`sha-<commit>` publicadas en GHCR y la referencia desde el clúster.

Los dos Secrets son `beciencia-runtime` (base de datos, firma JWT y contraseña
inicial de administración) y `ghcr-pull` (lectura de imágenes privadas). El
script `scripts/create-production-secrets.py` crea ambos cifrados sin escribir
valores en claro en disco. El `imagePullSecret` solo se usa para descargar las
imágenes; la aplicación no recibe el token de GitHub como variable de entorno.

La aplicación reserva 5 GiB para PostgreSQL y 15 GiB para archivos con el
almacenamiento local de K3s. Es suficiente para la primera versión, pero los
vídeos grandes se moverán a almacenamiento de objetos antes de crecer.

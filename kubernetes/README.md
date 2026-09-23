# Kubernetes

Los manifiestos se organizarán con Kustomize:

- `base/`: recursos reutilizables sin secretos ni datos de dominio.
- `apps/production/`: PostgreSQL, API, archivos y frontend activos solo dentro
  del clúster.
- `clusters/production/`: composición de producción y referencias a imágenes inmutables.

Los secretos se añaden cifrados mediante SOPS con la extensión `.sops.yaml`.
Flux descifra únicamente los campos `data` y `stringData` al sincronizar el
clúster. Nunca se añade una clave privada ni un manifiesto en claro a Git.

`clusters/production/` incluye la aplicación solo después de comprobar los
dos Secrets reales cifrados con SOPS y las etiquetas de imagen inmutables
`sha-<commit>` publicadas en GHCR. No contiene Ingress: todavía no hay acceso
público ni dominio.

Los dos Secrets son `beciencia-runtime` (base de datos, firma JWT y contraseña
inicial de administración) y `ghcr-pull` (lectura de imágenes privadas). El
script `scripts/create-production-secrets.py` crea ambos cifrados sin escribir
valores en claro en disco. El `imagePullSecret` solo se usa para descargar las
imágenes; la aplicación no recibe el token de GitHub como variable de entorno.

La aplicación reserva 5 GiB para PostgreSQL y 15 GiB para archivos con el
almacenamiento local de K3s. Es suficiente para la primera versión, pero los
vídeos grandes se moverán a almacenamiento de objetos antes de crecer.
Los volúmenes locales no son una copia de seguridad; su restauración debe
prepararse y probarse antes de abrir el servicio al público.

Para comprobar el despliegue por SSH en el VPS:

```bash
sudo kubectl get kustomization -n flux-system flux-system
sudo kubectl get pods,pvc -n beciencia
sudo kubectl exec -n beciencia deploy/frontend -- wget -qO- http://127.0.0.1/api/health
sudo kubectl get ingress -A
```

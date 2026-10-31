# Arquitectura objetivo de producción

## Alcance inicial

Un VPS OVH VPS-1 ejecutará K3s en un único nodo. Es una configuración adecuada para esta primera versión, pero no proporciona alta disponibilidad: si el VPS deja de estar disponible, también lo estará la web hasta que se recupere o se reconstruya en otro servidor.

## Componentes

| Componente | Responsabilidad | Ubicación |
| --- | --- | --- |
| K3s | Orquestación de contenedores | VPS Ubuntu |
| Caddy | Entrada HTTP/HTTPS y certificados Let's Encrypt | Pod K3s con hostNetwork; cuando se active el dominio |
| Frontend | Aplicación web Vue | Deployment Kubernetes |
| Backend | API FastAPI | Deployment Kubernetes, interno salvo rutas API |
| PostgreSQL | Datos transaccionales | StatefulSet y volumen persistente del VPS |
| Object Storage | PDFs y vídeos | OVH Public Cloud, pendiente de activar |
| Flux CD | Sincronización GitOps | K3s y este repositorio |
| GHCR | Imágenes Docker de frontend y backend | GitHub Container Registry |

## Límites de red

```text
Internet → HTTPS / Caddy → frontend y API
                                │
                                ├── PostgreSQL (solo red interna)
                                └── Object Storage (S3 mediante credenciales)
```

No se expondrán públicamente PostgreSQL, el panel de K3s, Traefik ni Flux.

## Ingreso HTTPS permanente (preparado, aún no activado)

`kubernetes/apps/production/caddy-ingress.yaml` declara Caddy como único
ingreso público, enlazado a TCP 80/443 del host mediante `hostNetwork` y
`hostPort`. Solo reenvía a `frontend.beciencia.svc.cluster.local:80`; Nginx del
frontend conserva el proxy `/api` al backend interno. No se publican NodePorts,
el backend, PostgreSQL ni el plano de control. UFW ya permite únicamente SSH
(22), HTTP (80) y HTTPS (443); no hace falta abrir otros puertos. El firewall
de OVH/red debe revisarse también antes de activar el ingreso.

Caddy conserva certificados y claves ACME en el PVC `caddy-data` (StorageClass
K3s `local-path`, 1 GiB, `ReadWriteOnce`). Mantener ese PVC al recrear el pod y
respaldar sus datos con acceso restringido; perderlo fuerza nuevas solicitudes
ACME y puede alcanzar límites de Let's Encrypt. `/config` es efímero porque la
configuración declarativa vive en ConfigMap. El correo ACME es opcional y puede
configurarse antes de activar. El HTTP-01 de Caddy requiere que el DNS público
de ambos nombres apunte al VPS y TCP 80/443 llegue a él.

Estado conocido al preparar este cambio: `beciencia.es` tiene A público
`213.186.33.5`; el IPv4 confirmado del VPS es `51.254.216.174`. Por tanto no
activar todavía la solicitud de certificados ni retirar el túnel. En el corte,
actualizar solo los A web de apex y `www` a `51.254.216.174`; conservar MX,
SPF, TXT, DNSSEC y demás registros de correo/verificación sin cambios. Verificar
ambos nombres desde resolutores públicos y probar HTTP-01 antes de considerar
completado el corte. La declaración GitOps requiere revisión y merge a `main`
para que Flux la aplique; esta preparación no despliega nada.

La configuración Caddy y el túnel temporal no deben estar activos a la vez:
ambos reclaman el mismo frontend lógico y el túnel mantendría un camino público
alternativo. Coordinar desactivación del túnel en el cambio de activación,
después de aprobar y probar el acceso permanente; no quitarlo en esta preparación.

## Recuperación

La reproducción de un servidor se hará con Ansible y los manifiestos GitOps. Los datos se recuperarán con copias de PostgreSQL y los documentos/vídeos se conservarán en Object Storage. El procedimiento exacto se documentará y probará antes de producción.

# Arquitectura objetivo de producción

## Alcance inicial

Un VPS OVH VPS-1 ejecutará K3s en un único nodo. Es una configuración adecuada para esta primera versión, pero no proporciona alta disponibilidad: si el VPS deja de estar disponible, también lo estará la web hasta que se recupere o se reconstruya en otro servidor.

## Componentes

| Componente | Responsabilidad | Ubicación |
| --- | --- | --- |
| K3s | Orquestación de contenedores | VPS Ubuntu |
| Traefik | Entrada HTTP/HTTPS del clúster | K3s |
| cert-manager | Certificados Let's Encrypt | K3s, cuando exista dominio |
| Frontend | Aplicación web Vue | Deployment Kubernetes |
| Backend | API FastAPI | Deployment Kubernetes, interno salvo rutas API |
| PostgreSQL | Datos transaccionales | StatefulSet y volumen persistente del VPS |
| Object Storage | PDFs y vídeos | OVH Public Cloud, pendiente de activar |
| Flux CD | Sincronización GitOps | K3s y este repositorio |
| GHCR | Imágenes Docker de frontend y backend | GitHub Container Registry |

## Límites de red

```text
Internet → HTTPS / Ingress → frontend y API
                                │
                                ├── PostgreSQL (solo red interna)
                                └── Object Storage (S3 mediante credenciales)
```

No se expondrán públicamente PostgreSQL, el panel de K3s, Traefik ni Flux.

## Recuperación

La reproducción de un servidor se hará con Ansible y los manifiestos GitOps. Los datos se recuperarán con copias de PostgreSQL y los documentos/vídeos se conservarán en Object Storage. El procedimiento exacto se documentará y probará antes de producción.

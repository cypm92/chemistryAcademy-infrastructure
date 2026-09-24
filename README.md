# Infraestructura de Be Ciencia

Este repositorio contiene la infraestructura reproducible del entorno de producción de Be Ciencia. El código de la aplicación continúa en sus repositorios propios:

- Frontend: <https://github.com/cypm92/chemistryAcademy-frontend>
- Backend: <https://github.com/cypm92/chemistryAcademy-backend>

## Objetivo

Poder reconstruir el servicio en un servidor Ubuntu nuevo con cambios auditables mediante Git:

1. OpenTofu/Terraform gestiona los recursos externos compatibles (DNS, almacenamiento de objetos y estado remoto).
2. Ansible prepara y endurece el VPS.
3. K3s ejecuta la aplicación en un clúster Kubernetes de un solo nodo.
4. Flux CD aplica desde este repositorio la configuración declarativa de producción.
5. GitHub Actions publica imágenes inmutables desde `main`; no se despliega nada desde `develop`.

## Estado actual

El VPS ya está preparado con Ansible y ejecuta K3s y Flux CD. Flux observa
`main` de este repositorio y mantiene PostgreSQL, backend y frontend dentro
del clúster. Los Secrets de producción están cifrados con SOPS + age y las
imágenes se publican desde `main` de sus respectivos repositorios en paquetes
privados de GHCR. No hay Ingress ni dominio configurado: la aplicación aún no
está expuesta públicamente. No se ha creado ningún recurso de pago adicional.

## Estructura

| Ruta | Propósito |
| --- | --- |
| `terraform/` | Recursos de OVH y estado remoto de OpenTofu/Terraform. |
| `ansible/` | Preparación reproducible de Ubuntu y K3s. |
| `kubernetes/` | Manifiestos base de la aplicación y configuración por entorno. |
| `flux/` | Declaración GitOps que Flux sincronizará. |
| `docs/` | Decisiones, arquitectura y procedimientos operativos. |
| `scripts/` | Utilidades seguras y documentadas. |

## Flujo previsto

```text
develop ──PR/merge──> main ──> GitHub Actions construye imágenes en GHCR
                                      │
                                      ▼
                       propone la referencia inmutable en develop
                                      │
                                      ▼
                       revisión/merge a main de infraestructura
                                      │
                                      ▼
                              Flux CD sincroniza K3s
```

`develop` ejecutará validaciones, pero no publicará ni desplegará producción. Un revert de Git sobre la referencia de imagen permitirá volver a una versión previa.
La promoción programada y su activación se documentan en
[`docs/image-promotion.md`](docs/image-promotion.md).

## Principios de seguridad

- Nunca guardar contraseñas, tokens, ficheros `.env`, claves privadas ni estados de Terraform en Git.
- Los secretos GitOps se almacenan cifrados con SOPS + age. La identidad
  privada se conserva exclusivamente en el VPS/Flux y en una copia de
  recuperación local ignorada por Git.
- PostgreSQL no se expondrá a Internet.
- El tráfico público será únicamente HTTPS cuando se conecte el dominio.
- La estrategia provisional de recuperación utiliza el backup Standard incluido
  de OVHcloud. Sus límites y el procedimiento están en
  [`docs/disaster-recovery.md`](docs/disaster-recovery.md); su restauración aún
  no se ha ensayado.

## Siguiente tarea

Verificar en OVHcloud el estado y la fecha de la última copia Standard,
preparar un ensayo de restauración sin afectar producción y activar la
promoción automática de imágenes con una credencial limitada. El dominio,
HTTPS y la exposición pública quedan para el último paso.

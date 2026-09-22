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

La estructura está creada, pero **no aplica cambios al VPS ni crea recursos de pago**. Cada capa se implementará y verificará en una tarea independiente.

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
                       actualiza la referencia inmutable en este repositorio
                                      │
                                      ▼
                              Flux CD sincroniza K3s
```

`develop` ejecutará validaciones, pero no publicará ni desplegará producción. Un revert de Git sobre la referencia de imagen permitirá volver a una versión previa.

## Principios de seguridad

- Nunca guardar contraseñas, tokens, ficheros `.env`, claves privadas ni estados de Terraform en Git.
- Usar secretos cifrados con SOPS + age cuando se llegue a la fase GitOps.
- PostgreSQL no se expondrá a Internet.
- El tráfico público será únicamente HTTPS cuando se conecte el dominio.
- Las copias de seguridad y su restauración se probarán antes de considerar listo el entorno.

## Siguiente tarea

Configurar las protecciones de ramas y las comprobaciones de CI en los tres repositorios, manteniendo el despliegue reservado exclusivamente para `main`.

# ADR 0001: Plataforma inicial de producción

**Estado:** aceptada para la primera versión

## Decisión

Se utilizará un VPS OVH VPS-1 existente con Ubuntu y un clúster K3s de un nodo. La configuración del servidor se aplicará mediante Ansible. La configuración de la aplicación se gestionará mediante GitOps con Flux CD.

OpenTofu/Terraform se empleará donde aporte valor para recursos externos reproducibles, como DNS de dominio, Object Storage y backend remoto de estado. No se utilizará para crear ni reinstalar el VPS adquirido, de forma que el servidor existente no quede ligado a funcionalidades incompletas del proveedor.

## Consecuencias

- El coste y consumo de recursos se mantiene bajo para una primera versión.
- No hay alta disponibilidad; un fallo de VPS causa indisponibilidad temporal.
- El despliegue ordinario no requiere acceso SSH: el cambio en `main` genera una imagen y Flux sincroniza la versión declarada.
- Para una recuperación completa harán falta copias verificadas de PostgreSQL y Object Storage.

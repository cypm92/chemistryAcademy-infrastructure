# Chemistry Academy — reglas para el agente de infraestructura

## Alcance y flujo de trabajo
- Este repositorio contiene infraestructura, CI/CD, Kubernetes, Ansible y configuración GitOps. Mantén los cambios dentro de él, salvo que se solicite explícitamente coordinar cambios con los repositorios de la aplicación.
- Trabaja en la rama actual. No cambies de rama, crees commits, hagas push o merge, publiques imágenes, apliques cambios de infraestructura ni despliegues sin autorización expresa del usuario.
- Antes de hacer cambios, revisa `git status` y la documentación/los flujos de trabajo pertinentes. Conserva todos los cambios existentes; nunca hagas reset ni limpies el repositorio.
- Trata producción como un entorno activo y sensible. Prioriza validaciones estáticas y pruebas locales/unitarias; no contactes servidores ni servicios de producción sin autorización expresa.

## Seguridad y secretos
- Nunca inspecciones, imprimas, copies ni confirmes en Git secretos en texto claro, archivos `.env`, claves privadas, archivos SOPS descifrados, estado de Terraform ni credenciales. No incluyas secretos en instrucciones ni informes.
- No descifres datos SOPS ni cambies secretos de producción salvo que el usuario autorice expresamente esa operación concreta.
- Nunca expongas públicamente PostgreSQL, los planos de control del clúster, Flux ni otros servicios internos.
- No cambies el cortafuegos, DNS, recursos de pago, referencias de imágenes de producción ni volúmenes persistentes sin aprobación expresa y un plan revisado.
- No ejecutes `terraform/tofu apply`, `kubectl apply`, `helm upgrade`, scripts de producción ni comandos destructivos sobre volúmenes/bases de datos sin aprobación expresa.

## Validación y publicación
- Usa las comprobaciones documentadas en el repositorio y en CI, incluidas la generación/validación de manifiestos y las pruebas unitarias pertinentes.
- Informa de los comandos exactos y sus resultados; diferencia una validación estática de un despliegue real.
- Editar la configuración GitOps no significa que algo esté desplegado. La promoción y el despliegue a producción requieren autorización expresa del usuario y verificación posterior mediante lectura del estado.

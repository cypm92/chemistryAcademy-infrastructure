# Mantenimiento GitOps: preparación, no activada

Estos overlays no están referenciados por producción. No hacer commits, push,
merge, cambios en el clúster ni ejecutar los comandos de observación siguientes
sin autorización expresa y un plan de ventana aprobado. Flux sigue `main`,
`./kubernetes/clusters/production`, con `prune: true` y `wait: true`: no basta
con preparar un commit en `develop` y no se debe dejar que Flux salte fases
porque se publiquen varios commits antes de que reconcilie cada uno.

## Condiciones previas

- Confirmar el estado real, rutas públicas, nombres, réplicas, HPA, otros
  controladores y recursos no gestionados; cerrar o cubrir **todos** los caminos
  alternativos antes de continuar. En particular, `temporary-preview-tunnel`
  apunta directamente al frontend y no pasa por Caddy: verificar que no exista
  ningún túnel activo ni entrada alternativa. También verificar accesos directos
  o internos a backend, tareas programadas y consumidores externos. No seguir
  si alguno puede escribir durante la ventana.
- Confirmar copias y restauración probada de PostgreSQL **y** archivos; evaluar
  compatibilidad de migraciones hacia delante/atrás, disponibilidad de imágenes
  inmutables anteriores/nuevas y plan de recuperación de cola. El lock
  advisory de la versión nueva no protege procesos de versiones antiguas.
- Verificar antes de la ventana cómo el worker termina tareas en curso, tiempos
  de gracia, claims, reintentos y posible duplicación de correos. Escalar a cero
  no garantiza drenaje limpio ni entrega exactamente una vez. Si no se puede
  demostrar seguridad, detenerse y resolverlo antes de operar.
- Estos overlays conservan las identidades de recursos y PVC, sin sustituir el
  Kustomization de Flux ni eliminar recursos. Comparar renders e inventario real
  antes de cada cambio: con `prune: true`, cualquier recurso omitido puede ser
  eliminado. No suspender Flux ni usar `kubectl scale` como estado deseado.
- El cambio fuerza un rollout de Caddy mediante una anotación del pod; un cambio
  de ConfigMap montado por sí solo no implica recarga de Caddy. Recreate puede
  causar una breve interrupción. El ConfigMap y el Deployment no se aplican de
  forma transaccional: comprobar la respuesta real; si carga configuración vieja,
  esperar la proyección y publicar un cambio GitOps adicional en la anotación
  para reiniciar Caddy de nuevo. Repetir esta comprobación al reabrir. La sonda
  TCP solo comprueba el puerto, no el 503. No cambiar los puertos HTTP/HTTPS ni
  bloquear desafíos ACME; confirmar renovación y certificado en el entorno real.

## Fases; cada una requiere autorización y observación antes de la siguiente

Todos los cambios de rutas siguientes se refieren exclusivamente a la entrada
`../../apps/production` en `kubernetes/clusters/production/kustomization.yaml`.
Mantener recursos Flux y SOPS intactos. No publicar las fases juntas.

1. **Cerrar tráfico**: en un cambio GitOps independiente sustituir esa entrada
   por `../../apps/maintenance-gate`. Tras promoción aprobada a `main`, esperar
   que Flux aplique exactamente esa revisión y que Caddy termine su rollout.
   Verificar desde fuera HTTPS para ambos dominios y varias rutas GET y POST,
   incluidas las API: respuestas 503, sin caché y sin redirección al frontend.
   Verificar también todas las entradas alternativas y conexiones persistentes;
   el 503 no cancela solicitudes que ya estaban en curso. Comprobar que ninguna
   de ellas todavía puede producir escrituras antes de la fase siguiente.
2. **Parada**: solo después de confirmar el cierre, cambiar la entrada a
   `../../apps/maintenance-stopped` y promover por separado. Esperar la revisión
   exacta de Flux y comprobar `spec.replicas=0` y ausencia real de pods antiguos
   de backend y worker, incluidos pods `Terminating`, procesos huérfanos y tareas
   en curso. Comprobar también que ninguna otra fuente escribe. No basta con
   esperar al estado Ready de Flux; si no se puede demostrar el drenaje, parar.
3. **Actualizar**: con ambos detenidos, promover en otra revisión las referencias
   de imagen aprobadas en `apps/production`, para API y worker de forma coherente.
   El overlay stopped sigue imponiendo cero réplicas. Verificar renders e imagen
   deseada, revisión exacta y que siguen sin existir pods. No arrancar mezclas
   de binarios antiguos/nuevos; evaluar migraciones antes de arrancar cualquiera.
4. **Arranque cerrado**: cambiar por separado a `../../apps/maintenance-gate`.
   Sigue el 503; se recuperan las réplicas declaradas en production. Verificar
   que solo corren las imágenes aprobadas, disponibilidad y salud de API, worker,
   base de datos y cola; el worker no tiene readiness probe propia. Validar el
   funcionamiento mediante un método interno autorizado que no exponga datos ni
   dispare operaciones irreversibles. Si falla, volver a stopped y diagnosticar.
5. **Reabrir**: únicamente tras pruebas satisfactorias, volver por separado a
   `../../apps/production`. Esperar revisión y rollout de Caddy, verificar que se
   sirve realmente la configuración normal y probar ambos dominios, frontend y
   API, certificados y funcionamiento del worker. Si Caddy siguiera con 503,
   aplicar la corrección GitOps del rollout descrita arriba; no asumir recarga.

En cada fase comprobar el revisionado aplicado de `Kustomization/flux-system`
y `GitRepository/flux-system`, estado de reconciliación, despliegues, pods y
respuestas. Ejecutar estas lecturas únicamente después de autorización:

```sh
kubectl -n flux-system get kustomization flux-system -o yaml
kubectl -n flux-system get gitrepository flux-system -o yaml
kubectl -n beciencia get deployments,pods -o wide
kubectl -n beciencia rollout status deployment/caddy-ingress
curl -i https://beciencia.es/
curl -i https://www.beciencia.es/api/health
```

Las comprobaciones anteriores son ejemplos, no una lista exhaustiva de rutas ni
un mecanismo para forzar reconciliación. No imprimir secretos ni datos de cola.

## Rollback

Si falla antes de actualizar y la compatibilidad está confirmada, mantener o
restablecer primero el gate, esperar su 503 efectivo y volver por etapas a la
composición anterior. Si ya se arrancó código nuevo o se modificó el esquema,
**no** volver automáticamente a la imagen vieja: primero parar de nuevo API y
worker con `maintenance-stopped` y demostrar ausencia de procesos/escrituras;
evaluar compatibilidad de esquema, cola y efectos externos. Si es compatible,
restaurar ambas referencias anteriores juntas mientras siguen a cero; después
pasar por gate, validar y reabrir. Si no es compatible, mantener 503 y cero,
seguir un plan de migración inversa o restauración de copias aprobado, teniendo
en cuenta pérdida de datos y efectos externos; no borrar PVC ni restaurar a
ciegas. En cada paso, esperar revisión exacta y verificación real. Revertir un
commit completo que cambió recursos podría activar prune: revisar el render.

## Prueba local

`kubectl kustomize kubernetes/apps/production`, `kubectl kustomize kubernetes/apps/maintenance-gate`,
`kubectl kustomize kubernetes/apps/maintenance-stopped` y
`python -m unittest discover -s scripts -p 'test_maintenance.py' -v` no contactan
el clúster. La prueba estática no demuestra TLS, ACME, drenaje, recarga ni Flux.

# Reparación de promoción de imágenes

El workflow comprueba CI y publicación GHCR de cada `main` de aplicación; el
backend y el worker comparten imagen. Construye la propuesta desde `main` de
infraestructura en `automation/promote-production-images`, nunca en `develop`.
La PR requiere revisión y merge humanos. Flux continúa siguiendo `main`.
La rama existente se comprueba antes de reemplazarla; el push usa
`--force-with-lease`. Si base y contenido no cambian se conserva la revisión.
Si no quedan cambios se cierra la PR propia sin fusionar, solo si no contiene
revisiones, comentarios o etiquetas ni está en borrador. La misma regla protege
el reemplazo de la rama; si existe contexto humano se detiene y pide revisión.
Si otra PR abierta modifica los manifiestos o el estado de imágenes, la
ejecución falla para que una persona resuelva el solapamiento; no cierra PR ajenas.

## Activación

1. Antes de publicar, decidir y desactivar temporalmente el workflow antiguo o
   su credencial. El cron utiliza el workflow de la rama predeterminada
   `develop`, que todavía contiene la versión anterior. No cambiar esa rama
   predeterminada sin autorización.
2. Revisar las PR antiguas #27 y #28 y cualquier otra que toque imágenes;
   decidir manualmente si cerrarlas o fusionarlas. Siguen siendo fusionables;
   la nueva automatización no las desactiva por sí misma.
3. Revisar y aprobar el cambio, publicarlo y fusionarlo en `main`. Integrar
   luego `main` en `develop` mediante PR `main` → `develop`, revisando y
   resolviendo conflictos sin perder trabajo. Confirmar que el workflow nuevo
   está en `develop` antes de reactivarlo; no reset ni force push a `develop`.
   Repetir la sincronización tras cambios aprobados de `main`.
4. Reactivar y ejecutar manualmente desde `develop`. Verificar logs y que no
   haya escrituras en `develop`; ante una publicación, revisar contenido de la
   PR y requerir CI y aprobación humana en la protección de `main`.

El secreto `INFRA_PROMOTION_TOKEN` del environment homónimo necesita Contents y
Pull requests lectura/escritura y Metadata lectura en infraestructura y acceso
necesario de lectura a los repositorios de aplicación. No guardar credenciales
localmente. Faltas de credencial o publicación impiden promover.

## Riesgos

La comprobación de `main` previa al push no es atómica con él: podría avanzar
inmediatamente después. La siguiente ejecución actualiza la PR; exigir rama
al día y revisión antes de fusionar. También puede abrirse una PR concurrente
tras comprobar duplicados. Las comprobaciones de propiedad del commit de bot
son defensivas, no una autenticación criptográfica de autoría. Proteger la
rama exclusiva y limitar quién puede escribirla. El flujo GitHub remoto no se
ha ejecutado durante la reparación local.

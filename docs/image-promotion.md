# Promoción de imágenes entre repositorios

## Qué hace

El workflow `.github/workflows/promote-images.yml` se ejecuta cada 15 minutos
o manualmente. Para frontend y backend consulta el commit actual de `main`,
comprueba que su CI de ese mismo commit terminó correctamente y que la tarea
**Publicar imagen de producción en GHCR** tuvo éxito. Solo entonces actualiza en
`develop` las etiquetas inmutables `sha-<commit>` de los manifiestos.

La imagen backend se actualiza en ambos Deployments: `backend.yaml` y
`notification-worker.yaml`. Comparten el mismo paquete/commit porque el worker
usa el módulo Python del backend. La imagen frontend se actualiza en
`frontend.yaml`. Las imágenes de `develop` de las aplicaciones nunca se
consideran.

Si hay cambios, el workflow abre o actualiza una PR de `develop` a `main`. La
PR no se fusiona automáticamente: una persona debe revisarla y fusionarla para
que Flux despliegue el cambio. Si CI de la aplicación falla o sigue en curso,
no se promueve la imagen.

`kubernetes/clusters/production/image-promotion-state.json` guarda el último
commit de aplicación ya procesado. Por eso una reversión manual que cambie
solo la imagen del manifiesto no se deshace en la siguiente ejecución; una
nueva publicación desde `main` sí vuelve a proponer una imagen.

La ejecución programada puede retrasarse por la carga de GitHub. No se
garantiza despliegue inmediato. El workflow es gratuito con runners estándar
para estos repositorios públicos, según la [política de facturación de
GitHub](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## Credencial de promoción

La automatización usa el secreto de Actions `INFRA_PROMOTION_TOKEN` guardado
en el *environment* del mismo nombre dentro del repositorio de
**infraestructura**. El job declara ese environment con `deployment: false`:
puede leer el secreto sin crear un registro de despliegue. Debe ser una
credencial nueva y limitada exclusivamente a
`cypm92/chemistryAcademy-infrastructure`, con permisos de repositorio:

- `Contents`: lectura y escritura, para actualizar `develop`;
- `Pull requests`: lectura y escritura, para abrir la PR;
- `Metadata`: lectura (GitHub la incluye automáticamente).

Una fine-grained personal access token es la opción sencilla para esta primera
versión. Elegir una caducidad y registrar un recordatorio para renovarla. No
usar un token clásico amplio ni reutilizar el token personal de `gh auth`.
Guardar el valor **solo** como secreto de GitHub Actions; nunca en el
repositorio, un comando compartido o una captura. La creación y carga del
token requieren una decisión explícita del propietario de la cuenta.

Una vez añadido, lanzar manualmente **Proponer nuevas imágenes de producción**
desde Actions para comprobar que informa «No hay imágenes nuevas que proponer».
Las etiquetas actuales ya coinciden con las últimas publicaciones de `main`.
Después, una publicación nueva abrirá la PR. Revisar que contiene únicamente
las imágenes esperadas antes de fusionarla.

El secreto del environment se configuró el 24-09-2026. Una ejecución manual
confirmó que el job pudo leer GitHub y que no había imágenes nuevas. El paso
de escritura en `develop` y creación de PR se verificará con la próxima
publicación real.

## Fallos y límites

- Si falta el secreto, el workflow termina sin escribir nada.
- Si falla una consulta a GitHub o falta la publicación, termina con error y
  no modifica `develop`.
- Si otro cambio llega a `develop` durante el push, este fallará sin forzar;
  la siguiente ejecución reintentará.
- Si `develop` contiene otros cambios pendientes, la PR a `main` también los
  incluirá. Revisarla antes de fusionar.
- La caducidad o revocación del token detiene la promoción, pero no altera
  las imágenes ya desplegadas.

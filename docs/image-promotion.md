# Promoción de imágenes entre repositorios

## Qué hace

El workflow `.github/workflows/promote-images.yml` se ejecuta cada 15 minutos
o manualmente. Para frontend y backend consulta el commit actual de `main`,
comprueba que el workflow de CI de ese mismo commit terminó correctamente y
que su tarea **Publicar imagen de producción en GHCR** tuvo éxito. Solo
entonces actualiza en `develop` de este repositorio la etiqueta inmutable
`sha-<commit>` del manifiesto correspondiente.

Si hay cambios, abre o actualiza una PR de `develop` a `main`. **La PR no se
fusiona automáticamente**: una persona debe revisar y fusionar, y solo al
llegar a `main` Flux despliega el cambio. Si la CI de la aplicación falla o
sigue en curso, no se promueve la imagen. Las imágenes de `develop` de las
aplicaciones nunca se consideran.

`kubernetes/clusters/production/image-promotion-state.json` guarda el último
commit de aplicación ya procesado. Por eso una reversión manual que cambie
solo la imagen del manifiesto no se deshace en la siguiente ejecución; una
nueva publicación desde `main` sí vuelve a proponer una imagen.

La ejecución programada puede retrasarse por la carga de GitHub. No se
garantiza despliegue inmediato. El workflow es gratuito con runners estándar
para estos repositorios públicos, según la [política de facturación de
GitHub](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## Activación pendiente

La automatización queda inactiva hasta añadir el secreto de Actions
`INFRA_PROMOTION_TOKEN` al repositorio de **infraestructura**. Debe ser una
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

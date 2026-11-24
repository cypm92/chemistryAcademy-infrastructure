# Excepción temporal de AppArmor para PostgreSQL

El manifiesto declara `Unconfined` únicamente para el contenedor PostgreSQL.
Es una excepción **temporal**, no una solución definitiva ni una garantía de
recuperación. La evidencia comunicada por el coordinador indica que, tras el
reinicio del VPS Ubuntu 26.04 el 23-11-2026 a las 16:36 UTC con kernel
`7.0.0-43-generic`, AppArmor denegó la señal `rtmin+1` de `gosu` hacia
`cri-containerd.apparmor.d//&unconfined`. `gosu` quedó bloqueado como PID 1,
PostgreSQL acumuló más de 270 reinicios sin logs ni socket, backend y worker
no estaban listos y `/api/health` respondió 502. El frontend nuevo estaba listo;
el fallo comenzó antes de su merge. Esta evidencia no se ha verificado de nuevo
en esta preparación. Véanse los informes de Ubuntu
[LP #2172422](https://bugs.launchpad.net/bugs/2172422) y
[LP #2172640](https://bugs.launchpad.net/bugs/2172640).

La declaración `Unconfined` pretende retirar la protección del perfil AppArmor
del contenedor y **reduce el aislamiento**; los controles restantes no ofrecen
seguridad equivalente. No garantiza eliminar restricciones AppArmor apiladas
del host. Permanecen seccomp `RuntimeDefault` a nivel pod,
`allowPrivilegeEscalation: false`, la retirada de todas las capabilities con
solo las cinco existentes añadidas, y el acceso de PostgreSQL limitado a la
red interna. No se deshabilita seccomp ni se modifica un sysctl global.

## Prueba excepcional en producción

El usuario autorizó expresamente usar la PR #63 como prueba directa en
producción, **sin ensayo aislado y con la copia OVH sin verificar**, tras
conocer la reducción del aislamiento y que revertir el YAML devuelve al
PostgreSQL previamente indisponible. No hay todavía prueba en un entorno
representativo con ese kernel y k3s; esta autorización no acredita que el
cambio funcione ni que la copia sea recuperable.

El valor observado `peer="cri-containerd.apparmor.d//&unconfined"` podría
indicar apilamiento forzado: declarar el contenedor `Unconfined` podría no
eludir una restricción AppArmor apilada del host. La lectura de `peer` por sí
sola no demuestra que el perfil efectivo esté totalmente sin restricciones.

Tras la promoción y aplicación mediante Flux, monitorizar si `gosu` avanza,
si PostgreSQL alcanza `Ready` y si desaparecen las denegaciones de señales;
comprobar también backend y worker, `/api/health` y el login. Registrar los
resultados observados sin dar por recuperado ningún componente sin comprobarlo.

Si no mejora, revertir el cambio GitOps mediante un commit y PR revisados, sin
usar `kubectl apply`. La reversión devuelve al estado previo de indisponibilidad:
**no recupera datos ni garantiza el login**. Investigar una alternativa, como
un kernel/runtime corregido o un perfil acotado, bajo aprobación independiente.
No tocar datos; las copias OVH vigentes no se han comprobado.

## Retirada y operación

Investigar y verificar primero una combinación corregida de kernel/runtime y
perfil AppArmor con el arranque real de la misma imagen y configuración, en un
entorno aislado representativo. Preparar después un cambio revisado que elimine
`appArmorProfile` del contenedor, actualice la prueba de renderizado y pase CI;
planificar y autorizar por separado la promoción y verificar el rollout y la
salud de la aplicación. Si reaparece el fallo, evaluar un cambio GitOps
revisado; no manipular la base de datos para resolver esta excepción.

Flux desde GitOps `main` es el único mecanismo de aplicación: **no usar
`kubectl apply` manual**. Este cambio preparado no está desplegado; no se puede
prometer que el login se recupere sin rollout real y comprobaciones posteriores.
No se han tocado PVC ni datos. Las copias OVH no se han verificado desde
septiembre de 2026 y su restauración no se ha ensayado; consultar
[recuperación](disaster-recovery.md) antes de cualquier operación sobre datos.

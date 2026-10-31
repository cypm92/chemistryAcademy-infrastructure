# Credenciales para la primera puesta en producción

El objetivo es publicar frontend y backend en GHCR como paquetes privados.
Kubernetes necesita una credencial de solo lectura para descargarlos. La
visibilidad debe comprobarse expresamente: un paquete vinculado a un
repositorio puede heredar su visibilidad al publicarse.

**Estado detectado el 22-09-2026:** las primeras imágenes
`chemistryacademy-frontend` y `chemistryacademy-backend` resultaron públicas.
GitHub indica que un paquete ya hecho público no puede volver a privado.
El 23-09-2026 se crearon por separado `beciencia-frontend` y
`beciencia-backend`; GitHub
confirma su visibilidad privada y la prueba de registro rechaza la descarga
anónima. Los manifiestos de Kubernetes apuntan únicamente a estos paquetes
privados.

## Preparación en GitHub

En la cuenta `cypm92`, crea un **Personal access token (classic)** desde
<https://github.com/settings/tokens/new> con el nombre `Be Ciencia VPS - GHCR
read`. Marca únicamente `read:packages`; no marques `repo`, `write:packages` ni
`delete:packages`. Elige una fecha de caducidad y anótala en tu gestor de
contraseñas: cuando caduque habrá que renovarlo antes del siguiente despliegue.
El token solo se muestra una vez al crearlo. No lo pegues en Git ni en un chat.

Después de publicar las imágenes, comprueba en GitHub que
`beciencia-frontend` y `beciencia-backend` figuran como **Private** en los
paquetes de la cuenta. Los repositorios públicos de frontend y backend tienen
acceso de escritura únicamente a su paquete correspondiente para publicar
desde `main`; GitHub advierte que los forks de esos repositorios podrían
acceder a las imágenes privadas. Ninguna credencial de producción se incluye
en las imágenes. Si alguno de los paquetes figura como público, no guardes el
token pensando que la imagen quedó protegida: revisa la visibilidad.

## Generación local del Secret cifrado

Desde PowerShell en la raíz de `chemistryAcademy-infrastructure`, con Docker
Desktop iniciado, ejecuta:

```powershell
py scripts/create-production-secrets.py
```

El programa pide en la terminal, sin mostrar lo escrito:

1. La contraseña inicial de Cresko Puyana y su confirmación (16 caracteres o
   más). El correo de esa cuenta ya está declarado como
   `cresko.puyana@gmail.com`.
2. El token clásico de GitHub con `read:packages`.

El programa genera por sí mismo la contraseña de PostgreSQL y la clave de
firma JWT. Solo escribe estos dos ficheros cifrados:

- `kubernetes/clusters/production/runtime.sops.yaml`
- `kubernetes/clusters/production/ghcr-pull.sops.yaml`

Revisa que contienen `ENC[` y una sección `sops:`. Nunca subas un Secret sin
cifrar. El script se niega a sobrescribir los ficheros existentes; la rotación
de credenciales se hará después como operación específica y comprobada.

Estos Secrets no se aplican por el mero hecho de crearlos. Se añadirán a
`clusters/production/kustomization.yaml` al activar la aplicación, después de
verificar que las imágenes existen con etiquetas `sha-<commit>`.

La clave privada age que permite descifrar los Secrets se guarda fuera del
repositorio. En el WSL de esta configuración, su ubicación local es
`$HOME/.config/beciencia/sops/age.agekey` (en esta máquina, bajo el home de
WSL). Mantén sus permisos restringidos y una copia de recuperación cifrada;
nunca la subas a Git ni la pegues en un chat. La copia de recuperación del VPS
también debe mantenerse fuera del repositorio.

El CLI de SOPS está instalado para el usuario WSL en `$HOME/.local/bin/sops`;
no requiere `sudo`. El perfil de Ubuntu añade `~/.local/bin` al `PATH` cuando
existe. El script `create-production-secrets.py` usa una imagen SOPS fijada de
Docker solo para la creación inicial; no instala el CLI ni sirve para editar
Secrets existentes.

## Verificar el acceso a las imágenes

Desde WSL, con `sops`, `python3` y `python3-yaml` disponibles, ejecuta desde la
raíz del repositorio:

```bash
set -o pipefail
SOPS_AGE_KEY_FILE="$HOME/.config/beciencia/sops/age.agekey" sops decrypt \
  kubernetes/clusters/production/ghcr-pull.sops.yaml | \
  python3 scripts/verify-ghcr-access.py
```

El Secret descifrado pasa únicamente por una tubería en memoria. El programa
comprueba que el token pertenece a `cypm92`, tiene `read:packages`, descarga
ambas etiquetas inmutables y que las imágenes no son accesibles anónimamente.
Solo imprime resultados, nunca las credenciales. Si alguna comprobación falla,
no actives la aplicación todavía.

## SMTP real

El manifiesto de producción configura el envío real y exige `SMTP_PASSWORD` en
el Secret `beciencia-runtime`. No fusiones el PR de infraestructura ni dejes
que Flux lo aplique hasta que esta clave exista cifrada: sin ella el
`notification-worker` no arrancará.

Como el Secret ya existe y `create-production-secrets.py` se niega a
sobrescribirlo, actualízalo con `sops edit` desde WSL y la raíz del repositorio:

```bash
export SOPS_AGE_KEY_FILE="$HOME/.config/beciencia/sops/age.agekey"
sops edit kubernetes/clusters/production/runtime.sops.yaml
```

En el editor local, añade `SMTP_PASSWORD` bajo `stringData` con la contraseña
de la cuenta SMTP OVH configurada como `SMTP_USERNAME`. Guarda y cierra; SOPS
vuelve a cifrar los campos protegidos. No pegues la contraseña en el chat, una
issue, un comentario de PR ni un archivo sin cifrar. Nunca edites el archivo
con un editor que no invoque SOPS ni lo muestres con `cat` o `git diff`. Añade
al PR únicamente el fichero `runtime.sops.yaml` cifrado; conserva la clave age
fuera del repositorio.

Si SOPS informa que no encuentra una identidad o no puede descifrar, no generes
otra clave ni cambies `.sops.yaml`: detente y recupera la clave age original.


Al iniciar, el worker enviará todas las notificaciones pendientes y las nuevas
a sus destinatarios guardados: los avisos administrativos a
`clases@beciencia.es` y las notificaciones de reserva/contacto a las
direcciones correspondientes. La usuaria autorizó esos envíos para la prueba
en producción. No saldrá ningún correo mientras este cambio siga en el PR sin
fusionar y aplicar por Flux.

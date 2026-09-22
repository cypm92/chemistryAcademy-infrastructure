# Credenciales para la primera puesta en producción

Los contenedores de frontend y backend se publican en GHCR como paquetes
privados. Kubernetes necesita una credencial de solo lectura para descargarlos.
GitHub crea los paquetes privados por defecto en su primera publicación.

## Preparación en GitHub

En la cuenta `cypm92`, crea un **Personal access token (classic)** desde
<https://github.com/settings/tokens/new> con el nombre `Be Ciencia VPS - GHCR
read`. Marca únicamente `read:packages`; no marques `repo`, `write:packages` ni
`delete:packages`. Elige una fecha de caducidad y anótala en tu gestor de
contraseñas: cuando caduque habrá que renovarlo antes del siguiente despliegue.
El token solo se muestra una vez al crearlo. No lo pegues en Git ni en un chat.

Después de publicar las imágenes, comprueba en GitHub que
`chemistryacademy-frontend` y `chemistryacademy-backend` figuran como
**Private** en los paquetes de la cuenta. Si alguno figura como público, no
guardes el token pensando que la imagen quedó protegida: revisa la visibilidad.

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

La clave privada age que permite descifrar los ficheros se guarda fuera del
repositorio, en el VPS y en la copia de recuperación de WSL creada en el paso
anterior. Conserva esa copia también en una copia de seguridad externa cifrada.

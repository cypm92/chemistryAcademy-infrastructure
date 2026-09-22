# Ansible: bootstrap del VPS

Este directorio contiene el endurecimiento reproducible del VPS de producción
y la instalación del clúster K3s. La aplicación se añadirá posteriormente por
GitOps, una vez se hayan publicado sus imágenes de contenedor.

## Qué aplica `playbooks/bootstrap.yml`

- actualizaciones automáticas de seguridad de Ubuntu;
- UFW: solo SSH (22), HTTP (80) y HTTPS (443) entrantes;
- Fail2ban para intentos fallidos de SSH;
- SSH solo con clave pública: se bloquean contraseña y acceso directo de `root`;
- el usuario administrativo de OVH (`ubuntu`) conserva acceso con `sudo`.

La clave SSH debe estar comprobada **antes** de ejecutar el playbook. Nunca se
guarda una clave privada, contraseña o secreto en Git.

El inventario real `inventory/production.ini` tampoco se versiona. Antes de
ejecutar Ansible, créalo a partir del ejemplo:

```bash
cp inventory/production.ini.example inventory/production.ini
```

Edita la ruta `ansible_ssh_private_key_file` para que apunte a la copia de la
clave dentro de tu directorio personal de WSL.

## Ejecutarlo desde Windows con WSL

La ejecución se hace desde WSL, no desde PowerShell nativo. Instala las
dependencias una sola vez:

```bash
sudo apt update
sudo apt install -y ansible
ansible-galaxy collection install -r requirements.yml
```

Como la clave se creó en Windows, cópiala a la carpeta SSH de WSL y limita sus
permisos. Sustituye `TU_USUARIO_WINDOWS` por tu usuario de Windows:

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cp /mnt/c/Users/TU_USUARIO_WINDOWS/.ssh/beciencia_vps_ed25519 ~/.ssh/
chmod 600 ~/.ssh/beciencia_vps_ed25519
```

Desde este directorio, primero valida sin cambiar el servidor:

```bash
ansible-playbook -i inventory/production.ini playbooks/bootstrap.yml --ask-become-pass --check --diff
```

En un VPS recién instalado, la simulación omite las reglas de UFW y los
reinicios de servicios: esos componentes aún no existen hasta la ejecución
real. El resto del playbook se valida sin modificar el servidor.

Después, para aplicar los cambios:

```bash
ansible-playbook -i inventory/production.ini playbooks/bootstrap.yml --ask-become-pass
```

Al terminar, verifica una nueva conexión desde otra terminal antes de cerrar la
sesión existente:

```bash
ssh -i ~/.ssh/beciencia_vps_ed25519 ubuntu@51.254.216.174
```

## Instalar K3s

`playbooks/k3s.yml` instala una versión fijada de K3s (Kubernetes ligero) en un
único nodo. Conserva CoreDNS, métricas y el almacenamiento local de K3s, pero
desactiva Traefik y ServiceLB: más adelante Caddy ocupará los puertos públicos
80 y 443 para servir la web y gestionar HTTPS.

El clúster usa etcd integrado, cifra los secretos de Kubernetes en reposo y
crea snapshots locales cada 12 horas. Esos snapshots no sustituyen una copia
externa, que se configurará antes de producción.

Primero valida el playbook:

```bash
ansible-playbook -i inventory/production.ini playbooks/k3s.yml --check --diff
```

Después aplícalo:

```bash
ansible-playbook -i inventory/production.ini playbooks/k3s.yml
```

Para comprobarlo desde el VPS:

```bash
ssh -i ~/.ssh/beciencia_vps_ed25519 ubuntu@51.254.216.174 \
  'kubectl get nodes && kubectl get pods -A'
```

## Instalar Flux CD

`playbooks/flux.yml` instala únicamente `source-controller` y
`kustomize-controller` de Flux. Con ello el clúster puede leer el repositorio
privado de infraestructura y aplicar los manifiestos declarados en `main`; no
instala controladores que aún no usamos (Helm, notificaciones ni automatización
de imágenes).

El playbook descarga una versión y checksum fijados de Flux, valida que la
clave de despliegue puede leer la rama `main` y guarda esa clave solo como un
Secret de Kubernetes. La clave privada no se versiona ni se registra en la
salida de Ansible.

Desde WSL, copia la clave de Flux a su directorio SSH privado una sola vez:

```bash
cp /mnt/c/Users/TU_USUARIO_WINDOWS/.ssh/beciencia_flux_deploy_ed25519 \
  /home/TU_USUARIO_WSL/.ssh/
cp /mnt/c/Users/TU_USUARIO_WINDOWS/.ssh/beciencia_flux_deploy_ed25519.pub \
  /home/TU_USUARIO_WSL/.ssh/
chmod 600 /home/TU_USUARIO_WSL/.ssh/beciencia_flux_deploy_ed25519
```

Después ejecuta el playbook indicando solo la ruta local de esa clave:

```bash
ansible-playbook -i inventory/production.ini playbooks/flux.yml \
  -e flux_deploy_key_path=/home/TU_USUARIO_WSL/.ssh/beciencia_flux_deploy_ed25519
```

Comprueba el estado desde el VPS:

```bash
K3S_CONFIG_FILE=/dev/null kubectl get pods -n flux-system
K3S_CONFIG_FILE=/dev/null flux get sources git -A
K3S_CONFIG_FILE=/dev/null flux get kustomizations -A
```

## Configurar secretos cifrados con SOPS + age

SOPS cifra los valores confidenciales antes de que lleguen a Git. `age` aporta
la identidad criptográfica: su destinatario público se puede versionar en
`.sops.yaml`, pero su clave privada **no** se sube a Git ni se comparte.
Flux recibe una copia de esa identidad como el Secret `sops-age` y la usa solo
para descifrar manifiestos declarados en el repositorio.

Este playbook genera la identidad una única vez en el VPS y guarda además una
copia de recuperación en WSL, fuera de los repositorios. Esa copia es crítica:
sin ella no se podrán descifrar secretos antiguos al recuperar o migrar el
servidor. Debe incluirse posteriormente en la copia de seguridad cifrada y
fuera del VPS.

Ejecuta desde WSL (la ruta indicada queda fuera de Git):

```bash
ansible-playbook -i inventory/production.ini playbooks/sops.yml \
  -e sops_age_backup_path=/home/TU_USUARIO_WSL/.config/beciencia/sops/age.agekey
```

El último mensaje muestra `SOPS_AGE_RECIPIENT=age1...`. Ese valor es público;
se añade a `.sops.yaml` para que los futuros secretos se puedan cifrar. Nunca
copies ni publiques el contenido de `age.agekey`.

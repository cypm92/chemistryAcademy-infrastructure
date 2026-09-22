# Ansible: bootstrap del VPS

Este directorio contiene el endurecimiento reproducible del VPS de producción.
No instala aún Kubernetes ni la aplicación: esas piezas se añadirán en pasos
posteriores, una vez tengamos el servidor base verificado.

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

Después, para aplicar los cambios:

```bash
ansible-playbook -i inventory/production.ini playbooks/bootstrap.yml --ask-become-pass
```

Al terminar, verifica una nueva conexión desde otra terminal antes de cerrar la
sesión existente:

```bash
ssh -i ~/.ssh/beciencia_vps_ed25519 ubuntu@51.254.216.174
```

# Recuperación del VPS de producción

## Alcance y estado

Be Ciencia usa actualmente el backup automático **Standard incluido** del VPS
de OVHcloud. Según [OVHcloud](https://www.ovhcloud.com/es-es/vps/options/),
se crea una copia diaria del VPS y se conserva durante 24 horas. No hay una
copia independiente de PostgreSQL ni de los archivos en otro proveedor. Los
volúmenes persistentes de K3s residen en el disco del mismo VPS.

**Última comprobación en el panel (24-09-2026):** el VPS
`vps-d7b2e60f.vps.ovh.net` mostraba Standard y un punto de restauración
creado el 23-09-2026 a las 14:26. El horario programado era 14:26 UTC.
Esto verifica que había una copia visible, **no su integridad ni una
restauración exitosa**. Debe repetirse la comprobación periódicamente.
La pérdida potencial de
datos puede acercarse a 24 horas; un error descubierto después de que se
reemplace la única copia ya no podrá deshacerse con este servicio.

## Comprobación periódica sin cambios

1. Entrar en OVHcloud Manager → Servidores privados virtuales →
   `vps-d7b2e60f.vps.ovh.net` → **Backup automatizado**.
2. Confirmar que aparece **Standard** y que la última copia figura completada.
   Registrar su fecha y hora, incluida la zona horaria que muestre el panel.
3. Si falta una copia reciente o aparece un error, investigar antes de asumir
   que los datos están protegidos. No contratar Premium ni cambiar la hora de
   copia sin una decisión expresa.

La [guía oficial de OVHcloud](https://docs.ovhcloud.com/es/guides/bare-metal-cloud/virtual-private-servers/using-automated-backups-on-a-vps)
describe las opciones de restaurar y montar. **No pulsar Restauración ni
Montaje como mera comprobación:** restaurar sobrescribe el estado actual;
montar/desmontar requiere una ventana de mantenimiento (OVH advierte que
desmontar reinicia el VPS).

## Accesos necesarios, conservados fuera del VPS

- Cuenta OVHcloud con acceso al VPS y segundo factor de autenticación.
- Acceso a los tres repositorios GitHub: frontend, backend e infraestructura.
- Clave SSH privada de administración del VPS (la copia local usada por
  Ansible); no publicar ni copiar su contenido en un ticket o en Git.
- Identidad privada SOPS/age, cuya copia de recuperación creó
  `ansible/playbooks/sops.yml` fuera del repositorio. Sin ella, los Secrets
  cifrados de Git no podrán descifrarse en un clúster nuevo.
- Clave de despliegue de Flux y acceso al paquete GHCR privado mediante un
  token `read:packages` vigente; si faltan, regenerarlos por el procedimiento
  de acceso correspondiente, nunca añadirlos en claro a Git.
- Acceso a la contraseña de administración inicial o posibilidad de rotarla.

Verificar que las copias de estas claves siguen disponibles fuera del VPS, sin
mostrar su contenido en comandos, capturas o logs. El backup Standard del
servidor no sustituye esas copias externas de recuperación.

## Si el VPS sigue disponible y se necesita volver a la última copia

1. Detener cambios y anotar el incidente, la hora y la última copia visible.
   Advertir que se perderán las reservas, usuarios y archivos posteriores a
   esa copia. Obtener autorización explícita del responsable.
2. Revisar la guía oficial enlazada arriba. En el panel, elegir la copia y
   **Restauración** solamente tras confirmar que es el VPS y punto correctos.
   No ejecutar este paso para ensayar sobre producción.
3. Esperar la confirmación de OVHcloud. Conectar por SSH y comprobar:

   ```bash
   sudo kubectl get nodes
   sudo kubectl get pods,pvc -A
   sudo kubectl get kustomizations -A
   sudo kubectl exec -n beciencia deploy/frontend -- wget -qO- http://127.0.0.1/api/health
   ```

4. Comprobar en la aplicación algunos registros y archivos conocidos,
   incluidos los creados antes de la copia. No concluir que PostgreSQL es
   íntegro solo porque el pod esté `Running`: el backup de la máquina no es
   una exportación lógica de PostgreSQL.
5. Revisar logs y reconciliación de Flux. Si la copia restauró un estado de
   GitOps antiguo, Flux puede volver a aplicar el `main` actual; evaluar esa
   diferencia antes de reabrir el servicio.

## Si el VPS se pierde por completo

Consultar primero con OVHcloud si la copia Standard existente puede
restaurarse en el mismo servicio o recuperarse mediante su procedimiento de
soporte. **No está verificada la portabilidad de esa copia a otro VPS**; no
prometer una migración automática de los datos a otra máquina. Si OVHcloud
solo ofrece restaurarla en el servicio original y ese servicio no es
recuperable, los repositorios y Ansible permiten reconstruir la aplicación,
pero no recuperar la base de datos ni los archivos.

Para reconstruir la parte reproducible en un Ubuntu nuevo: actualizar el
inventario privado de Ansible con la nueva IP y la ruta de la clave SSH,
seguir `ansible/README.md` para `bootstrap.yml`, `k3s.yml` y `flux.yml`,
reinyectar **la identidad age original** con un procedimiento revisado, y
dejar que Flux sincronice `main`. No ejecutar `sops.yml` a ciegas si crea una
identidad distinta de la usada para cifrar los Secrets. Confirmar el acceso
GHCR y, solo después, recuperar los datos por un método soportado por OVH.
Las operaciones de recuperación en un VPS nuevo pueden tener coste y requieren
autorización previa.

## Criterio para considerar probada la recuperación

Una prueba real debe restaurar una copia sin sobrescribir producción, arrancar
PostgreSQL y la aplicación, y validar registros y archivos anteriores a la
copia. Si para ello hace falta otro VPS o almacenamiento, solicitar aprobación
del coste antes de contratarlo. Hasta entonces, el estado es **última copia
visible verificada el 24-09-2026; restauración no ensayada**.

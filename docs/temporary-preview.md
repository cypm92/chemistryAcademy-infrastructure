# Acceso temporal para pruebas sin dominio

Un pod `cloudflared` abre una conexión saliente desde K3s a Cloudflare y
publica el servicio `frontend` (que a su vez sirve `/api/`) en un subdominio
aleatorio `https://…trycloudflare.com`. No abre nuevos puertos entrantes en
el VPS. Es gratuito y no necesita comprar un dominio.

**Solo para pruebas con personas de confianza.** Cloudflare indica que Quick
Tunnels no son para producción y no garantiza disponibilidad. La URL puede
cambiar si se reinicia el pod o el VPS. Cualquiera que conozca la URL puede
ver la portada, registrarse y enviar formularios públicos; no hay una
contraseña adicional. Los datos de acceso viajan por HTTPS hasta Cloudflare;
el último tramo del túnel llega por HTTP a la red interna de Kubernetes.

Para obtener la URL actual por SSH:

```bash
sudo kubectl logs -n beciencia deployment/temporary-preview-tunnel --tail=100 | grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1
```

Verificar antes de compartirla que `/`, `/api/health` y `/api/home-content`
responden y que el frontend muestra la portada. No probar reservas reales de
alumnos para un simple chequeo. El enlace se debe compartir por un canal
privado y retirar al terminar las pruebas.

Para activar el dominio de producción, la composición GitOps retirará este
Deployment al mismo tiempo que crea el ingreso Caddy. No se mantendrán los dos
accesos públicos activos simultáneamente y puede haber una interrupción hasta
que DNS resuelva al VPS y Caddy obtenga su certificado. Esto es aceptable para
la puesta en marcha inicial; no compartas enlaces temporales durante el corte.

El cambio se hace quitando `temporary-preview-tunnel.yaml` de
`kubernetes/apps/production/kustomization.yaml` en `develop`, revisando y
fusionando la PR a `main`, y esperando a que Flux reconcilie. La declaración
actualizada ya omite el túnel; no apliques manifiestos manualmente en producción.

Documentación: [Quick Tunnels de Cloudflare](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/).

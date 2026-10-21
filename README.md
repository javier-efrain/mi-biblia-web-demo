# Mi Biblia Web · Demostración técnica

Publicación aislada con datos e imágenes sintéticos. No contiene texto bíblico RVC, materiales definitivos de V15 ni los 394 archivos originales del sitio principal.

## Actualización automática — Etapa 4, Bloque 2

El flujo [demo.yml](.github/workflows/demo.yml) consulta aproximadamente cada cinco minutos la rama `desarrollo-motor-visual` de `javier-efrain/mi-biblia-web`. GitHub puede demorar las ejecuciones programadas. No necesita ejecutar ni aprobar manualmente cada actualización. También se inicia al actualizar las herramientas `.github/` de esta rama; **Run workflow** queda disponible como recuperación.

Se utiliza consulta programada porque un evento entre repositorios necesitaría una credencial adicional. No se crean tokens personales, secretos ni workflows en el repositorio principal. No se escriben commits automáticos, por lo que no hay bucles de publicación.

1. Fija un commit fuente y descarga únicamente los **27 archivos** de [.github/permitidos.json](.github/permitidos.json).
2. Incorpora el aviso permanente de demostración y valida dependencias, contenido sintético, rutas y posibles secretos.
3. Si la huella ya se publicó, termina sin desplegar de nuevo. Si cambia, ejecuta las 14 pruebas de seguridad y las pruebas Chromium de escritorio y móvil bajo la subruta de Pages.
4. Solo después de superar las pruebas publica el artefacto `_site`. README, herramientas, informes, ZIP y archivos originales quedan fuera.
5. Comprueba por HTTP que los **27 archivos servidos** coinciden mediante SHA-256 con el paquete probado. Solo entonces registra la huella como publicada. Los artefactos `revision-candidata` y el resumen de Actions identifican el commit y las pruebas.

El propietario confirmó que desactivó **Required reviewers** en el entorno `github-pages`. Se conserva la restricción de rama a `publicacion-demo`. Pages ya estaba habilitado; el flujo usa `enablement: false` y no cambia su configuración. Tampoco modifica Pages, `main` ni el dominio del repositorio principal.

Los permisos generales son de lectura; únicamente el trabajo de despliegue tiene `pages: write` e `id-token: write`. La variable `PUBLICACION_DEMO_HABILITADA` debe seguir en `true`. Cambiarla a `false` detiene futuras publicaciones. Una caché eliminada puede provocar repetir las pruebas y el despliegue; nunca evita las validaciones de un paquete nuevo.

La programación requiere que `publicacion-demo` siga siendo la rama predeterminada. GitHub puede desactivar las ejecuciones programadas por inactividad; si ocurre, reactivar el workflow desde Actions. Las actualizaciones son automáticas con cierta demora, no instantáneas al hacer push.

## Abrir la demostración

[Probar el lector visual](https://javier-efrain.github.io/mi-biblia-web-demo/motor-visual/demo.html?relato=demo-dos&modo=visual).

Conserva el diseño claro marfil/salvia, tamaño inicial 12 px y rango 8–30 px. El Bloque 2 añade paneles paginados compactos, navegación de capítulo al pie, visor integrado, gestos de dos dedos y recursos bajo demanda desde Solo texto.

Los archivos `motor-visual/` guardados en esta rama son la instantánea inicial. La web se construye desde el commit fuente más reciente, identificado en Actions; no se sincronizan mediante commits automáticos. Los informes `paquete-inicial.json` y `pruebas-iniciales.json` son evidencia histórica.

## Pruebas y reproducción local

Chromium en escritorio 1280×900 y móvil simulado 390×844; tamaños 8/12/20/30 px, selección y paginación, gestos táctiles, zoom, recursos bajo demanda y aislamiento de Solo texto. Un teléfono físico sigue pendiente.

```sh
python .github/scripts/paquete.py --actualizar --salida /tmp/mi-biblia-paquete --informe /tmp/mi-biblia-paquete.json
PAQUETE_A_PROBAR=/tmp/mi-biblia-paquete python -m unittest discover -s .github/scripts -p 'test_*.py' -v
python .github/scripts/probar_paquete.py --paquete /tmp/mi-biblia-paquete --informe /tmp/mi-biblia-pruebas.json
```

Requiere Python, Playwright y Chromium; puede indicarse `CHROMIUM_PATH`. Usar una carpeta de salida vacía. Los servidores efímeros de pruebas se cierran al finalizar. La demostración es pública y tiene `noindex`; esa directiva no la convierte en privada.

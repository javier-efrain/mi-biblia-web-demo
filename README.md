# Mi Biblia Web · Demostración técnica

Preparación aislada del motor visual, con datos e imágenes sintéticos. No contiene texto bíblico RVC, materiales definitivos de V15 ni los archivos del sitio principal.

**GitHub Pages todavía no está activado. Esta preparación no autoriza la primera publicación.**

## Qué contiene esta rama

La rama `publicacion-demo` conserva exactamente **27 archivos de ejecución** dentro de `motor-visual/`. Su lista está en [.github/permitidos.json](.github/permitidos.json). La única adaptación del motor es el aviso visible de demostración en `demo.html`; los otros 26 archivos coinciden byte por byte con el commit fuente.

Fuente inicial: [`3089fedd574ace8dd7697305c6cb582efd8279db`](https://github.com/javier-efrain/mi-biblia-web/commit/3089fedd574ace8dd7697305c6cb582efd8279db), rama `desarrollo-motor-visual` de `javier-efrain/mi-biblia-web`.

Los archivos nuevos de `.github/` y este README son herramientas e instrucciones de publicación. **No entran al sitio publicado.** El artefacto de Pages contiene solamente los 27 archivos permitidos: no se copia todo el repositorio ni todo `motor-visual/` indiscriminadamente.

Los `main` de ambos repositorios permanecen intactos. No se modifica la configuración del sitio principal, su dominio ni su origen de Pages.

## Pruebas realizadas

- Chromium 154.0.8037.57, escritorio 1280×900 y móvil simulado 390×844.
- 88 comprobaciones aprobadas: los tres relatos, ambos enfoques, imágenes completas, selección sincronizada, ocultación, páginas independientes, modal opcional, zoom, desplazamiento, tamaños 8/20/30 px y aislamiento de Solo texto.
- Gestos táctiles reales del dispositivo emulado: horizontal para paginar y vertical para desplazar sin cambiar de página.
- Las 27 rutas cargan bajo `/mi-biblia-web-demo/`, sin errores HTTP, errores JavaScript ni solicitudes externas al paquete.
- 7 pruebas de seguridad aprobadas: se rechazan archivos adicionales, RVC, recursos no sintéticos, dependencias desconocidas, ausencia del aviso y enlaces simbólicos.
- La descarga selectiva desde GitHub produjo los mismos hashes que la copia local.

Evidencia: [.github/pruebas-iniciales.json](.github/pruebas-iniciales.json) y [.github/paquete-inicial.json](.github/paquete-inicial.json). Todavía no se ha probado el despliegue real en Pages, en Actions ni en teléfonos físicos.

## Actualizaciones futuras

El flujo [demo.yml](.github/workflows/demo.yml) existe únicamente en este repositorio de demostración. No hay nuevos flujos ni secretos en el repositorio principal.

Una vez autorizado y configurado:

1. Cada hora aproximadamente, o pulsando **Actions → Demostración técnica con publicación aprobada → Run workflow**, se consulta `desarrollo-motor-visual`.
2. Se fija un commit concreto y se descargan únicamente los 27 archivos autorizados. No se clona el historial ni se descargan los 394 archivos originales.
3. Se adapta el aviso, se valida el contenido sintético y se ejecutan las pruebas. Si hay fallos o dependencias nuevas, no se publica.
4. El resumen de Actions muestra el commit fuente y la huella del paquete. Los artefactos `revision-candidata` permiten revisar el resultado.
5. Si el paquete cambió, Actions solicita la aprobación manual del entorno `github-pages`. Sin revisión obligatoria del propietario, el flujo falla antes de desplegar.
6. Después de aprobarlo con **Review deployments → github-pages → Approve and deploy**, se publica únicamente el paquete probado.

Los archivos guardados en esta rama son la instantánea inicial. Las actualizaciones posteriores se construyen desde el commit fuente y quedan identificadas en los registros de Actions; no se hacen commits automáticos en ninguno de los repositorios.

Una caché evita pedir aprobación reiteradamente por el mismo paquete publicado. Si GitHub elimina esa caché, puede volver a solicitar aprobación; nunca omite la revisión por esa causa. Las ejecuciones programadas pueden demorarse o desactivarse tras un período prolongado de inactividad; **Run workflow** permite iniciarlas manualmente.

## Configuración pendiente — solo después de confirmar la publicación

**No realizar los pasos de activación hasta que Javier confirme expresamente la primera publicación pública.** Todos estos ajustes pertenecen a `mi-biblia-web-demo`, nunca a `mi-biblia-web`.

1. En **Settings → Default branch**, establecer `publicacion-demo` como rama predeterminada. Esto hace visible el flujo manual y habilita su programación; no modifica `main`.
2. En **Settings → Actions → General**, permitir GitHub Actions y las acciones oficiales de GitHub usadas por el flujo. No hacen falta claves personales ni secretos entre repositorios.
3. En **Settings → Environments**, crear o editar `github-pages`. Activar **Required reviewers**, seleccionar **javier-efrain** y guardar. Dejar **Prevent self-review** desmarcado si el propietario también inicia las ejecuciones. Se recomienda desactivar el permiso de omitir las reglas como administrador.
4. Restringir las ramas de despliegue de ese entorno a `publicacion-demo`.
5. Después de la confirmación expresa, en **Settings → Pages → Build and deployment → Source**, elegir **GitHub Actions**. No seleccionar una rama para publicar su contenido completo ni configurar un dominio personalizado.
6. En **Settings → Secrets and variables → Actions → Variables**, crear la variable de repositorio `PUBLICACION_DEMO_HABILITADA` con valor exacto `true`. Mientras falte o no sea `true`, el flujo no intenta publicar. Esta habilitación no reemplaza la aprobación manual de cada despliegue.
7. Abrir **Actions**, ejecutar el flujo en `publicacion-demo`, revisar el commit candidato y aprobar el despliegue pendiente. Comprobar después la URL real desde computadora y celular.

El flujo no activa Pages automáticamente (`enablement: false`). Si falta la configuración de Pages o la protección del entorno, no publica. Para detener futuras publicaciones, quitar la variable de habilitación o cambiar su valor a `false`.

## Dirección prevista

Aún no habilitada:

```text
https://javier-efrain.github.io/mi-biblia-web-demo/motor-visual/demo.html?relato=demo-dos&modo=visual
```

Una vez publicada podrá abrirse directamente desde cualquier navegador, sin Codespaces ni herramientas de programación. `noindex` pide no indexarla en buscadores, pero no hace privada una página pública.

## Reproducir la verificación local

Para quien mantenga el prototipo, con Python, Chromium y Playwright instalados:

```sh
python .github/scripts/paquete.py --salida /tmp/mi-biblia-paquete --informe /tmp/mi-biblia-paquete.json
python -m unittest discover -s .github/scripts -p 'test_*.py' -v
python .github/scripts/probar_paquete.py --paquete /tmp/mi-biblia-paquete --informe /tmp/mi-biblia-pruebas.json
```

La carpeta de salida debe ser nueva o estar vacía. Con Chromium del sistema puede especificarse `CHROMIUM_PATH`. Las pruebas usan un servidor local efímero que se apaga al finalizar.

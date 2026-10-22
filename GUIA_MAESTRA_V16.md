# MI BIBLIA WEB — GUÍA MAESTRA V16
Estado: referencia de producción basada en Marcos 12:1–12. Fecha: 2026-10-22.

## 1. Fuentes de verdad y restauración
- **Respaldo congelado**: repositorio `javier-efrain/mi-biblia-web-demo`, rama `respaldo-maestro-v16-marcos-12`, commit exacto `fac7b1cc4ebf56e73f80cce17f3b99a29dea1643`.
- **Sitio de revisión**: https://javier-efrain.github.io/mi-biblia-web-demo/revision/motor-visual/desarrollo/index.html?relato=mc-12-1-12&modo=visual&enfoque=estudio
- **Repositorio de desarrollo principal**: `javier-efrain/mi-biblia-web`, rama `desarrollo-motor-visual`. NO alterar `main` ni el sitio principal.
- La rama de respaldo se mantiene inmutable. La documentación evoluciona por separado. La antigua V15 se conserva como antecedente histórico; no sustituye este respaldo.
- La revisión pública utiliza texto Reina-Valera 1909. No publicar RVC sin autorización de licencia. Nunca insertar claves de API en archivos públicos.

## 2. Archivos del estudio aprobado (en el respaldo)
Raíz: `revision/motor-visual/`.
- `desarrollo/contenido/biblia/marcos.json`: texto bíblico.
- `desarrollo/contenido/estudios/mc-12-1-12-v15.json`: estudios y reflexión; el nombre histórico v15 NO significa que la versión funcional sea V15.
- `desarrollo/contenido/catalogo.json`, `recursos.json`, `registro-v15.json`: catálogos, vínculos y registro editorial.
- `desarrollo/contenido/recursos/`: portada y dos imágenes educativas originales del relato.
- `desarrollo/index.html`, `iniciar.js`, `revision.css`: arranque de la revisión.
- `css/motor.css`, `js/componentes/`, `js/estado/`, `js/servicios/`: motor y componentes compartidos.
- La demo sintética `motor-visual/` es independiente; no modificarla al producir relatos reales.

## 3. Interfaz aprobada
- Dos enfoques: **Estudio** y **Devocional**. Dos modos: **Con recursos visuales** y **Solo texto**; cuatro combinaciones, con cambio sin salir del relato.
- Lectura continua; índice narrativo horizontal no fijo. Encabezado del relato, portada narrativa horizontal **16:9**, referencia y texto bíblico. Recursos educativos normalmente **3:4**, salvo panorámicos.
- Visor integrado siempre visible en modo visual; en solo texto, acceso discreto «Ver recurso visual» mediante modal con «Cerrar recurso». NO botón «Pantalla completa».
- Visor sin recortes de imagen, cercano al ancho disponible en móvil; zoom − / porcentaje / + / restablecer; gestos y desplazamiento. Marcadores pequeños con zona táctil cómoda. El ojo oculta **solo marcadores de la imagen**, no los botones dinámicos ni la explicación.
- Botones debajo de la imagen sincronizados con los marcadores; panel educativo único. Textos largos paginados horizontalmente con anterior/siguiente.
- Advertencias editoriales o de reconstrucción no se repiten como párrafos visibles de lectura; conservar los fundamentos en metadatos y, cuando corresponda, en información contextual accesible.
- Devocional: lectura bíblica y reflexión, sin saturación de recursos de estudio.

## 4. Reglas editoriales de cada nuevo relato
1. Analizar el pasaje y delimitar sus unidades narrativas.
2. Investigar el contexto literario, histórico, geográfico, político y cultural. Distinguir evidencia documentada, reconstrucción probable e hipótesis.
3. Redactar estudio exegético y educativo completo; añadir reflexión devocional diferenciada. Tomar el JSON del estudio aprobado como **patrón estructural exacto**, no inferir campos de memoria.
4. Seleccionar recursos **solo si enseñan algo**: portada narrativa 16:9; objetos/reconstrucciones/infografías generalmente 3:4; mapas interactivos cuando la geografía importe. Preferencia editorial actual: **infografías antes que carruseles** cuando un resumen visual aporte valor. Carruseles quedan pendientes de futuras pruebas, no son requisito.
5. Mantener imágenes sin textos incrustados cuando puedan ser HTML; metadatos separados del texto bíblico, identificadores únicos, descripciones alternativas y registro de fuentes.
6. Reutilizar el visor y componentes aprobados; no rediseñar ni duplicar el motor. Integrar con catálogos/manifiestos JSON y recursos independientes.
7. Verificar modos, botones, navegación, accesibilidad, escritorio y celular; publicar solo en revisión. Registrar commit y resultado de pruebas.

## 5. Método para nuevos chats
- Abrir un chat por relato, pero **consultar primero esta guía y el respaldo GitHub**; no confiar solo en recuerdos conversacionales.
- Comparar la estructura del estudio anterior con el nuevo antes de escribir o integrar.
- Trabajar por etapas: análisis → investigación → texto → revisión → recursos → integración → pruebas → publicación.
- Medir tiempo por etapa en Marcos 12:13–17 para evaluar el proceso de producción real.
- Correcciones menores de la web de pruebas están autorizadas, siempre que no alteren estudios aprobados, imágenes, permisos, sitio principal o arquitectura. Cambios importantes requieren decisión conjunta.

## 6. Restauración
1. Identificar el commit/árbol de la rama congelada; verificar que contiene los 27 archivos de `revision/motor-visual/` (y mantener la demo sintética separada).
2. Restaurar **solo** el conjunto de archivos correspondiente a la revisión, sin revertir indiscriminadamente el repositorio principal ni sus otras ramas.
3. Ejecutar verificaciones de integridad, seguridad y experiencia móvil/escritorio; publicar únicamente tras comprobarlas.
4. Conservar intacta la rama de respaldo; nunca escribir cambios sobre ella.

## 7. Alcance y límites
- Esta guía documenta decisiones aprobadas y rutas verificadas en GitHub; el código y JSON del respaldo son la fuente de verdad para esquemas exactos, redacción completa, estudios y activos.
- No confundir imágenes artísticas o reconstrucciones con evidencia arqueológica.
- El ZIP offline es un complemento útil pero **todavía no se declara generado ni verificado** en este documento.

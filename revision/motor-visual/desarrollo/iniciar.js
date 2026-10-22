import {crearServicioBiblia} from '../js/servicios/biblia.js';
import {crearServicioContenidos} from '../js/servicios/contenidos.js';
import {crearMotor} from '../js/estado/lectura.js';
import {leerRuta} from '../js/estado/navegacion.js';
import {crearPreferencias} from '../js/estado/preferencias.js';
import {crearControlesPreferencias} from '../js/componentes/preferencias.js';
import {nodo} from '../js/componentes/dom.js';

const root=document.querySelector('#motor');
try {
  const baseURL=new URL('contenido/',import.meta.url);
  const contenidos=crearServicioContenidos({baseURL});
  const catalogo=await contenidos.cargarCatalogo();
  const registro=await (await fetch(new URL('registro-v15.json',baseURL))).json();
  document.querySelector('#avisos').append(...registro.advertenciasHistoricas.map(texto=>nodo('p',{className:'mv-aviso'},texto)));
  const biblia=crearServicioBiblia({baseURL:new URL('biblia/',baseURL),version:'RV1909'});
  const controlesPreferencias=crearControlesPreferencias(crearPreferencias(),{compacto:true}).el;
  await crearMotor({root,catalogo,biblia,contenidos,controlesPreferencias,inicial:leerRuta(location.search,catalogo),usarHistorial:true});
  root.dataset.listo='true';
} catch(error) {
  root.textContent='No se pudo abrir la revisión local. Revisá los archivos recuperados y serví esta carpeta mediante HTTP.';
  root.setAttribute('role','alert');
}

import {crearServicioBiblia} from '../js/servicios/biblia.js';
import {crearServicioContenidos} from '../js/servicios/contenidos.js';
import {crearMotor} from '../js/estado/lectura.js';
import {leerRuta} from '../js/estado/navegacion.js';
import {crearPreferencias} from '../js/estado/preferencias.js';
import {crearControlesPreferencias} from '../js/componentes/preferencias.js';

const root=document.querySelector('#motor');
try {
  const baseURL=new URL('contenido/',import.meta.url);
  const registro=await (await fetch(new URL('registro-v15.json',baseURL))).json();
  // Los avisos históricos permanecen íntegros en los metadatos de origen.
  // Proyectar únicamente sus campos de presentación; nunca tocar párrafos educativos.
  const sinAvisos=texto=>registro.advertenciasHistoricas.reduce(
    (actual,aviso)=>actual.replaceAll(aviso,''),texto
  ).replace(/(?:\\n|\s)+$/g,'').trim();
  const presentarRecurso=recurso=>({...recurso,leyenda:sinAvisos(recurso.leyenda)});
  const servicio=crearServicioContenidos({baseURL});
  const contenidos={...servicio,
    async cargarRecurso(...args) { return presentarRecurso(await servicio.cargarRecurso(...args)); },
    async cargarVisuales(...args) {
      const datos=await servicio.cargarVisuales(...args);
      return {...datos,recursos:datos.recursos.map(presentarRecurso)};
    }
  };
  const original=await contenidos.cargarCatalogo();
  const catalogo={...original,relatos:original.relatos.map(relato=>({...relato,
    recursos:relato.recursos.map(uso=>({...uso,
      marcadores:uso.marcadores.map(m=>({...m,certezaHistorica:sinAvisos(m.certezaHistorica??'')}))
    }))
  }))};
  const biblia=crearServicioBiblia({baseURL:new URL('biblia/',baseURL),version:'RV1909'});
  const controlesPreferencias=crearControlesPreferencias(crearPreferencias(),{compacto:true}).el;
  await crearMotor({root,catalogo,biblia,contenidos,controlesPreferencias,inicial:leerRuta(location.search,catalogo),usarHistorial:true});
  root.dataset.listo='true';
} catch(error) {
  root.textContent='No se pudo abrir la revisión local. Revisá los archivos recuperados y serví esta carpeta mediante HTTP.';
  root.setAttribute('role','alert');
}

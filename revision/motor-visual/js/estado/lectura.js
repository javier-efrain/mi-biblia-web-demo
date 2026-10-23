import { nodo, mensaje, boton, abrirDialogoRecurso } from '../componentes/dom.js';
import { crearLector, claveVersiculo } from '../componentes/lector.js';
import { crearSelectorModo } from '../componentes/selector-modo.js';
import { composicionLectura } from '../componentes/selector-enfoque.js';
import { crearNavegacion, crearIndiceCapitulo, relatosDelCapitulo, leerRuta, escribirRuta } from './navegacion.js';

export async function crearMotor({ root, catalogo, biblia, contenidos, inicial, usarHistorial = false, controlesPreferencias }) {
  let estado = { relatoId:catalogo.relatos[0].id, modo:'texto', enfoque:'estudio', ...inicial };
  let generacion=0,transicion=0,carga,destruido=false,listo=Promise.resolve();
  const eventos=new AbortController(),memorias=new Map(),educadores=new Set();
  function posicionLectura() {
    const versos=[...root.querySelectorAll('[data-versiculo]')];
    const visibles=versos.filter(e=>{const r=e.getBoundingClientRect();return r.bottom>0&&r.top<innerHeight;});
    // Preferir un versículo completo: un título o el último renglón del relato
    // anterior no deben desplazar el pasaje al reaparecer una portada o contexto.
    const el=visibles.find(e=>e.getBoundingClientRect().top>=0)||visibles[0]||
      [...root.querySelectorAll('.mv-titulo-relato')].find(e=>e.getBoundingClientRect().bottom>0)||versos[0];
    return el && {versiculo:el.dataset.versiculo,relato:el.closest('[data-relato-contenido]').dataset.relatoContenido,top:el.getBoundingClientRect().top};
  }
  function restaurarPosicion(p) {
    if(!p)return;
    const relato=root.querySelector(`[data-relato-contenido="${p.relato}"]`);
    const el=p.versiculo?relato?.querySelector(`[data-versiculo="${p.versiculo}"]`):relato?.querySelector('.mv-titulo-relato');
    if(el)scrollBy(0,el.getBoundingClientRect().top-p.top);
  }
  function señalar() {
    root.dataset.relato=estado.relatoId;
    root.querySelectorAll('[data-relato-contenido]').forEach(e=>e.dataset.activo=String(e.dataset.relatoContenido===estado.relatoId));
    root.querySelectorAll('[data-relato-indice]').forEach(e=>e.setAttribute('aria-current',String(e.dataset.relatoIndice===estado.relatoId)));
  }
  function actualizarControles() {
    root.dataset.modo=estado.modo;root.dataset.enfoque=estado.enfoque;
    root.dataset.experiencia=estado.modo==='texto'?'texto':estado.enfoque;
    root.querySelectorAll('[data-experiencia]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.experiencia===root.dataset.experiencia)));
  }
  function irAlRelato(suave=true) {
    const titulo=root.querySelector(`[data-relato-contenido="${estado.relatoId}"] .mv-titulo-relato`);
    titulo?.focus({preventScroll:true});
    titulo?.scrollIntoView({block:'start',behavior:suave&&!matchMedia('(prefers-reduced-motion: reduce)').matches?'smooth':'instant'});
  }
  async function cambiarLectura(proximo,{historial=true}={}) {
    const turno=generacion,revision=++transicion;
    const vigente=()=>!destruido&&turno===generacion&&revision===transicion;
    if(estado.modo===proximo.modo&&estado.enfoque===proximo.enfoque) {
      estado={...proximo};actualizarControles();señalar();root.removeAttribute('aria-busy');
      if(usarHistorial&&historial)escribirRuta(estado);
      return;
    }
    root.setAttribute('aria-busy','true');
    let preparados=[];
    try {
      await listo;
      if(!vigente())return;
      // Preparar datos y componentes fuera del documento. Los versículos y la
      // barra permanecen montados durante toda la carga y la transición.
      const resultados=await Promise.allSettled([...educadores].map(preparar=>preparar(proximo)));
      preparados=resultados.filter(r=>r.status==='fulfilled').map(r=>r.value);
      const fallo=resultados.find(r=>r.status==='rejected');
      if(fallo)throw fallo.reason;
      if(!vigente()){preparados.forEach(p=>p.cancelar());return;}
      // Capturar después de esperar: un gesto manual durante la carga debe ganar.
      const posicion=posicionLectura();estado={...proximo};
      preparados.forEach(p=>p.aplicar());actualizarControles();señalar();
      restaurarPosicion(posicion);
      if(usarHistorial&&historial)escribirRuta(estado);
      root.querySelector('[data-error-lectura]')?.remove();
    } catch(error) {
      preparados.forEach(p=>p.cancelar());
      if(vigente()&&!root.querySelector('[data-error-lectura]')) {
        const aviso=mensaje('No fue posible cambiar el modo. Podés seguir leyendo y volver a intentarlo.');
        aviso.dataset.errorLectura='true';root.querySelector('.mv-barra-lector').append(aviso);
      }
    } finally {if(vigente())root.removeAttribute('aria-busy');}
  }
  function cambiarEnfoque(enfoque,opciones) {
    if(!['estudio','devocional'].includes(enfoque))throw new Error('Enfoque inválido.');
    return cambiarLectura({...estado,enfoque},opciones);
  }
  function abrirRecurso(relato,uso) {
    abrirDialogoRecurso({contenedor:root,signal:carga.signal,cargar:async signal=>{
      const [recurso,{crearExplorador}]=await Promise.all([contenidos.cargarRecurso(relato,uso,{signal}),import('../componentes/explorador.js')]);
      return crearExplorador(recurso,uso,{signal});
    }});
  }
  async function montarRelato(relato,signal,vigente) {
    const hook=relato.id==='mc-12-18-27'?relato.presentacion:'';
    const titulo=nodo('h2',{className:'mv-titulo-relato',tabindex:-1,id:`relato-${relato.id}`},relato.titulo);
    const referencia=nodo('p',{className:'mv-referencia'},relato.referenciaEtiqueta);
    const presentacion=relato.mostrarPresentacion&&relato.presentacion?nodo('p',{className:'mv-referencia'},relato.presentacion):null;
    const cuerpo=nodo('div',{className:'mv-cuerpo'},mensaje('Cargando texto…'));
    const articulo=nodo('article',{className:'mv-relato','data-relato-contenido':relato.id,'aria-labelledby':titulo.id},titulo,presentacion,referencia,cuerpo);
    root.querySelector('.mv-capitulo-lectura').append(articulo);
    try {
      const pasaje=await biblia.obtenerPasaje(relato.referencia);
      if(!vigente())return;
      root.querySelector('.mv-libro').textContent=pasaje.libro;
      const lector=crearLector(pasaje),antes=nodo('div',{className:'mv-antes-lectura'}),despues=nodo('div',{className:'mv-despues-lectura'});
      cuerpo.replaceChildren(antes,lector,despues);
      const accesos=[];
      for(const versiculo of lector.querySelectorAll('[data-versiculo]')) {
        const usos=relato.recursos.filter(u=>claveVersiculo({libro:u.anclajeBiblico.libro,capitulo:u.anclajeBiblico.capitulo,numero:u.anclajeBiblico.versiculo})===versiculo.dataset.versiculo);
        if(!usos.length)continue;
        const grupo=nodo('span',{className:'mv-accesos-recurso'});
        usos.forEach((uso,i)=>grupo.append(boton('🖼 Ver recurso visual',()=>abrirRecurso(relato,uso),{
          className:'mv-acceso-recurso','data-recurso-acceso':uso.id,
          'aria-label':`Ver recurso visual ${i+1} del versículo ${uso.anclajeBiblico.versiculo}`
        })));
        versiculo.after(grupo);accesos.push(grupo);
      }
      let datos,portada,educacion;
      const instancias=new Map();
      if(!memorias.has(relato.id))memorias.set(relato.id,{contexto:{},estudio:{},devocional:{}});
      const memoria=memorias.get(relato.id);
      signal.addEventListener('abort',()=>educacion?.abort(),{once:true});
      async function preparar(proximo) {
        const plan=composicionLectura(proximo.enfoque,proximo.modo);
        const local=new AbortController();
        signal.addEventListener('abort',()=>local.abort(),{once:true,signal:local.signal});
        let contexto=[],cierre=[],recursos=[];
        try {
          if(proximo.modo==='visual') {
            const [contenido,{crearLecturaHorizontal},{crearPortada},{crearExplorador}]=await Promise.all([
              datos?Promise.resolve(datos):contenidos.cargarVisuales(relato,{signal}),
              import('../componentes/lectura-horizontal.js'),import('../componentes/portada.js'),import('../componentes/explorador.js')
            ]);
            if(!vigente()){local.abort();return {aplicar(){},cancelar(){}};}
            datos=contenido;
            const biblioteca=new Map(datos.recursos.map(r=>[r.id,r]));
            portada??=crearPortada(biblioteca.get(relato.portadaId),relato.titulo,{pieVisible:false,hook});
            const opciones=(clase,etiqueta,estadoPagina)=>({clase,etiqueta,estado:estadoPagina,signal:local.signal});
            const crear=(tipos,config)=>{
              const secciones=datos.estudio.secciones.filter(s=>tipos.includes(s.tipo));
              return secciones.length?[crearLecturaHorizontal({...datos.estudio,secciones},config)]:[];
            };
            contexto=crear(plan.contexto,opciones('mv-contexto','Contexto · Antes de leer',memoria.contexto));
            cierre=crear(plan.cierre,opciones(proximo.enfoque==='estudio'?'mv-cierre':'mv-cierre mv-devocional',
              proximo.enfoque==='estudio'?'Estudio del relato':(datos.estudio.secciones.find(s=>s.tipo==='devocional')?.titulo||'Devocional'),
              proximo.enfoque==='estudio'?memoria.estudio:memoria.devocional));
            recursos=relato.recursos.map(uso=>{
              const clave=`${uso.id}:${plan.puntosInteractivos}`;
              if(!instancias.has(clave))instancias.set(clave,crearExplorador(biblioteca.get(uso.recursoId),uso,{signal,interactivo:plan.puntosInteractivos}));
              return {uso,el:instancias.get(clave)};
            });
          }
          return {cancelar:()=>local.abort(),aplicar(){
            educacion?.abort();educacion=local;
            antes.replaceChildren(...contexto);despues.replaceChildren(...cierre);
            if(plan.portada)cuerpo.insertBefore(portada,antes);else portada?.remove();
            if(presentacion)presentacion.hidden=proximo.modo==='texto'||Boolean(plan.portada&&hook);
            accesos.forEach(el=>el.hidden=!plan.accesos);
            instancias.forEach(el=>el.remove());
            for(const versiculo of lector.querySelectorAll('[data-versiculo]')) {
              let cursor=versiculo;
              for(const {uso,el} of recursos.filter(({uso})=>claveVersiculo({libro:uso.anclajeBiblico.libro,capitulo:uso.anclajeBiblico.capitulo,numero:uso.anclajeBiblico.versiculo})===versiculo.dataset.versiculo)) {
                cursor.after(el);cursor=el;
              }
            }
          }};
        } catch(error){local.abort();throw error;}
      }
      educadores.add(preparar);
      const preparado=await preparar(estado);
      if(vigente())preparado.aplicar();else preparado.cancelar();
    } catch(error) {
      if(vigente())cuerpo.replaceChildren(mensaje('No fue posible cargar el relato. Probá seleccionar otro modo.'));
    }
  }
  async function renderizar(proximo=estado,{historial=true,irAlInicio=false}={}) {
    if(destruido)return;
    proximo={...proximo,enfoque:proximo.enfoque??'estudio'};
    if(!['texto','visual'].includes(proximo.modo))throw new Error('Modo inválido.');
    if(!['estudio','devocional'].includes(proximo.enfoque))throw new Error('Enfoque inválido.');
    if(!catalogo.relatos.some(r=>r.id===proximo.relatoId))throw new Error('Relato inexistente.');
    const relatos=relatosDelCapitulo(catalogo,proximo.relatoId);
    const mismoCapitulo=relatos.some(r=>r.id===estado.relatoId)&&root.querySelector('.mv-capitulo-lectura');
    if(mismoCapitulo) {
      const cambia=estado.relatoId!==proximo.relatoId,turno=generacion;
      await cambiarLectura(proximo,{historial});await listo;
      if(!destruido&&turno===generacion&&(cambia||irAlInicio))irAlRelato();
      return;
    }
    carga?.abort();carga=new AbortController();educadores.clear();const {signal}=carga,turno=++generacion;
    const vigente=()=>!destruido&&!signal.aborted&&turno===generacion;
    estado={...proximo};
    if(usarHistorial&&historial)escribirRuta(estado);
    const seleccionar=relatoId=>renderizar({...estado,relatoId},{irAlInicio:true});
    const elegirExperiencia=opcion=>renderizar({...estado,modo:opcion==='texto'?'texto':'visual',enfoque:opcion==='texto'?estado.enfoque:opcion});
    const cabecera=nodo('header',{className:'mv-barra-lector','aria-label':'Controles del lector'},
      nodo('div',{className:'mv-selectores'},crearSelectorModo(estado.modo,elegirExperiencia,estado.enfoque)));
    if(controlesPreferencias)cabecera.append(controlesPreferencias);
    root.replaceChildren(cabecera,crearIndiceCapitulo(catalogo,estado.relatoId,seleccionar),
      nodo('div',{className:'mv-capitulo-lectura'}),crearNavegacion(catalogo,estado.relatoId,seleccionar));
    actualizarControles();señalar();
    listo=Promise.all(relatos.map(relato=>montarRelato(relato,signal,vigente)));
    await listo;
    if(vigente()&&(irAlInicio||estado.relatoId!==relatos[0].id))irAlRelato(false);
  }
  if(usarHistorial)window.addEventListener('popstate',()=>renderizar(leerRuta(location.search,catalogo),{historial:false}),{signal:eventos.signal});
  await renderizar(estado,{historial:false});
  return {
    cambiarModo:modo=>renderizar({...estado,modo}),cambiarEnfoque,
    seleccionar:relatoId=>renderizar({...estado,relatoId},{irAlInicio:true}),obtenerEstado:()=>({...estado}),
    destruir(){destruido=true;generacion++;carga?.abort();educadores.clear();eventos.abort();root.replaceChildren();}
  };
}

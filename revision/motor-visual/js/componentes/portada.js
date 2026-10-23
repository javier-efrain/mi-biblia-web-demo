import { nodo } from './dom.js';
export function crearPortada(recurso, titulo, { pieVisible = true, hook = '' } = {}) {
  const imagen = nodo('img', { src:recurso.src, alt:recurso.alt, width:1600, height:900 });
  if (recurso.dimensiones.ancho / recurso.dimensiones.alto > 1.8) imagen.style.aspectRatio = `${recurso.dimensiones.ancho}/${recurso.dimensiones.alto}`;
  const portadaConHook = Boolean(hook);
  const figura = nodo('figure', { className:portadaConHook ? 'mv-portada mv-portada-hook' : 'mv-portada', 'data-educativo':'portada' }, imagen,
    ...(portadaConHook ? [nodo('div', {className:'mv-portada-hook-texto'}, nodo('p',{className:'mv-portada-titulo-cine'}, nodo('span',{},'La resurrección'), nodo('span',{className:'mv-portada-titulo-dorado'},'y los saduceos')), nodo('span',{className:'mv-portada-filete','aria-hidden':'true'}), nodo('p',{className:'mv-portada-subtitulo-cine'},hook))] : []),
    nodo('figcaption', { className:pieVisible ? '' : 'mv-solo-lectores' }, titulo, nodo('small', {}, recurso.leyenda)));
  imagen.addEventListener('error', () => imagen.replaceWith(nodo('p', { role:'status' }, 'Portada no disponible.')));
  return figura;
}

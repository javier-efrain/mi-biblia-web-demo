import { nodo } from './dom.js';
export function crearPortada(recurso, titulo, { pieVisible = true, hook = '' } = {}) {
  const imagen = nodo('img', { src:recurso.src, alt:recurso.alt, width:1600, height:900 });
  if (recurso.dimensiones.ancho / recurso.dimensiones.alto > 1.8) imagen.style.aspectRatio = `${recurso.dimensiones.ancho}/${recurso.dimensiones.alto}`;
  const portadaConHook = Boolean(hook);
  const figura = nodo('figure', { className:portadaConHook ? 'mv-portada mv-portada-hook' : 'mv-portada', 'data-educativo':'portada' }, imagen,\n    ...(portadaConHook ? [nodo('div', {className:'mv-portada-hook-texto'}, nodo('p',{},hook))] : []),
    nodo('figcaption', { className:pieVisible ? '' : 'mv-solo-lectores' }, titulo, nodo('small', {}, recurso.leyenda)));
  imagen.addEventListener('error', () => imagen.replaceWith(nodo('p', { role:'status' }, 'Portada no disponible.')));
  return figura;
}

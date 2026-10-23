import { nodo, boton } from './dom.js';
// Tres experiencias visibles; los parámetros de URL anteriores siguen siendo compatibles.
export function crearSelectorModo(modo, cambiar, enfoque = 'estudio') {
  const actual = modo === 'texto' ? 'texto' : enfoque;
  return nodo('div', { className:'mv-modos mv-tres-modos', role:'group', 'aria-label':'Experiencia de lectura' },
    ...[['estudio','Estudio'],['devocional','Devocional'],['texto','Solo texto']].map(([valor,etiqueta]) =>
      boton(etiqueta, () => cambiar(valor), {
        'aria-label': valor === 'texto' ? 'Lectura bíblica con accesos opcionales a recursos' : 'Lectura en modo '+etiqueta,
        'aria-pressed':String(actual===valor), 'data-experiencia':valor
      })));
}

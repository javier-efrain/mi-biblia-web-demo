"""Construye exclusivamente los 27 archivos autorizados. Nunca activa Pages."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from urllib.request import urlopen
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
MANIFIESTO = REPO / '.github/permitidos.json'
AVISO = ('DEMOSTRACIÓN TÉCNICA DE MI BIBLIA WEB. Contenido sintético de prueba; '
         'no es una Biblia definitiva. No contiene texto bíblico RVC ni materiales definitivos de V15.')


def exigir(condicion, mensaje):
    if not condicion:
        raise ValueError(mensaje)


def permitidos():
    d = json.loads(MANIFIESTO.read_text())
    exigir(d['repositorioFuente'] == 'javier-efrain/mi-biblia-web' and
           d['ramaFuente'] == 'desarrollo-motor-visual', 'Fuente no autorizada')
    archivos = d['archivos']
    exigir(len(archivos) == len(set(archivos)) == 27, 'Se requiere revisar los 27 archivos permitidos')
    exigir(all(p.startswith('motor-visual/') and '..' not in PurePosixPath(p).parts and
               Path(p).suffix in {'.html', '.css', '.js', '.json', '.svg'} for p in archivos), 'Ruta no autorizada')
    return archivos


def adaptar_html(texto):
    texto, n = re.subn(r'(<p class="mv-aviso">).*?(</p>)',
                      lambda m: m[1] + AVISO + m[2], texto, count=1, flags=re.S)
    exigir(n == 1, 'Falta el aviso permanente de demostración')
    texto = texto.replace('Demostración técnica local', 'Demostración técnica')
    return texto.replace('Mi Biblia Web · Laboratorio local', 'Mi Biblia Web · Demostración técnica')


def validar(base):
    archivos = set(permitidos())
    presentes = {p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()}
    exigir(presentes == archivos, f'Paquete distinto de la lista permitida: {presentes ^ archivos}')
    exigir(not any(p.is_symlink() for p in base.rglob('*')), 'No se permiten enlaces simbólicos')
    catalogo = json.loads((base/'motor-visual/datos/catalogo.json').read_text())
    relatos = catalogo['relatos']
    exigir(len(relatos) == 3, 'Revisar los relatos sintéticos antes de ampliar el catálogo')
    exigir(all(r['demostracion'] is True and r['estadoEditorial'] == 'borrador' and
               r['referencia']['version'] == 'DEMO' and r['referencia']['libro'] == 'contenido-sintetico'
               for r in relatos), 'El catálogo debe contener solo demostraciones sintéticas')
    for r in relatos:
        for u in r['recursos']:
            exigir(u['anclajeBiblico']['version'] == 'DEMO', 'Anclaje no sintético')
        ruta = f"motor-visual/datos/estudios/{r['estudioId']}.json"
        exigir(ruta in archivos, 'Estudio fuera de la lista permitida')
        e = json.loads((base/ruta).read_text())
        exigir(e['demostracion'] is True and e['estadoEditorial'] == 'borrador' and e['relatoId'] == r['id'],
               'Estudio no sintético o ajeno')
    recursos = json.loads((base/'motor-visual/datos/recursos.json').read_text())['recursos']
    for r in recursos:
        exigir(r['demostracion'] is True and r['estadoEditorial'] == 'borrador' and
               r['autoria'] == 'Prototipo técnico Mi Biblia Web' and
               r['derechos'] == 'Recurso geométrico creado para esta demostración.', 'Recurso no autorizado')
        exigir('motor-visual/datos/'+r['src'] in archivos, 'Imagen fuera de la lista permitida')
    fuente = json.loads((base/'motor-visual/pruebas/fixtures/contenido-sintetico.json').read_text())
    exigir(fuente['version'] == 'DEMO' and fuente['demostracion'] is True and
           fuente['slug'] == 'contenido-sintetico', 'Fuente del lector no sintética')
    exigir(all(t.startswith('DEMOSTRACIÓN: línea sintética ') for cap in fuente['capitulos'].values()
               for t in cap.values()), 'El lector debe usar exclusivamente líneas sintéticas')
    inicio = (base/'motor-visual/js/iniciar.js').read_text()
    exigir("version:'DEMO'" in inicio and "../pruebas/fixtures/" in inicio, 'Origen del lector alterado')
    html = (base/'motor-visual/demo.html').read_text()
    exigir(AVISO in html and 'noindex, nofollow' in html, 'Falta el aviso público o la directiva noindex')
    for nombre in archivos:
        texto = (base/nombre).read_text()
        exigir(not re.search(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}', texto), 'Posible secreto en el paquete')
        if nombre.endswith('.js'):
            for ruta in re.findall(r'(?:from\s*|import\s*\(\s*|import\s*)[\'"]([^\'"]+)[\'"]', texto):
                resuelta = os.path.normpath(str(PurePosixPath(nombre).parent / ruta))
                exigir(ruta.startswith('.') and resuelta in archivos, f'Dependencia no autorizada: {ruta}')
        if nombre.endswith('.svg'):
            raiz = ET.fromstring(texto)
            exigir(not any(e.tag.rsplit('}',1)[-1] in {'script','foreignObject','image','use'} or
                           any(k.startswith('on') or k.rsplit('}',1)[-1] == 'href' for k in e.attrib)
                           for e in raiz.iter()), 'SVG con contenido activo o dependencias externas')
    return {nombre:hashlib.sha256((base/nombre).read_bytes()).hexdigest() for nombre in sorted(archivos)}


def construir(origen, salida):
    exigir(not salida.exists() or not any(salida.iterdir()), 'La salida debe estar vacía')
    salida.mkdir(parents=True, exist_ok=True)
    for nombre in permitidos():
        fuente = origen/nombre
        exigir(fuente.is_file() and not fuente.is_symlink(), f'Falta archivo permitido: {nombre}')
        destino = salida/nombre
        destino.parent.mkdir(parents=True, exist_ok=True)
        contenido = fuente.read_bytes()
        if nombre.endswith('/demo.html'):
            contenido = adaptar_html(contenido.decode()).encode()
        destino.write_bytes(contenido)
    return validar(salida)


def obtener_fuente(destino):
    salida = subprocess.check_output(['git','ls-remote','https://github.com/javier-efrain/mi-biblia-web.git',
                                     'refs/heads/desarrollo-motor-visual'], text=True)
    revision = salida.split()[0]
    exigir(re.fullmatch(r'[0-9a-f]{40}',revision), 'Revisión de origen inválida')
    for nombre in permitidos():
        url = f'https://raw.githubusercontent.com/javier-efrain/mi-biblia-web/{revision}/{nombre}'
        with urlopen(url, timeout=45) as respuesta:
            exigir(respuesta.geturl() == url, 'Redirección de origen no autorizada')
            contenido = respuesta.read(2_000_001)
        exigir(len(contenido) <= 2_000_000, 'Archivo inesperadamente grande')
        archivo = destino/nombre
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(contenido)
    return revision


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origen',type=Path,default=REPO)
    parser.add_argument('--salida',type=Path,required=True)
    parser.add_argument('--actualizar',action='store_true')
    parser.add_argument('--revision',default='copia-local')
    parser.add_argument('--informe',type=Path)
    args = parser.parse_args()
    revision = args.revision
    if args.actualizar:
        with tempfile.TemporaryDirectory() as temporal:
            origen = Path(temporal)
            revision = obtener_fuente(origen)
            hashes = construir(origen,args.salida)
    else:
        hashes = construir(args.origen,args.salida)
    huella = hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    informe = {'revisionFuente':revision,'archivos':len(hashes),'huella':huella,'sha256':hashes}
    if args.informe:
        args.informe.write_text(json.dumps(informe,ensure_ascii=False,indent=2)+'\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:
            f.write(f'revision={revision}\nhuella={huella}\n')
    print(json.dumps({'revisionFuente':revision,'archivos':len(hashes),'huella':huella}))


if __name__ == '__main__':
    main()

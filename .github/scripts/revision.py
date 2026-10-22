"""Incorpora la revisión editorial autorizada al paquete del repositorio demo.
Calcula una huella conjunta antes de cachear e incorpora solo rutas autorizadas.
No activa Pages ni hace push. La autorización final es obligatoria.
"""
import argparse,hashlib,json,re,shutil
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--sitio',type=Path,required=True)
parser.add_argument('--informe',type=Path,required=True)
parser.add_argument('--incorporar',action='store_true')
a=parser.parse_args()
repo=Path(__file__).resolve().parents[2]
manifiesto=json.loads((repo/'.github/revision-permitidos.json').read_text())
assert manifiesto['publicacionAprobada'] is True, 'Falta aprobación final de la revisión'
assert manifiesto['procedenciaConfirmada'] is True, 'Falta confirmar procedencia'
informe=json.loads(a.informe.read_text())
archivos=manifiesto['archivos']; hashes={}
assert archivos and len(set(archivos))==len(archivos)
for nombre in archivos:
 ruta=Path(nombre)
 assert nombre.startswith('revision/motor-visual/') and '..' not in ruta.parts
 assert ruta.suffix in {'.html','.css','.js','.json','.jpg','.png','.webp','.svg'}
 archivo=repo/ruta
 assert archivo.is_file() and not any(p.is_symlink() for p in [archivo,*archivo.parents])
 data=archivo.read_bytes()
 if ruta.suffix in {'.html','.css','.js','.json','.svg'}:
  text=data.decode()
  assert not re.search(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}',text)
 if ruta.name=='marcos.json': assert json.loads(data)['version']=='RV1909'
 hashes[nombre]=hashlib.sha256(data).hexdigest()
 assert hashes[nombre]==manifiesto['sha256'][nombre], 'Contenido distinto del inventario aprobado: '+nombre
 if a.incorporar:
  destino=a.sitio/ruta
  assert not destino.exists(), 'No reemplazar archivos de la demo'
  destino.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(archivo,destino)
informe['sha256'].update(hashes)
informe['archivos']=len(informe['sha256'])
informe['huella']=hashlib.sha256(json.dumps(informe['sha256'],sort_keys=True).encode()).hexdigest()
if a.incorporar:
 presentes={p.relative_to(a.sitio).as_posix() for p in a.sitio.rglob('*') if p.is_file()}
 assert presentes==set(informe['sha256']), 'Paquete fuera de la lista combinada'
 a.informe.write_text(json.dumps(informe,ensure_ascii=False,indent=2)+'\n')
else:
 import os
 if os.environ.get('GITHUB_OUTPUT'):
  with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('huella='+informe['huella']+'\n')
print(json.dumps({'archivos':informe['archivos'],'huella':informe['huella']}))

import json
import os
from unittest.mock import patch
from pathlib import Path
import tempfile
import unittest
from paquete import construir, validar, obtener_fuente, REPO


class PaqueteSeguro(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.paquete = Path(self.temporal.name)/'paquete'
        construir(Path(os.environ.get('PAQUETE_A_PROBAR',REPO)),self.paquete)

    def cambiar_json(self,ruta,modificar):
        p = self.paquete/ruta
        datos = json.loads(p.read_text()); modificar(datos)
        p.write_text(json.dumps(datos))

    def test_paquete_tiene_solo_27_archivos(self):
        self.assertEqual(len(validar(self.paquete)),27)

    def test_archivo_extra_impide_publicar(self):
        (self.paquete/'respaldo.zip').write_bytes(b'no autorizado')
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_lector_rvc_impide_publicar(self):
        self.cambiar_json('motor-visual/pruebas/fixtures/contenido-sintetico.json',lambda d:d.update(version='RVC'))
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_contenido_definitivo_impide_publicar(self):
        self.cambiar_json('motor-visual/datos/recursos.json',lambda d:d['recursos'][0].update(demostracion=False))
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_dependencia_nueva_impide_publicar(self):
        p=self.paquete/'motor-visual/js/iniciar.js'
        p.write_text(p.read_text()+"\nimport './no-permitido.js';\n")
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_aviso_es_obligatorio(self):
        p=self.paquete/'motor-visual/demo.html';p.write_text('<html></html>')
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_no_se_copian_enlaces(self):
        p=self.paquete/'motor-visual/css/motor.css';p.unlink();p.symlink_to('/etc/hosts')
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_estudio_definitivo_impide_publicar(self):
        self.cambiar_json('motor-visual/datos/estudios/piloto-tecnico.json',lambda d:d.update(demostracion=False))
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_catalogo_rvc_impide_publicar(self):
        self.cambiar_json('motor-visual/datos/catalogo.json',lambda d:d['relatos'][0]['referencia'].update(version='RVC'))
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_lineas_no_sinteticas_impiden_publicar(self):
        self.cambiar_json('motor-visual/pruebas/fixtures/contenido-sintetico.json',lambda d:d['capitulos']['1'].update({'1':'Texto definitivo no autorizado'}))
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_ruta_privada_impide_publicar(self):
        self.cambiar_json('motor-visual/datos/recursos.json',lambda d:d['recursos'][0].update(src='../../README.md'))
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_svg_activo_impide_publicar(self):
        p=self.paquete/'motor-visual/datos/recursos/portada-demo.svg'
        p.write_text(p.read_text().replace('</svg>','<script>ejemplo()</script></svg>'))
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_pat_sintetico_impide_publicar(self):
        p=self.paquete/'motor-visual/js/iniciar.js'
        p.write_text(p.read_text()+'\n// '+ 'ghp_' + 'a'*40)
        with self.assertRaises(ValueError): validar(self.paquete)

    def test_revision_invalida_no_descarga_contenido(self):
        with patch('paquete.subprocess.check_output',return_value='revision-invalida refs/heads/desarrollo-motor-visual'), patch('paquete.urlopen') as descargar:
            with self.assertRaises(ValueError): obtener_fuente(self.paquete)
            descargar.assert_not_called()


if __name__ == '__main__': unittest.main()

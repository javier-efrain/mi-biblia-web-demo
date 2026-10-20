import json
from pathlib import Path
import tempfile
import unittest
from paquete import construir, validar, REPO


class PaqueteSeguro(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.paquete = Path(self.temporal.name)/'paquete'
        construir(REPO,self.paquete)

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


if __name__ == '__main__': unittest.main()

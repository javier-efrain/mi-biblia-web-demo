"""Prueba únicamente el paquete publicable, bajo la subruta real de Pages."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
from paquete import validar, AVISO


class Silencioso(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass


def probar(paquete):
    hashes = validar(paquete)
    informe = {'ok':False,'archivos':len(hashes),'casos':[],'erroresJS':[],
               'fallosHTTP':[],'solicitudesNoPermitidas':[]}
    rutas = {'/mi-biblia-web-demo/'+p for p in hashes}
    solicitadas = set()
    def comprobar(condicion,descripcion):
        if not condicion: raise AssertionError(descripcion)
        informe['casos'].append(descripcion)
    with tempfile.TemporaryDirectory() as temporal:
        shutil.copytree(paquete,Path(temporal)/'mi-biblia-web-demo')
        servidor = ThreadingHTTPServer(('127.0.0.1',0),partial(Silencioso,directory=temporal))
        threading.Thread(target=servidor.serve_forever,daemon=True).start()
        origen = f'http://127.0.0.1:{servidor.server_port}'
        try:
            with sync_playwright() as p:
                ejecutable = os.environ.get('CHROMIUM_PATH')
                navegador = p.chromium.launch(executable_path=ejecutable,headless=True,args=['--no-sandbox'])
                informe['chromium'] = navegador.version
                for nombre,config in [('escritorio',{'viewport':{'width':1280,'height':900}}),
                                      ('movil',{'viewport':{'width':390,'height':844},'has_touch':True,'is_mobile':True})]:
                    contexto = navegador.new_context(**config)
                    pagina = contexto.new_page()
                    pagina.on('pageerror',lambda e:informe['erroresJS'].append(str(e)))
                    pagina.on('response',lambda r:informe['fallosHTTP'].append(r.url) if r.status>=400 else None)
                    def registrar(r):
                        if r.url.startswith('data:'): return
                        ruta = urlparse(r.url).path
                        solicitadas.add(ruta)
                        if not r.url.startswith(origen+'/') or ruta not in rutas:
                            informe['solicitudesNoPermitidas'].append(r.url)
                    pagina.on('request',registrar)
                    for relato in ['demo-uno','demo-dos','demo-tres']:
                        etiqueta = nombre+' '+relato
                        url = origen+f'/mi-biblia-web-demo/motor-visual/demo.html?relato={relato}'
                        pagina.goto(url+'&modo=visual')
                        pagina.wait_for_selector('#motor[data-listo="true"]')
                        pagina.wait_for_selector('.mv-visor img')
                        pagina.wait_for_function("[...document.querySelectorAll('img')].every(i=>i.complete&&i.naturalWidth>0)")
                        expect(pagina.locator('.mv-aviso')).to_have_text(AVISO)
                        comprobar(pagina.locator('.mv-aviso').is_visible(),etiqueta+': aviso visible y recursos completos')
                        comprobar(pagina.locator('body').evaluate('e=>e.dataset.apariencia === "oscuro"'),etiqueta+': apariencia oscura')
                        r = pagina.locator('.mv-recurso').first
                        r.locator('[data-elemento="punto-b"]').click()
                        expect(r.locator('[data-marcador="punto-b"]')).to_have_attribute('aria-pressed','true')
                        r.locator('.mv-panel nav button').last.click()
                        expect(r.locator('.mv-panel output')).to_have_text('2 / 2')
                        r.locator('[data-control="puntos"]').click()
                        comprobar(r.locator('[data-marcador]:visible,[data-elemento]:visible').count()==0,
                                  etiqueta+': puntos y botones ocultos')
                        comprobar(r.locator('img').is_visible() and r.locator('.mv-panel p').is_visible(),
                                  etiqueta+': imagen limpia con descripción')
                        pagina.get_by_role('button',name='Devocional',exact=True).click()
                        r.locator('[data-control="puntos"]').click()
                        expect(r.locator('.mv-panel output')).to_have_text('2 / 2')
                        comprobar(r.locator('[data-elemento="punto-b"]').get_attribute('aria-pressed')=='true',
                                  etiqueta+': selección y página conservadas entre enfoques')
                        rango = r.locator('input[type="range"]')
                        rango.fill('300'); rango.dispatch_event('input')
                        visor = r.locator('.mv-viewport')
                        visor.evaluate('e=>e.scrollTo(80,120)')
                        comprobar(r.evaluate('''e=>{const p=e.querySelector('.mv-plano').getBoundingClientRect(),
                            b=e.querySelector('[data-marcador="punto-b"]').getBoundingClientRect();
                            return Math.abs((b.x+b.width/2-p.x)/p.width-.75)<.01&&Math.abs((b.y+b.height/2-p.y)/p.height-.5)<.01;}'''),
                                  etiqueta+': zoom y desplazamiento mantienen puntos alineados')
                        r.get_by_role('button',name='Restablecer',exact=True).click()
                        expect(rango).to_have_value('100')
                        comprobar(r.evaluate('''e=>{const v=e.querySelector('.mv-viewport').getBoundingClientRect(),
                            p=e.querySelector('.mv-plano').getBoundingClientRect();
                            return Math.abs(v.width/v.height-.75)<.01&&Math.abs(p.width/p.height-2/3)<.01&&p.width<=v.width+1&&p.height<=v.height+1;}'''),
                                  etiqueta+': imagen 2:3 completa dentro del visor 3:4')
                        r.locator(':scope > button').click()
                        expect(r.locator('dialog')).to_be_visible()
                        r.get_by_role('button',name='Cerrar visor').click()
                        expect(r.locator('.mv-panel output')).to_have_text('2 / 2')
                        comprobar(True,etiqueta+': modal opcional preserva estado')
                        pagina.get_by_role('button',name='Restablecer tamaño de letra a 8 px',exact=True).click()
                        anterior_tamano=8
                        for tamano in [8,20,30]:
                            for _ in range((tamano-anterior_tamano)//2):
                                pagina.get_by_role('button',name='Aumentar tamaño de letra',exact=True).click()
                            anterior_tamano=tamano
                            expect(pagina.get_by_label('Tamaño de lectura',exact=True)).to_have_text(f'{tamano} px')
                            comprobar(pagina.evaluate('document.documentElement.scrollWidth<=innerWidth') and
                                      r.locator('.mv-panel .mv-hoja').evaluate('e=>e.scrollWidth<=e.clientWidth'),
                                      etiqueta+f': lectura {tamano} px sin desbordamiento')
                        pagina.get_by_role('button',name='Restablecer tamaño de letra a 8 px',exact=True).click()
                        if nombre=='movil' and relato=='demo-dos':
                            r.locator('[data-elemento="punto-a"]').click()
                            hoja = r.locator('.mv-panel .mv-hoja')
                            cdp = contexto.new_cdp_session(pagina)
                            def gesto(dx,dy):
                                hoja.scroll_into_view_if_needed()
                                caja=hoja.bounding_box();x=caja['x']+caja['width']*.75;y=max(150,min(650,caja['y']+30))
                                cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
                                for paso in range(1,7):
                                    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x+dx*paso/6,'y':y+dy*paso/6}]})
                                    pagina.wait_for_timeout(25)
                                cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
                                pagina.wait_for_timeout(250)
                            gesto(-140,2)
                            expect(r.locator('.mv-panel output')).to_have_text('2 / 2')
                            comprobar(True,etiqueta+': gesto táctil horizontal real')
                            hoja.scroll_into_view_if_needed();previo=pagina.evaluate('scrollY');gesto(2,-100)
                            expect(r.locator('.mv-panel output')).to_have_text('2 / 2')
                            comprobar(pagina.evaluate('scrollY')>previo+20,etiqueta+': gesto vertical desplaza sin paginar')
                            cdp.detach()
                        pagina.get_by_role('button',name='Estudio',exact=True).click()
                        pagina.get_by_role('button',name='Solo texto bíblico',exact=True).click()
                        comprobar(pagina.locator('[data-educativo],img').count()==0,etiqueta+': Solo texto desmonta recursos')
                        for enfoque in ['estudio','devocional']:
                            registro=[]
                            def registrar_texto(r): registro.append(r.url)
                            pagina.on('request',registrar_texto)
                            pagina.goto(url+'&modo=texto&enfoque='+enfoque)
                            pagina.wait_for_selector('#motor[data-listo="true"]')
                            comprobar(pagina.locator('[data-educativo],img').count()==0 and
                                      not any('/datos/estudios/' in u or '/datos/recursos' in u or '/componentes/explorador.js' in u for u in registro),
                                      etiqueta+': carga inicial Solo texto '+enfoque+' aislada')
                            pagina.remove_listener('request',registrar_texto)
                    contexto.close()
                navegador.close()
        finally:
            servidor.shutdown();servidor.server_close()
    comprobar(not informe['erroresJS'] and not informe['fallosHTTP'] and not informe['solicitudesNoPermitidas'],
              'Sin errores JavaScript, errores HTTP ni solicitudes fuera del paquete')
    comprobar(solicitadas==rutas,'Las 27 rutas del paquete fueron solicitadas correctamente')
    informe['ok']=True
    return informe


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--paquete',type=Path,required=True)
    parser.add_argument('--informe',type=Path,required=True)
    args=parser.parse_args()
    resultado=probar(args.paquete)
    args.informe.write_text(json.dumps(resultado,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'ok':resultado['ok'],'chromium':resultado['chromium'],'archivos':resultado['archivos'],'comprobaciones':len(resultado['casos'])}))

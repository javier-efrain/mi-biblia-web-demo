"""Prueba únicamente el paquete publicable, bajo la subruta real de Pages."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
from pathlib import Path
import shutil
import tempfile
import threading
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
from paquete import validar, AVISO


class Silencioso(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass


# Las regresiones por relato apuntan al activo sin esconder los otros relatos.
def localizar(pagina, selector):
    locales = ('.mv-cierre','.mv-contexto','.mv-devocional','.mv-recurso','.mv-viewport',
               '.mv-portada','.mv-panel','.mv-visor','.mv-hoja','.mv-texto','.mv-plano',
               '.mv-titulo-relato','[data-marcador','[data-elemento','[data-recurso-acceso',
               'input[type=range]','input[type="range"]')
    raiz = 'dialog[open]' if pagina.locator('dialog[open]').count() else '.mv-relato[data-activo=true]'
    partes = []
    for parte in selector.split(','):
        limpia = parte.strip().removeprefix('#motor ').strip()
        partes.append(raiz+' '+limpia if limpia.startswith(locales) or limpia.startswith('[data-versiculo]') else parte)
    return pagina.locator(','.join(partes))


def buscar_rol(pagina, rol, **opciones):
    if opciones.get('name') in ['Exégesis','Enseñanzas']:
        return localizar(pagina,'.mv-cierre').get_by_role(rol,**opciones)
    return pagina.get_by_role(rol,**opciones)


def esperar_selector(pagina, selector, **opciones):
    return localizar(pagina,selector).first.wait_for(state='visible',**opciones)


def probar(paquete):
    hashes = validar(paquete)
    informe = {'ok':False,'archivos':len(hashes),'casos':[],'erroresJS':[],
               'fallosHTTP':[],'solicitudesNoPermitidas':[]}
    rutas = {'/mi-biblia-web-demo/'+p for p in hashes}
    solicitadas = set()
    def comprobar(condicion,descripcion):
        if not condicion: raise AssertionError(descripcion)
        informe['casos'].append(descripcion)
    def comprobar_paginacion(bloque,etiqueta):
        hoja=bloque.locator('.mv-hoja'); nav=bloque.locator('nav'); pagina.wait_for_timeout(60)
        original=int(bloque.locator('output').inner_text().split('/')[0])
        while not nav.locator('button').first.is_disabled():nav.locator('button').first.click()
        total=int(bloque.locator('output').inner_text().split('/')[1]);altura=hoja.bounding_box()['height']
        for paso in range(total):
            comprobar(abs(hoja.bounding_box()['height']-altura)<1 and altura<=260,etiqueta+f': altura estable {paso+1}/{total}')
            if paso<total-1:nav.locator('button').last.click()
        final=hoja.evaluate('''e=>{
          const h=e.getBoundingClientRect(),w=document.createTreeWalker(e.firstChild,NodeFilter.SHOW_TEXT);let n,ultimo;
          while((n=w.nextNode())) if(n.textContent.trim()) ultimo=n;
          const fin=ultimo.textContent.trimEnd().length,r=document.createRange();r.setStart(ultimo,fin-1);r.setEnd(ultimo,fin);
          const p=r.getBoundingClientRect();return {ok:p.left>=h.left-1&&p.right<=h.right+1&&p.top>=h.top-1&&p.bottom<=h.bottom+1,hoja:h.toJSON(),letra:p.toJSON(),scroll:e.scrollLeft,ancho:e.scrollWidth,texto:ultimo.textContent};
        }''')
        comprobar(final['ok'],etiqueta+': final del texto accesible'+(' '+str(final) if not final['ok'] else ''))
        for _ in range(total-original):nav.locator('button').first.click()
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
                        esperar_selector(pagina,'#motor[data-listo="true"]')
                        esperar_selector(pagina,'.mv-visor img')
                        pagina.wait_for_function("[...document.querySelectorAll('img')].every(i=>i.complete&&i.naturalWidth>0)")
                        expect(localizar(pagina,'.mv-aviso')).to_have_text(AVISO)
                        comprobar(localizar(pagina,'.mv-aviso').is_visible(),etiqueta+': aviso visible y recursos completos')
                        comprobar(localizar(pagina,'body').evaluate('e=>e.dataset.apariencia === "claro"'),etiqueta+': apariencia editorial clara')
                        comprobar(localizar(pagina,'.mv-texto > p').first.evaluate('e=>getComputedStyle(e).fontSize')=='12px',
                                  etiqueta+': tamaño inicial de lectura a 12 px')
                        comprobar(buscar_rol(pagina,'button',name='Modo oscuro',exact=True).count()==0 and
                                  localizar(pagina,'.mv-descubrimiento').count()==0,
                                  etiqueta+': sin controles ni descubrimiento retirados')
                        comprobar(localizar(pagina,'.mv-navegacion').evaluate('e=>e===e.parentElement.lastElementChild'),etiqueta+': capítulos al final')
                        cantidad=2 if relato!='demo-tres' else 1
                        comprobar(pagina.locator('.mv-relato').count()==cantidad,etiqueta+': todos los relatos del capítulo montados')
                        comprobar(pagina.locator('.mv-texto [data-versiculo]').count()==(4 if cantidad==2 else 3),etiqueta+': capítulo completo sin versos duplicados')
                        comprobar_paginacion(localizar(pagina,'.mv-contexto'),etiqueta+' contexto')
                        comprobar_paginacion(localizar(pagina,'.mv-cierre'),etiqueta+' exégesis')
                        buscar_rol(pagina,'button',name='Enseñanzas',exact=True).click()
                        comprobar_paginacion(localizar(pagina,'.mv-cierre'),etiqueta+' enseñanzas')
                        if relato=='demo-uno':
                            pagina.evaluate('window.__capituloContinuo=[...document.querySelectorAll(".mv-relato")]')
                            for destino in ['demo-dos','demo-uno']:
                                pagina.locator(f'[data-relato-indice="{destino}"]').click()
                                expect(pagina.locator('#motor')).to_have_attribute('data-relato',destino)
                                comprobar(pagina.evaluate('window.__capituloContinuo.every((e,i)=>e===document.querySelectorAll(".mv-relato")[i])'),etiqueta+': índice conserva relatos '+destino)
                            pagina.wait_for_timeout(600)
                        r = localizar(pagina,'.mv-recurso').first
                        r.locator('[data-elemento="punto-b"]').click()
                        expect(r.locator('[data-marcador="punto-b"]')).to_have_attribute('aria-pressed','true')
                        r.locator('.mv-panel nav button').last.click()
                        expect(r.locator('.mv-panel output')).to_have_text(re.compile(r'^2 / \d+$'))
                        r.locator('[data-control="puntos"]').click()
                        comprobar(r.locator('[data-marcador]:visible,[data-elemento]:visible').count()==0,
                                  etiqueta+': puntos y botones ocultos')
                        comprobar(r.locator('img').is_visible() and r.locator('.mv-panel p').is_visible(),
                                  etiqueta+': imagen limpia con descripción')
                        buscar_rol(pagina,'button',name='Devocional',exact=True).click()
                        r.locator('[data-control="puntos"]').click()
                        expect(r.locator('.mv-panel output')).to_have_text(re.compile(r'^2 / \d+$'))
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
                        comprobar(r.get_by_role('button',name='Ampliar visor',exact=True).count()==0,etiqueta+': visor integrado sin Ampliar visor')
                        abrir=r.get_by_role('button',name='Pantalla completa',exact=True)
                        abrir.scroll_into_view_if_needed();posicion=pagina.evaluate('scrollY')
                        r.evaluate('e=>{window.__recursoCompleto=e;window.__visorCompleto=e.querySelector(".mv-visor")}')
                        abrir.click();modal=pagina.locator('dialog.mv-completa[open]');expect(modal).to_be_visible();pagina.wait_for_timeout(100)
                        comprobar(modal.evaluate('e=>e.querySelector(".mv-visor")===window.__visorCompleto'),etiqueta+': pantalla completa reutiliza la misma instancia')
                        comprobar(modal.evaluate('e=>e.clientWidth>=innerWidth-2&&e.clientHeight>=innerHeight-2'),etiqueta+': pantalla completa ocupa el navegador')
                        comprobar(modal.locator('.mv-viewport').evaluate('e=>getComputedStyle(e).aspectRatio')=='auto',etiqueta+': pantalla completa sin marco 3:4')
                        modal.get_by_role('button',name='Aumentar zoom',exact=True).click()
                        expect(modal.locator('.mv-visor output')).to_have_text('125 %')
                        comprobar(modal.locator('[data-elemento="punto-b"]').get_attribute('aria-pressed')=='true',etiqueta+': pantalla completa conserva selección')
                        pagina.keyboard.press('Escape');expect(pagina.locator('dialog')).to_have_count(0);pagina.wait_for_timeout(100)
                        comprobar(abs(pagina.evaluate('scrollY')-posicion)<2 and r.evaluate('e=>e===window.__recursoCompleto'),etiqueta+': cerrar devuelve recurso y posición')
                        expect(abrir).to_be_focused()
                        r.get_by_role('button',name='Restablecer',exact=True).click()
                        buscar_rol(pagina,'button',name='Restablecer tamaño de letra a 12 px',exact=True).click()
                        expect(pagina.get_by_label('Tamaño de lectura',exact=True)).to_have_text('12 px')
                        anterior_tamano=12
                        for tamano in [8,12,20,30]:
                            control='Aumentar tamaño de letra' if tamano>anterior_tamano else 'Reducir tamaño de letra'
                            for _ in range(abs(tamano-anterior_tamano)//2):
                                buscar_rol(pagina,'button',name=control,exact=True).click()
                            anterior_tamano=tamano
                            comprobar_paginacion(r.locator('.mv-panel .mv-estudio'),etiqueta+f' marcador {tamano}px')
                            expect(pagina.get_by_label('Tamaño de lectura',exact=True)).to_have_text(f'{tamano} px')
                            comprobar(pagina.evaluate('document.documentElement.scrollWidth<=innerWidth') and
                                      r.locator('.mv-panel .mv-hoja').evaluate('e=>e.clientHeight<=260'),
                                      etiqueta+f': lectura {tamano} px sin desbordamiento')
                        buscar_rol(pagina,'button',name='Restablecer tamaño de letra a 12 px',exact=True).click()
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
                            expect(r.locator('.mv-panel output')).to_have_text(re.compile(r'^2 / \d+$'))
                            comprobar(True,etiqueta+': gesto táctil horizontal real')
                            hoja.scroll_into_view_if_needed();previo=pagina.evaluate('scrollY');gesto(2,-100)
                            expect(r.locator('.mv-panel output')).to_have_text(re.compile(r'^2 / \d+$'))
                            comprobar(pagina.evaluate('scrollY')>previo+20,etiqueta+': gesto vertical desplaza sin paginar')
                            visor=r.locator('.mv-viewport');visor.scroll_into_view_if_needed()
                            def tocar(puntos,finales):
                                cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':puntos})
                                for paso in range(1,9):
                                    datos=[{'id':a['id'],'x':a['x']+(b['x']-a['x'])*paso/8,'y':a['y']+(b['y']-a['y'])*paso/8} for a,b in zip(puntos,finales)]
                                    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':datos});pagina.wait_for_timeout(25)
                                cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});pagina.wait_for_timeout(150)
                            def centro_visor():
                                visor.scroll_into_view_if_needed();c=visor.bounding_box();return c['x']+c['width']/2,c['y']+c['height']/2
                            x,y=centro_visor();antes=pagina.evaluate('scrollY')
                            tocar([{'id':1,'x':x,'y':y}],[{'id':1,'x':x,'y':y-100}])
                            comprobar(pagina.evaluate('scrollY')>antes+20,etiqueta+': deslizar imagen permite lectura vertical')
                            x,y=centro_visor()
                            tocar([{'id':1,'x':x-45,'y':y},{'id':2,'x':x+45,'y':y}],
                                  [{'id':1,'x':x-90,'y':y},{'id':2,'x':x+90,'y':y}])
                            comprobar(int(r.locator('.mv-visor output').inner_text().split()[0])>=180,etiqueta+': pellizco amplía la imagen')
                            comprobar(r.evaluate('''e=>{const p=e.querySelector('.mv-plano').getBoundingClientRect(),m=e.querySelector('[data-marcador="punto-b"]').getBoundingClientRect();
                              return Math.abs((m.x+m.width/2-p.x)/p.width-.75)<.01&&Math.abs((m.y+m.height/2-p.y)/p.height-.5)<.01;}'''),etiqueta+': pellizco mantiene marcadores alineados')
                            x,y=centro_visor();antes=pagina.evaluate('scrollY');pan=visor.evaluate('e=>({x:e.scrollLeft,y:e.scrollTop})')
                            tocar([{'id':1,'x':x,'y':y}],[{'id':1,'x':x-40,'y':y-60}])
                            comprobar(abs(pagina.evaluate('scrollY')-antes)<2 and visor.evaluate('e=>e.scrollLeft')>pan['x']+20 and visor.evaluate('e=>e.scrollTop')>pan['y']+30,
                                      etiqueta+': un dedo desplaza imagen ampliada en ambos ejes sin mover la página')
                            x,y=centro_visor()
                            tocar([{'id':1,'x':x-90,'y':y},{'id':2,'x':x+90,'y':y}],
                                  [{'id':1,'x':x-40,'y':y},{'id':2,'x':x+40,'y':y}])
                            comprobar(int(r.locator('.mv-visor output').inner_text().split()[0])==100,etiqueta+': pellizco reduce la imagen')
                            cdp.detach()
                        buscar_rol(pagina,'button',name='Estudio',exact=True).click()
                        buscar_rol(pagina,'button',name='Solo texto bíblico',exact=True).click()
                        comprobar(localizar(pagina,'[data-educativo],img').count()==0,etiqueta+': Solo texto desmonta recursos')
                        icono=localizar(pagina,'[data-recurso-acceso]').first;icono.scroll_into_view_if_needed();posicion=pagina.evaluate('scrollY')
                        comprobar('Ver recurso visual' in icono.inner_text() and 'Ver recurso visual' in icono.get_attribute('aria-label'),etiqueta+': acceso con texto y nombre accesible coherentes')
                        inicio=len(solicitadas)
                        icono.click();esperar_selector(pagina,'dialog .mv-visor')
                        comprobar(localizar(pagina,'.mv-recurso').count()==1 and localizar(pagina,'img').count()==1,etiqueta+': Solo texto abre un solo recurso')
                        localizar(pagina,'dialog [data-elemento="punto-b"]').click()
                        expect(localizar(pagina,'dialog [data-marcador="punto-b"]')).to_have_attribute('aria-pressed','true')
                        pagina.keyboard.press('Escape');expect(localizar(pagina,'dialog')).to_have_count(0);pagina.wait_for_timeout(60)
                        expect(icono).to_be_focused()
                        comprobar(abs(pagina.evaluate('scrollY')-posicion)<2 and localizar(pagina,'#motor').get_attribute('data-modo')=='texto',
                                  etiqueta+': cerrar conserva posición, foco y Solo texto')
                        for enfoque in ['estudio','devocional']:
                            registro=[]
                            def registrar_texto(r): registro.append(r.url)
                            pagina.on('request',registrar_texto)
                            pagina.goto(url+'&modo=texto&enfoque='+enfoque)
                            esperar_selector(pagina,'#motor[data-listo="true"]')
                            comprobar(localizar(pagina,'[data-educativo],img').count()==0 and
                                      not any('/datos/estudios/' in u or '/datos/recursos' in u or '/componentes/explorador.js' in u for u in registro),
                                      etiqueta+': carga inicial Solo texto '+enfoque+' aislada')
                            pagina.remove_listener('request',registrar_texto)
                    contexto.close()
                navegador.close()
        finally:
            servidor.shutdown();servidor.server_close()
    comprobar(not informe['erroresJS'] and not informe['fallosHTTP'] and not informe['solicitudesNoPermitidas'],
              'Sin errores JavaScript, errores HTTP ni solicitudes fuera del paquete')
    # El paquete conserva la lista estricta de 27 archivos. Descubrimiento ya no se monta.
    modulo_retirado='/mi-biblia-web-demo/motor-visual/js/componentes/descubrimiento.js'
    comprobar(solicitadas==rutas-{modulo_retirado},
              'Las 26 rutas necesarias cargan correctamente; descubrimiento no se descarga')
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

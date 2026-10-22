from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import importlib.util,json,sys,threading,tempfile
from playwright.sync_api import sync_playwright,expect
import argparse,os
parser=argparse.ArgumentParser();parser.add_argument('--sitio',type=Path,required=True);parser.add_argument('--informe',type=Path,required=True);parser.add_argument('--url');args=parser.parse_args()
SITIO=args.sitio.resolve()
checks=[]
def check(ok,name):
 assert ok,name
 checks.append(name)
def ajustar_zoom(salida, porcentaje):
    barra=salida.locator('..')
    actual=int(salida.get_attribute('data-zoom'))
    assert 100 <= int(porcentaje) <= 400 and (int(porcentaje)-actual)%25 == 0
    nombre='Aumentar zoom' if int(porcentaje)>actual else 'Reducir zoom'
    for _ in range(abs(int(porcentaje)-actual)//25):
        barra.get_by_role('button',name=nombre,exact=True).click()


class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
# Simula exactamente el prefijo de GitHub Pages.
with tempfile.TemporaryDirectory() as temp:
 raiz=Path(temp);(raiz/'mi-biblia-web-demo').symlink_to(SITIO,target_is_directory=True)
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=raiz))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),args=['--no-sandbox'])
   for device,config in [('escritorio',{'viewport':{'width':1280,'height':900}}),('movil',{'viewport':{'width':390,'height':844},'is_mobile':True,'has_touch':True})]:
    ctx=browser.new_context(**config);page=ctx.new_page();errors=[];bad=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:bad.append(r.url) if r.status>=400 else None)
    base=args.url.rstrip('/')+'/' if args.url else f'http://127.0.0.1:{server.server_port}/mi-biblia-web-demo/'
    expected=list(json.loads((SITIO/'revision/motor-visual/desarrollo/contenido/biblia/marcos.json').read_text())['capitulos']['12'].values())
    for modo in ['visual','texto']:
     for enfoque in ['estudio','devocional']:
      label=f'{device}/{modo}/{enfoque}'
      page.goto(base+f'revision/motor-visual/desarrollo/index.html?relato=mc-12-1-12&modo={modo}&enfoque={enfoque}')
      page.wait_for_selector('#motor[data-listo=true]')
      verses=page.locator('.mv-texto > p').evaluate_all('es=>es.map(e=>[...e.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join("").trim())')
      check(verses==expected,label+' 12 versículos RV1909 completos')
      check(page.locator('.mv-portada').count()==(1 if modo=='visual' else 0),label+' portada')
      check(page.locator('.mv-recurso').count()==(2 if modo=='visual' and enfoque=='estudio' else 0),label+' recursos según composición')
      check(page.locator('.mv-contexto').count()==(1 if enfoque=='estudio' else 0),label+' contexto')
      check(page.locator('.mv-devocional').count()==(1 if enfoque=='devocional' else 0),label+' devocional')
      if modo=='texto':
       page.locator('[data-recurso-acceso]').last.click();page.wait_for_selector('dialog .mv-visor')
       check(page.locator('dialog img').count()==1,label+' modal opcional')
       page.keyboard.press('Escape');expect(page.locator('dialog')).to_have_count(0)
      else:
       if enfoque=='estudio':
        page.locator('[data-elemento="vina-1"]').click()
        check(page.locator('[data-marcador="vina-1"]').get_attribute('aria-pressed')=='true',label+' selección sincronizada')
        recurso=page.locator('.mv-recurso').first
        barra=recurso.locator('.mv-herramientas')
        check(barra.locator('button').count()==4 and barra.locator('input').count()==0,label+' barra compacta sin deslizador')
        check(recurso.locator('[data-elemento]').first.get_attribute('aria-pressed')=='true',label+' primer elemento seleccionado')
        check(recurso.locator('.mv-panel h4').inner_text()=='La viña',label+' explicación inicial')
        check(recurso.locator('.mv-visor > small').count()==0 and not recurso.locator('.mv-ficha-recurso').get_attribute('open'),label+' sin descripción general permanente')
        # Esperar fuentes y dos cuadros: el paginador mide sus columnas tras montar.
        page.evaluate('async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}')
        pagina_explicativa=recurso.locator('.mv-panel output').inner_text()
        panel_original=recurso.locator('.mv-panel').element_handle()
        barra.get_by_role('button',name='Ocultar puntos',exact=True).click()
        check(recurso.locator('.mv-panel').is_visible() and recurso.locator('.mv-elementos').is_visible() and recurso.locator('[data-marcador]:visible').count()==0,label+' solo marcadores ocultos')
        ultimo=recurso.locator('[data-elemento]').last
        ultimo.click();actual=ultimo.get_attribute('data-elemento')
        expect(recurso.locator(f'[data-marcador="{actual}"]')).to_have_attribute('aria-pressed','true')
        check(recurso.locator('.mv-panel h4').inner_text()==ultimo.inner_text() and recurso.locator('[data-marcador]:visible').count()==0,label+' botones cambian explicación con puntos ocultos')
        page.evaluate('async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}')
        pagina_explicativa=recurso.locator('.mv-panel output').inner_text()
        barra.get_by_role('button',name='Mostrar puntos',exact=True).click()
        expect(recurso.locator('.mv-panel output')).to_have_text(pagina_explicativa)
        check(recurso.locator('.mv-panel').evaluate('(e,original)=>e===original',panel_original) and recurso.locator('[data-elemento][aria-pressed=true]').get_attribute('data-elemento')==actual,label+' selección actual, panel y página restaurados')
        slider=recurso.locator('[data-zoom]');ajustar_zoom(slider,250)
        check(slider.get_attribute('data-zoom')=='250',label+' zoom')
      check(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),label+' sin desbordamiento')
    # Comprueba que el mismo sitio sigue sirviendo la demo sintética independiente.
    page.goto(base+'motor-visual/demo.html?relato=demo-dos&modo=visual')
    page.wait_for_selector('.mv-relato')
    check('Los labradores malvados' not in page.locator('body').inner_text(),device+' demo sintética separada')
    check(not errors and not bad,device+' sin errores JS ni HTTP')
    ctx.close()
   browser.close()
 finally:server.shutdown();server.server_close()
args.informe.write_text(json.dumps({'ok':True,'urlPublica':args.url,'comprobaciones':len(checks),'casos':checks},ensure_ascii=False,indent=2)+'\n')
print('Rutas Pages y cuatro modos:',len(checks),'comprobaciones correctas.')

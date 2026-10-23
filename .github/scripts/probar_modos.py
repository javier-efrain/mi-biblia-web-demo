"""Tres experiencias, enlaces heredados y transiciones sin desmontar la lectura."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import argparse,json,os,tempfile,threading
from playwright.sync_api import sync_playwright,expect
p=argparse.ArgumentParser();p.add_argument('--sitio',type=Path,required=True);p.add_argument('--informe',type=Path,required=True);p.add_argument('--url');args=p.parse_args()
checks=[];desplazamientos=[]
def check(ok,label):
 assert ok,label
 checks.append(label)
def esperar(page):
 page.wait_for_function('!document.querySelector("#motor").hasAttribute("aria-busy")')
 page.evaluate('async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}')
 page.wait_for_timeout(100)
def elegir(page,modo):
 page.locator(f'button[data-experiencia="{modo}"]').evaluate('(e)=>e.click()')
 expect(page.locator('#motor')).to_have_attribute('data-experiencia',modo);esperar(page)
def comprobar(page,modo,label):
 check(page.locator('button[data-experiencia]').all_text_contents()==['Estudio','Devocional','Solo texto'],label+' solo tres botones')
 check(page.locator('button[data-experiencia][aria-pressed=true]').count()==1 and page.locator('button[data-experiencia][aria-pressed=true]').get_attribute('data-experiencia')==modo,label+' indicador activo sincronizado')
 check(page.locator('.mv-texto > p').count()==27,label+' 27 versículos sin duplicados')
 check(page.locator('[data-relato-indice]').count()==3,label+' tres relatos en índice')
 check(page.locator('.mv-portada').count()==(0 if modo=='texto' else 3),label+' portadas según experiencia')
 check(page.locator('.mv-contexto').count()==(3 if modo=='estudio' else 0),label+' contexto según experiencia')
 check(page.locator('.mv-devocional').count()==(3 if modo=='devocional' else 0),label+' reflexiones según experiencia')
 check(page.locator('.mv-recurso').count()==(0 if modo=='texto' else 6),label+' recursos según experiencia')
 if modo=='devocional':
  check(page.locator('[data-marcador],.mv-panel,.mv-elementos,[data-control=puntos]').count()==0,label+' imágenes sin controles de elementos ni paneles montados')
 if modo=='texto':
  check(page.locator('.mv-estudio,.mv-recurso,.mv-portada,main img').count()==0,label+' lectura bíblica sin contenidos educativos ni imágenes montadas')
  check(page.locator('[data-recurso-acceso]:visible').count()==6,label+' seis accesos opcionales')
 check(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),label+' sin desbordamiento')
 check(page.locator('[data-error-lectura]').count()==0,label+' transición sin errores')
class H(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
with tempfile.TemporaryDirectory() as temp:
 raiz=Path(temp);(raiz/'mi-biblia-web-demo').symlink_to(args.sitio.resolve(),target_is_directory=True)
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(H,directory=raiz));threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),args=['--no-sandbox'])
   for ancho in [1280,390,393]:
    ctx=browser.new_context(viewport={'width':ancho,'height':844},is_mobile=ancho<500,has_touch=ancho<500)
    page=ctx.new_page();errores=[];solicitudes=[];fallos=[]
    page.on('pageerror',lambda e:errores.append(str(e)));page.on('request',lambda r:solicitudes.append(r.url));page.on('response',lambda r:fallos.append(r.url) if r.status>=400 else None)
    base=(args.url.rstrip('/')+'/' if args.url else f'http://127.0.0.1:{server.server_port}/mi-biblia-web-demo/')+'revision/motor-visual/desarrollo/index.html'
    # Los cuatro formatos de enlaces anteriores convergen en tres experiencias.
    for modo,enfoque,experiencia in [('visual','estudio','estudio'),('visual','devocional','devocional'),('texto','estudio','texto'),('texto','devocional','texto')]:
     solicitudes.clear();page.goto(base+f'?relato=mc-12-18-27&modo={modo}&enfoque={enfoque}');page.wait_for_selector('#motor[data-listo=true]');esperar(page)
     comprobar(page,experiencia,f'{ancho}/enlace-{modo}-{enfoque}')
     if modo=='texto':check(not any('/contenido/estudios/' in u or '/contenido/recursos' in u for u in solicitudes),f'{ancho} texto no carga estudios ni recursos antes de pedirlos')
    # Cambios profundos: no usar click() de Playwright, que primero desplazaría
    # deliberadamente la página hacia la barra superior fuera de pantalla.
    elegir(page,'estudio')
    visor=page.locator('[data-uso="mc-12-19-levirato"]');visor.locator('[data-elemento]').last.click()
    seleccionado=visor.locator('[data-elemento][aria-pressed=true]').get_attribute('data-elemento')
    visor.get_by_role('button',name='Aumentar zoom',exact=True).click();instancia=visor.element_handle()
    verso=page.locator('[data-versiculo="marcos:12:14"]');original=verso.element_handle()
    verso.evaluate('(e)=>scrollTo(0,e.getBoundingClientRect().top+scrollY-8)');esperar(page)
    # El versículo observado es el primero completo en pantalla, también con
    # las fuentes del servidor CI; los accesos pueden refluir otros párrafos.
    for experiencia in ['devocional','texto','estudio','texto','devocional','estudio']:
     page.evaluate('''()=>{window.muestras=[];window.midiendo=true;function medir(){muestras.push(document.querySelector('[data-versiculo="marcos:12:14"]').getBoundingClientRect().top);if(midiendo)requestAnimationFrame(medir)}medir()}''')
     elegir(page,experiencia);page.wait_for_timeout(120)
     muestras=page.evaluate('()=>{midiendo=false;return muestras}')
     delta=max(muestras)-min(muestras);desplazamientos.append({'ancho':ancho,'experiencia':experiencia,'variacionPx':delta})
     check(delta<=3,f'{ancho}/{experiencia} conserva posición sin cuadros de salto (variación {delta:.2f}px)')
     check(verso.evaluate('(e,original)=>e===original',original),f'{ancho}/{experiencia} conserva el mismo nodo bíblico')
     comprobar(page,experiencia,f'{ancho}/boton-{experiencia}')
    check(page.locator('[data-uso="mc-12-19-levirato"]').evaluate('(e,original)=>e===original',instancia),f'{ancho} reutiliza visor de estudio')
    expect(page.locator('[data-uso="mc-12-19-levirato"] [data-zoom]')).to_have_attribute('data-zoom','125')
    check(page.locator('[data-uso="mc-12-19-levirato"] [data-elemento][aria-pressed=true]').get_attribute('data-elemento')==seleccionado,f'{ancho} conserva selección y zoom al volver a Estudio')
    # Historial y enlaces conservan modo/enfoque; la experiencia visible es única.
    elegir(page,'devocional');elegir(page,'texto');page.go_back();expect(page.locator('#motor')).to_have_attribute('data-experiencia','devocional');esperar(page)
    page.go_forward();expect(page.locator('#motor')).to_have_attribute('data-experiencia','texto');esperar(page)
    check('modo=texto' in page.url and 'enfoque=devocional' in page.url,f'{ancho} historial y parámetros heredados')
    # La carga lenta no debe devolver al lector al punto anterior a su gesto.
    page.goto(base+'?relato=mc-12-1-12&modo=texto&enfoque=estudio');page.wait_for_selector('#motor[data-listo=true]');esperar(page)
    cdp=ctx.new_cdp_session(page);cdp.send('Network.enable');cdp.send('Network.setCacheDisabled',{'cacheDisabled':True});cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':350,'downloadThroughput':-1,'uploadThroughput':-1})
    verso=page.locator('[data-versiculo="marcos:12:5"]');verso.evaluate('(e)=>scrollTo(0,e.getBoundingClientRect().top+scrollY-80)')
    page.locator('button[data-experiencia="estudio"]').evaluate('(e)=>e.click()');page.wait_for_function('document.querySelector("#motor").hasAttribute("aria-busy")')
    page.mouse.wheel(0,60);page.wait_for_timeout(120);antes=verso.bounding_box()['y']
    check(0<=antes<=30,f'{ancho} gesto manual mueve el pasaje observado sin llegar al final del documento')
    expect(page.locator('#motor')).to_have_attribute('data-experiencia','estudio');esperar(page)
    check(abs(verso.bounding_box()['y']-antes)<=3,f'{ancho} respeta scroll manual realizado durante la carga: {antes:.2f} → {verso.bounding_box()["y"]:.2f}px')
    cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1});cdp.detach()
    elegir(page,'texto')
    page.evaluate('''()=>{for(const m of ['estudio','devocional','texto'])document.querySelector(`button[data-experiencia="${m}"]`).click()}''');esperar(page);page.wait_for_timeout(200)
    comprobar(page,'texto',f'{ancho}/pulsaciones-rapidas')
    check(not errores and not fallos,f'{ancho} sin errores JavaScript ni HTTP: {errores} {fallos}')
    ctx.close()
   browser.close()
 finally:server.shutdown();server.server_close()
args.informe.write_text(json.dumps({'ok':True,'comprobaciones':len(checks),'casos':checks,'desplazamientos':desplazamientos},ensure_ascii=False,indent=2)+'\n')
print('Tres experiencias de lectura:',len(checks),'comprobaciones correctas.')

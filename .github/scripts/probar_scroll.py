"""Regresión de scroll con gestos táctiles y barra móvil emulada por CDP.
La diferencia svh/lvh permanece en 64 px al ocultar la barra: no se confunde
un cambio de interfaz del navegador con cambiar el tamaño físico del teléfono.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import argparse,json,os,tempfile,threading
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--sitio',type=Path,required=True);p.add_argument('--informe',type=Path,required=True);p.add_argument('--url');args=p.parse_args()
checks=[];mediciones=[]
def check(ok,label):
 if not ok:raise AssertionError(label)
 checks.append(label)
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
def esperar(page):
 page.evaluate('async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}')
 page.wait_for_timeout(150)
def estado(page):
 return page.evaluate('''()=>({y:scrollY,alto:document.documentElement.scrollHeight,
  cajas:[...document.querySelectorAll('.mv-hoja')].map(e=>e.getBoundingClientRect().height),
  paginas:[...document.querySelectorAll('.mv-estudio output')].map(e=>e.textContent),
  llamadas:window.movimientos.splice(0)})''')
with tempfile.TemporaryDirectory() as temp:
 raiz=Path(temp);(raiz/'mi-biblia-web-demo').symlink_to(args.sitio.resolve(),target_is_directory=True)
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=raiz));threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),args=['--no-sandbox'])
   for ancho in [390,393,1280]:
    ctx=browser.new_context(viewport={'width':ancho,'height':780},is_mobile=ancho<500,has_touch=ancho<500)
    page=ctx.new_page();cdp=ctx.new_cdp_session(page)
    page.add_init_script('''window.movimientos=[];
      for(const n of ['scrollTo','scrollBy']){const f=window[n];window[n]=function(...a){movimientos.push([n,...a]);return f.apply(this,a)}}
      const f=Element.prototype.scrollIntoView;Element.prototype.scrollIntoView=function(...a){movimientos.push(['scrollIntoView',this.className]);return f.apply(this,a)};''')
    base=args.url.rstrip('/')+'/' if args.url else f'http://127.0.0.1:{server.server_port}/mi-biblia-web-demo/'
    for modo in ['visual','texto']:
     for enfoque in ['estudio','devocional']:
      label=f'{ancho}/{modo}/{enfoque}'
      page.goto(base+f'revision/motor-visual/desarrollo/index.html?relato=mc-12-18-27&modo={modo}&enfoque={enfoque}')
      page.wait_for_selector('#motor[data-listo=true]');esperar(page)
      if ancho<500:
       superficies=['versiculo','imagen'] if modo=='visual' else ['versiculo']
       if page.locator('.mv-portada-hook-texto').count():superficies.append('hook')
       for superficie in superficies:
        page.set_viewport_size({'width':ancho,'height':780})
        cdp.send('Emulation.setSmallViewportHeightDifferenceOverride',{'difference':0});esperar(page)
        selector='[data-versiculo="marcos:12:14"]' if superficie=='versiculo' else '[data-relato-contenido="mc-12-13-17"] .mv-portada img'
        if superficie=='hook':selector='[data-relato-contenido="mc-12-18-27"] .mv-portada-hook-texto'
        page.locator(selector).evaluate('(e)=>scrollTo(0,e.getBoundingClientRect().top+scrollY-180)');esperar(page)
        # Desplazamiento táctil nativo, sin inercia posterior ni scroll JS.
        page.evaluate('''()=>{movimientos=[];window.trayectoria=[scrollY];window.midiendo=true;function tomar(){trayectoria.push(scrollY);if(midiendo)requestAnimationFrame(tomar)}requestAnimationFrame(tomar)}''')
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':ancho//2,'y':210}]})
        for paso in range(1,11):
         cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':ancho//2,'y':210-paso*10}]})
         page.wait_for_timeout(30)
        page.wait_for_timeout(150)
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        esperar(page)
        recorrido=page.evaluate('()=>{midiendo=false;return trayectoria}')
        mediciones.append({'gesto':label+'/'+superficie,'recorrido':recorrido})
        check(recorrido[-1]>recorrido[0]+40 and all(b>=a-1 for a,b in zip(recorrido,recorrido[1:])),label+'/'+superficie+' gesto vertical continuo sin retroceso')
        inicial=estado(page);check(not inicial['llamadas'],label+' sin scroll JS durante gesto')
        for alto in [844,780,844,780]:
         page.set_viewport_size({'width':ancho,'height':alto})
         cdp.send('Emulation.setSmallViewportHeightDifferenceOverride',{'difference':alto-780});esperar(page)
         actual=estado(page);mediciones.append({'caso':label+'/'+superficie,'ventana':alto,'antes':inicial,'despues':actual})
         check(actual['cajas']==inicial['cajas'] and actual['alto']==inicial['alto'],label+' cajas y documento estables al cambiar barra')
         check(abs(actual['y']-inicial['y'])<=1,label+' sin corrección automática de posición')
         check(actual['paginas']==inicial['paginas'] and not actual['llamadas'],label+' sin repaginación ni scroll JS por barra')
      else:
       page.locator('[data-versiculo="marcos:12:14"]').evaluate('(e)=>scrollTo(0,e.getBoundingClientRect().top+scrollY-200)');esperar(page);estado(page)
       y=page.evaluate('scrollY');page.mouse.wheel(0,120);esperar(page);actual=estado(page)
       check(actual['y']>y and not actual['llamadas'],label+' scroll de escritorio nativo')
      # Paginación explícita: sigue funcionando sin mover el documento al medir.
      if modo=='texto':continue
      caja=page.locator('[data-relato-contenido="mc-12-18-27"] .mv-contexto' if enfoque=='estudio' else '[data-relato-contenido="mc-12-18-27"] .mv-devocional')
      caja.scroll_into_view_if_needed();esperar(page)
      siguiente=caja.get_by_role('button',name='Siguiente →',exact=True)
      if siguiente.is_enabled():
       antes=caja.locator('output').inner_text();siguiente.click();esperar(page)
       check(caja.locator('output').inner_text()!=antes,label+' Siguiente conserva paginación')
       caja.get_by_role('button',name='← Anterior',exact=True).click();esperar(page)
       check(caja.locator('output').inner_text()==antes,label+' Anterior conserva paginación')
    ctx.close()
   browser.close()
 finally:
  server.shutdown();server.server_close()
  args.informe.write_text(json.dumps({'comprobaciones':len(checks),'casos':checks,'mediciones':mediciones},ensure_ascii=False,indent=2)+'\n')
print('Scroll estable:',len(checks),'comprobaciones correctas.')

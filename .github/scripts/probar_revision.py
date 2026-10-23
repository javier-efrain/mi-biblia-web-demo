"""Regresión del catálogo editorial completo, también contra la URL de Pages."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import argparse,json,os,tempfile,threading
from playwright.sync_api import sync_playwright,expect
p=argparse.ArgumentParser();p.add_argument('--sitio',type=Path,required=True);p.add_argument('--informe',type=Path,required=True);p.add_argument('--url');args=p.parse_args()
sitio=args.sitio.resolve();contenido=sitio/'revision/motor-visual/desarrollo/contenido'
catalogo=json.loads((contenido/'catalogo.json').read_text());libro=json.loads((contenido/'biblia/marcos.json').read_text())
checks=[]
registro=json.loads((contenido/'registro-v15.json').read_text())
avisos=[registro['avisoEditorial'],*registro['advertenciasHistoricas']]
def check(ok,label):
 assert ok,label
 checks.append(label)
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
with tempfile.TemporaryDirectory() as temp:
 raiz=Path(temp);(raiz/'mi-biblia-web-demo').symlink_to(sitio,target_is_directory=True)
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=raiz));threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),args=['--no-sandbox'])
   for ancho in [1280,390,393]:
    ctx=browser.new_context(viewport={'width':ancho,'height':900 if ancho==1280 else 844},is_mobile=ancho<500,has_touch=ancho<500)
    page=ctx.new_page();errores=[];fallos=[]
    page.on('pageerror',lambda e:errores.append(str(e)));page.on('response',lambda r:fallos.append(r.url) if r.status>=400 else None)
    base=args.url.rstrip('/')+'/' if args.url else f'http://127.0.0.1:{server.server_port}/mi-biblia-web-demo/'
    for modo in ['visual','texto']:
     for enfoque in ['estudio','devocional']:
      label=f'{ancho}/{modo}/{enfoque}'
      page.goto(base+f'revision/motor-visual/desarrollo/index.html?relato=mc-12-18-27&modo={modo}&enfoque={enfoque}')
      page.wait_for_selector('#motor[data-listo=true]')
      check(page.locator('[data-relato-indice]').count()==len(catalogo['relatos'])==3,label+' tres relatos en índice')
      check(page.locator('.mv-texto > p').count()==27,label+' lectura continua con 27 versículos')
      check('no disponibles' not in page.locator('body').inner_text() and 'No fue posible' not in page.locator('body').inner_text(),label+' sin errores de contenido')
      check(all(a not in page.locator('body').inner_text() for a in avisos),label+' avisos antiguos permanecen fuera de lectura')
      for relato in catalogo['relatos']:
       rid=relato['id'];art=page.locator(f'[data-relato-contenido="{rid}"]');ref=relato['referencia']['rangos'][0]
       nums=list(range(ref['desde'],ref['hasta']+1));versos=art.locator('.mv-texto > p').all()
       check(len(versos)==len(nums) and all(v.get_attribute('data-versiculo')==f'marcos:12:{n}' and libro['capitulos']['12'][str(n)] in v.inner_text() for n,v in zip(nums,versos)),label+' '+rid+' texto completo y ordenado')
       check(art.locator('.mv-portada').count()==int(modo=='visual'),label+' '+rid+' portada según modo')
       check(art.locator('.mv-contexto').count()==int(enfoque=='estudio'),label+' '+rid+' contexto según enfoque')
       check(art.locator('.mv-devocional').count()==int(enfoque=='devocional'),label+' '+rid+' devocional según enfoque')
       check(art.locator('.mv-recurso').count()==(len(relato['recursos']) if modo=='visual' and enfoque=='estudio' else 0),label+' '+rid+' recursos según enfoque')
       check(art.locator('[data-recurso-acceso]').count()==(len(relato['recursos']) if modo=='texto' else 0),label+' '+rid+' accesos opcionales')
       if modo=='visual':
        expect(art.locator('.mv-portada img')).to_have_js_property('complete',True)
        check(art.locator('.mv-portada img').evaluate('(e)=>e.naturalWidth>0'),label+' '+rid+' portada cargada')
        if rid!='mc-12-18-27':
         check(art.locator('.mv-portada-hook-texto').count()==0 and art.locator('.mv-portada img').evaluate('(e)=>Math.abs(e.clientWidth/e.clientHeight-16/9)<.02 && getComputedStyle(e).objectFit==="contain"'),label+' '+rid+' portada anterior conservada')
       for uso in relato['recursos']:
        if modo=='visual' and enfoque=='devocional':continue
        modal=modo=='texto'
        if modal:
         acceso=art.locator(f'[data-recurso-acceso="{uso["id"]}"]');acceso.click();page.wait_for_selector('dialog .mv-visor');host=page.locator('dialog')
        else:host=art.locator(f'[data-uso="{uso["id"]}"]')
        imagen=host.locator('.mv-visor img');expect(imagen).to_have_js_property('complete',True)
        check(imagen.evaluate('(e)=>e.naturalWidth>0 && e.naturalHeight>0'),label+' '+uso['id']+' imagen cargada')
        ficha=host.locator('.mv-ficha-recurso');ficha.locator('summary').click()
        check(all(a not in ficha.inner_text() for a in avisos),label+' ficha sin avisos retirados')
        ficha.locator('summary').click()
        if not modal:
         check(host.evaluate('(e)=>e.previousElementSibling.dataset.versiculo')==f'marcos:12:{uso["anclajeBiblico"]["versiculo"]}',label+' '+uso['id']+' anclaje correcto')
        check(host.locator('[data-elemento][aria-pressed=true]').get_attribute('data-elemento')==uso['marcadores'][0]['id'],label+' '+uso['id']+' selección inicial')
        for marcador in uso['marcadores']:
         mid=marcador['id'];boton=host.locator(f'[data-elemento="{mid}"]');boton.click()
         expect(host.locator(f'[data-marcador="{mid}"]')).to_have_attribute('aria-pressed','true')
         check(host.locator('.mv-panel h4').inner_text()==marcador['titulo'],label+' '+mid+' botón, marcador y explicación sincronizados')
        ojo=host.get_by_role('button',name='Ocultar puntos',exact=True);ojo.click()
        check(host.locator('[data-marcador]:visible').count()==0 and host.locator('.mv-panel').is_visible() and host.locator('.mv-elementos').is_visible(),label+' '+uso['id']+' ojo oculta solo puntos')
        host.locator('[data-elemento]').first.click();expect(host.locator('.mv-panel h4')).to_have_text(uso['marcadores'][0]['titulo'])
        host.get_by_role('button',name='Mostrar puntos',exact=True).click()
        host.locator('[data-marcador]').first.click();expect(host.locator('[data-elemento]').first).to_have_attribute('aria-pressed','true')
        host.get_by_role('button',name='Aumentar zoom',exact=True).click();expect(host.locator('[data-zoom]')).to_have_attribute('data-zoom','125')
        host.get_by_role('button',name='Restablecer',exact=True).click();expect(host.locator('[data-zoom]')).to_have_attribute('data-zoom','100')
        check(host.locator('.mv-abrir-completa').count()==0,label+' sin botón pantalla completa')
        if modal:
         cerrar=host.get_by_role('button',name='Cerrar recurso',exact=True)
         if ancho<500:cerrar.tap()
         else:cerrar.click()
         expect(page.locator('dialog')).to_have_count(0);expect(acceso).to_be_focused()
      if modo=='visual' and enfoque=='estudio':
       visor3=page.locator('[data-uso="mc-12-19-levirato"]')
       visor3.get_by_role('button',name='Aumentar zoom',exact=True).click()
       page.locator('[data-enfoque="devocional"]').click();expect(page.locator('.mv-recurso')).to_have_count(0)
       page.locator('[data-enfoque="estudio"]').click();expect(page.locator('[data-uso="mc-12-19-levirato"] [data-zoom]')).to_have_attribute('data-zoom','125')
       check(True,label+' visor conserva estado al cambiar enfoque')
       hoja=page.locator('[data-relato-contenido="mc-12-18-27"] .mv-contexto')
       siguiente=hoja.get_by_role('button',name='Siguiente →',exact=True)
       expect(siguiente).to_be_enabled();antes=hoja.locator('output').inner_text();siguiente.click()
       expect(hoja.locator('output')).not_to_have_text(antes)
       check(True,label+' contexto con paginación horizontal')
      if modo=='visual':
       tercera=page.locator('[data-relato-contenido="mc-12-18-27"]')
       check('Una pregunta sobre la muerte, una respuesta sobre la vida' in tercera.inner_text(),label+' frase de interés en HTML')
       img=tercera.locator('.mv-portada img')
       check(tercera.locator('.mv-portada-hook-texto').count()==1 and tercera.get_by_text('Una pregunta sobre la muerte, una respuesta sobre la vida',exact=True).count()==1,label+' hook HTML presente sin duplicados')
       for tamano in [8,12,20,30]:
        page.evaluate('(n)=>document.body.style.setProperty("--mv-tamano-lectura",n+"px")',tamano)
        page.evaluate('async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}')
        medidas=tercera.evaluate('''e=>{const f=e.querySelector('.mv-portada'),i=f.querySelector('img'),h=f.querySelector('.mv-portada-hook-texto'),t=e.querySelector('.mv-titulo-relato');const r=f.getBoundingClientRect(),s=h.getBoundingClientRect(),a=i.getBoundingClientRect();return {ratio:r.width/r.height,imagen:a.width/a.height,titulo:t.getBoundingClientRect().bottom<=r.top&&!f.contains(t),hook:s.left>=r.left&&s.right<=r.right&&s.top>=r.top&&s.bottom<=r.bottom,html:h.querySelector('.mv-portada-subtitulo-cine').textContent,visible:getComputedStyle(h).position==='absolute'&&getComputedStyle(h).color==='rgb(255, 255, 255)',recorte:h.scrollHeight<=h.clientHeight&&h.scrollWidth<=h.clientWidth}}''')
        cine=tercera.evaluate('''e=>{const f=e.querySelector('.mv-portada'),h=f.querySelector('.mv-portada-hook-texto'),spans=[...h.querySelectorAll('.mv-portada-titulo-cine > span')],linea=h.querySelector('.mv-portada-filete'),sub=h.querySelector('.mv-portada-subtitulo-cine');const r=f.getBoundingClientRect(),a=spans[0].getBoundingClientRect(),b=spans[1].getBoundingClientRect(),s=getComputedStyle(spans[0]),d=getComputedStyle(spans[1]),l=getComputedStyle(linea),k=getComputedStyle(sub);return {textos:spans.map(x=>x.textContent),blanco:s.color==='rgb(255, 255, 255)',dorado:d.color==='rgb(230, 199, 126)',serif:s.fontFamily.includes('Georgia'),dosLineas:a.bottom<=b.top+.2&&a.height<=parseFloat(s.fontSize)*1.1&&b.height<=parseFloat(d.fontSize)*1.1,filete:l.backgroundColor===d.color&&linea.getBoundingClientRect().height===1,hook:k.fontStyle==='italic'&&parseFloat(k.fontSize)>=12&&parseFloat(k.fontSize)<parseFloat(s.fontSize),inferior:h.getBoundingClientRect().top>=r.top+r.height*.5,degradado:getComputedStyle(f,'::after').backgroundImage.includes('linear-gradient')}}''')
        check(cine['textos']==['La resurrección','y los saduceos'] and cine['blanco'] and cine['dorado'] and cine['serif'] and cine['dosLineas'],label+f'/{tamano}px título serif blanco y dorado en dos líneas')
        check(cine['filete'] and cine['hook'] and cine['inferior'] and cine['degradado'],label+f'/{tamano}px filete, hook elegante y texto inferior legible')
        check(abs(medidas['ratio']-16/9)<.005 and abs(medidas['imagen']-16/9)<.005,label+f'/{tamano}px banner e imagen 16:9')
        check(medidas['titulo'] and medidas['hook'] and medidas['recorte'] and medidas['visible'] and medidas['html']=='Una pregunta sobre la muerte, una respuesta sobre la vida',label+f'/{tamano}px título externo y hook HTML superpuesto sin recortes')
       page.evaluate('document.body.style.setProperty("--mv-tamano-lectura","12px")')
      else:
       tercera=page.locator('[data-relato-contenido="mc-12-18-27"]')
       check(tercera.locator('.mv-portada-hook-texto').count()==0 and tercera.get_by_text('Una pregunta sobre la muerte, una respuesta sobre la vida',exact=True).count()==1,label+' Solo texto conserva presentación sin banner ni hook superpuesto')
      for relato in catalogo['relatos']:
       page.locator(f'[data-relato-indice="{relato["id"]}"]').click();expect(page.locator('#motor')).to_have_attribute('data-relato',relato['id'])
       expect(page.locator(f'[data-relato-indice="{relato["id"]}"]')).to_have_attribute('aria-current','true')
      check(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),label+' sin desbordamiento horizontal')
    page.goto(base+'motor-visual/demo.html?relato=demo-dos&modo=visual');page.wait_for_selector('.mv-relato')
    check('Los labradores malvados' not in page.locator('body').inner_text(),f'{ancho} demo sintética independiente')
    check(not errores and not fallos,f'{ancho} sin errores JavaScript ni HTTP: {errores} {fallos}')
    ctx.close()
   browser.close()
 finally:server.shutdown();server.server_close()
args.informe.write_text(json.dumps({'ok':True,'urlPublica':args.url,'comprobaciones':len(checks),'casos':checks},ensure_ascii=False,indent=2)+'\n')
print('Tres estudios y cuatro modos:',len(checks),'comprobaciones correctas.')

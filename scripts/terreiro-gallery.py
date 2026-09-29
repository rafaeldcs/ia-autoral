"""Build a local gallery from the QA worker's synthetic screenshots."""
import argparse
import html
import json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);args=p.parse_args()
root=args.directory
report=json.loads((root/'browser-report.json').read_text())
interactions=json.loads((root/'interaction-report.json').read_text())
cards=[]
for item in report['screens']:
    filename=item['file']
    if Path(filename).name!=filename or not filename.endswith('.png'): raise ValueError('Invalid screenshot filename')
    label=f"{item['role']} · {item['path']} · {item['viewport']}"
    cards.append(f'<article data-label="{html.escape(label,quote=True)}"><h2>{html.escape(label)}</h2><a href="screenshots/{html.escape(filename,quote=True)}"><img loading="lazy" src="screenshots/{html.escape(filename,quote=True)}" alt="{html.escape(label,quote=True)}"></a></article>')
for filename in interactions['screenshots']:
    if Path(filename).name!=filename: raise ValueError('Invalid filename')
    cards.append(f'<article data-label="interação"><h2>{html.escape(filename)}</h2><a href="screenshots/{filename}"><img loading="lazy" src="screenshots/{filename}" alt="Interação funcional sintética"></a></article>')
page='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MeuTerreiro — evidências da simulação</title>
<style>body{font:16px system-ui;background:#f2f6f5;color:#143c36;margin:32px}h1{font-size:30px}input{font:inherit;padding:12px;width:min(90%,600px)}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}article{background:white;padding:14px;border-radius:12px}h2{font-size:16px}img{width:100%;height:360px;object-fit:contain;object-position:top}a{color:#146c61}[hidden]{display:none}</style>
<h1>MeuTerreiro · centro de simulação</h1><p>Capturas produzidas pelo executor de navegador do LocalAuthor. Dados fictícios. O modelo escolheu a etapa; os roteiros foram escritos por Codex.</p>
<p><a href="http-report.json">Simulação HTTP</a> · <a href="followup-report.json">Verificações adicionais</a> · <a href="browser-report.json">Navegação</a> · <a href="interaction-report.json">Interações</a></p>
<label>Filtrar por perfil, tela ou dispositivo <input id="filter" placeholder="Ex.: Treasury mensalidades mobile"></label><p id="count"></p><main>'''+''.join(cards)+'''</main><script>const cards=[...document.querySelectorAll('article')];const input=document.querySelector('#filter');function filter(){const terms=input.value.toLowerCase().split(/\\s+/).filter(Boolean);let count=0;for(const c of cards){c.hidden=!terms.every(t=>c.dataset.label.toLowerCase().includes(t));if(!c.hidden)count++;}document.querySelector('#count').textContent=count+' capturas';}input.addEventListener('input',filter);filter();</script></html>'''
(root/'index.html').write_text(page,encoding='utf-8')
print(json.dumps({'screenshots':len(cards),'gallery':'index.html'}))

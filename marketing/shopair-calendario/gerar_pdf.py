"""Document compositor reviewed by Codex. Editorial copy is read from LocalAuthor output.

Requires reportlab. Fonts/logo are licensed and provenance is in assets/proveniencia.json.
Does not call an AI, access accounts, publish posts or schedule external work.
"""
from pathlib import Path
import json
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

ROOT=Path(__file__).parent
OUT=ROOT.parent.parent/'output/pdf/SHOPAIR_POSTAGENS_CALENDARIO_20261008.pdf'
W,H=595.276,841.89
BLUE=HexColor('#2452ff');PURPLE=HexColor('#7c3ff2');PINK=HexColor('#ec2a9a')
DARK=HexColor('#0f172a');BODY=HexColor('#334155');GRAY=HexColor('#64748b');PALE=HexColor('#f8fbff');LINE=HexColor('#dce5f2')

def main():
 for name,file in [('Outfit','Outfit400.ttf'),('OutfitB','Outfit700.ttf'),('Jakarta','Jakarta400.ttf'),('JakartaB','Jakarta700.ttf')]:
  pdfmetrics.registerFont(TTFont(name,str(ROOT/'assets'/file)))
 data=json.loads((ROOT/'postagens.json').read_text(encoding='utf-8'))
 assert data['reviewed'] and len(data['posts'])==12
 OUT.parent.mkdir(parents=True,exist_ok=True)
 c=canvas.Canvas(str(OUT),pagesize=(W,H),pageCompression=1)
 c.setTitle('ShopAir | Postagens e calendário editorial');c.setAuthor('LocalAuthor - conteúdo; Codex - pesquisa, revisão e diagramação')
 pages=[];n=0
 def gradient(x,y,w,h):
  for i in range(80):
   t=i/79;a,b=(BLUE,PURPLE) if t<.5 else (PURPLE,PINK);u=t*2 if t<.5 else (t-.5)*2
   c.setFillColor(Color(a.red+(b.red-a.red)*u,a.green+(b.green-a.green)*u,a.blue+(b.blue-a.blue)*u))
   c.rect(x+i*w/80,y,w/80+.3,h,fill=1,stroke=0)
 def para(text,x,top,width,size=10.5,font='Jakarta',color=BODY,leading=None,bottom=58):
  style=ParagraphStyle('p',fontName=font,fontSize=size,leading=leading or size*1.42,textColor=color,spaceAfter=0)
  p=Paragraph(escape(str(text)).replace('\n','<br/>'),style);_,height=p.wrap(width,H)
  if top-height<bottom:raise ValueError(f'Overflow page {n}: {str(text)[:70]}, bottom {top-height:.1f}')
  p.drawOn(c,x,top-height);return top-height
 def rich(text,x,top,width,size=10.5):
  p=Paragraph(text,ParagraphStyle('r',fontName='Jakarta',fontSize=size,leading=size*1.4,textColor=BODY))
  _,h=p.wrap(width,H)
  if top-h<58:raise ValueError(f'Overflow link page {n}')
  p.drawOn(c,x,top-h);return top-h
 def label(text,x,y):return para(text.upper(),x,y,510,8.2,'JakartaB',BLUE,11)
 def logo(x,y,size=34):
  c.drawImage(str(ROOT/'assets/shopair-icon.png'),x,y,width=size,height=size,preserveAspectRatio=True,mask='auto')
 def page(kicker,title,subtitle=None):
  nonlocal n
  if n:c.showPage()
  n+=1;pages.append(title)
  c.setFillColor(white);c.rect(0,0,W,H,fill=1,stroke=0);gradient(0,H-6,W,6)
  logo(42,H-52,23);para('ShopAir',72,H-33,130,12,'OutfitB',DARK)
  para('PLANO EDITORIAL | 4 SEMANAS',343,H-35,210,7.6,'JakartaB',GRAY)
  c.setStrokeColor(LINE);c.line(42,47,W-42,47)
  para('Proposta revisada | '+data['consultation_date'],42,33,420,7.5,'Jakarta',GRAY,bottom=8)
  para(f'{n:02d}',W-70,33,28,8,'JakartaB',BLUE,bottom=8)
  label(kicker,42,H-78)
  y=para(title,42,H-101,W-84,28,'OutfitB',DARK,31)-13
  if subtitle:y=para(subtitle,42,y,W-84,10.5,'Jakarta',GRAY)-20
  return y
 def block(title,text,y,width=511,x=42):
  y=para(title,x,y,width,14,'OutfitB',DARK)-7
  return para(text,x,y,width)-19
 def card(x,y,w,h,title,body):
  c.setFillColor(PALE);c.setStrokeColor(LINE);c.roundRect(x,y-h,w,h,9,fill=1,stroke=1)
  yy=para(title,x+13,y-14,w-26,13,'OutfitB',DARK)-10
  para(body,x+13,yy,w-26,9.6,bottom=y-h+10)
 def art(post,x,y,width,height,slide=None):
  # Native typographic concept: it is deliberately not a fabricated application screenshot.
  c.saveState();c.translate(x,y);c.scale(width/232,width/232)
  x=y=0;width=232;height=290
  c.setFillColor(PALE);c.setStrokeColor(LINE);c.roundRect(x,y-height,width,height,12,fill=1,stroke=1)
  gradient(x+14,y-height+14,width-28,5);logo(x+18,y-47,27)
  para('ShopAir',x+52,y-24,width-70,12,'OutfitB',DARK,bottom=y-height+20)
  sl=slide or {'titulo':post['headline'],'apoio':post['visual_support']}
  para(post['segment_label'].upper(),x+20,y-66,width-40,7.5,'JakartaB',BLUE,bottom=y-height+20)
  end=para(sl['titulo'],x+20,y-85,width-40,19,'OutfitB',DARK,22,bottom=y-height+85)
  para(sl['apoio'],x+20,end-12,width-40,10,'Jakarta',BODY,14,bottom=y-height+65)
  c.setFillColor(BLUE);c.roundRect(x+20,y-height+32,width-40,26,7,fill=1,stroke=0)
  para(post['cta_arte'],x+28,y-height+50,width-56,9.2,'JakartaB',white,12,bottom=y-height+30)
  c.restoreState()
 y=page('Campanha de descoberta e contato','Sua marca. Seu produto.\nUma conversa que faz sentido.','Postagens originais da ShopAir, criadas pela LocalAuthor com pesquisa e revisão supervisionadas.')
 logo(48,y-150,118)
 para('ShopAir',188,y-46,320,42,'OutfitB',DARK,46)
 para('Vitrine online e gestão para\nlojas e restaurantes',191,y-104,320,17,'Outfit',BODY,23)
 y-=183
 y=block('12 peças, quatro semanas', 'Textos para Instagram e Facebook, carrosséis completos, três roteiros de vídeo e desdobramentos para Stories. Um objetivo comum: gerar interesse e contatos compatíveis com o produto.',y)
 y=block('Como usar este documento','Defina a data da Semana 1, confira o destino de contato e aprove as peças. O calendário é operacional e relativo: nenhuma publicação ou conta foi acionada nesta entrega.',y)
 y=block('Autoria transparente','A LocalAuthor escreveu propostas e revisões no modelo local. Codex pesquisou, conferiu o produto e a marca, revisou e editou os textos, definiu controles e diagramou o PDF. As versões iniciais reprovadas foram preservadas em registros privados. Este trabalho supervisionado não altera os pesos nem comprova autonomia geral.',y)
 y=page('Pesquisa de mercado','O que o mercado ensina','Fontes oficiais comparadas por mensagem, demonstração e entrada comercial; consulta em '+data['consultation_date']+'.')
 for item in data['market']:
  y=block(item['name'],item['observation']+'\nAplicação para a ShopAir: '+item['application'],y)
 y=block('Pista de contexto, com limites','A Pesquisa Serviço 2025 do Sebrae, com mais de 1.300 pequenos negócios de serviço, aponta uso frequente de WhatsApp e pouca sistematização. Isso inspira linguagem prática sobre atendimento; não mede os seguidores nem os resultados da ShopAir.',y)
 y=block('O que ainda falta medir','Sem Insights das contas, entrevistas com clientes ou histórico de conversão disponível. Cadência, temas e horários são hipóteses editoriais. Não há ranking comprovado de artes que mais vendem.',y)
 y=page('Estratégia','Um público, duas rotinas','A ShopAir vende a plataforma. As peças falam com quem administra o negócio, não com quem compra roupas ou comida.')
 y=block('Lojista','Decisor de pequeno varejo que precisa apresentar produtos e organizar o cotidiano. Começar por foto, descrição, variação e disponibilidade; depois apresentar estoque, caixa e relatórios. Evitar abrir a conversa com jargão técnico.',y)
 y=block('Gestor de restaurante','Responsável pelo cardápio e pela operação. Mostrar a sequência cardápio, preparo e modalidades de atendimento. Usar exemplos de rotina, sem anunciar funcionalidades de concorrentes como se fossem da ShopAir.',y)
 y=block('Mensagem de campanha',data['strategy']['posicionamento'],y)
 for week,goal in [(1,'Descoberta: vitrine e catálogo do varejo.'),(2,'Entendimento: cardápio e modalidades do restaurante.'),(3,'Consideração: gestão, atendimento e escopo dos módulos.'),(4,'Ação: preparar a vitrine e conhecer a plataforma.')]:
  y=block(f'Semana {week}',goal,y)
 y=block('Contato que interessa','Um responsável por loja ou restaurante com necessidade identificada e meio autorizado de acompanhamento. Visita ou clique isolado mede tráfego; não equivale a oportunidade qualificada.',y)
 y=page('Identidade visual','Reconhecível como ShopAir','Logo preservada e tipografia do produto. O conceito de arte é original, sem copiar a comunicação dos concorrentes.')
 logo(52,y-133,112)
 para('Carrinho + nuvem + cursor',196,y-15,340,20,'OutfitB',DARK)
 para('Usar o símbolo original. Não recolorir, esticar ou substituir. Reservar ao menos metade da altura do símbolo como respiro; sugestão de produção, não manual oficial da marca.',196,y-56,340,10.5)
 y-=158
 for i,(name,color,hx) in enumerate([('Azul',BLUE,'#2452ff'),('Roxo',PURPLE,'#7c3ff2'),('Magenta',PINK,'#ec2a9a')]):
  x=42+i*176;c.setFillColor(color);c.roundRect(x,y-61,159,61,8,fill=1,stroke=0)
  para(name+'\n'+hx,x,y-73,159,10,'JakartaB',DARK)
 y-=133
 y=block('Outfit nos títulos | Plus Jakarta Sans no corpo','As fontes foram conferidas no código da interface e adquiridas da coleção Google Fonts sob SIL OFL 1.1. O gradiente azul-roxo-rosa acompanha a marca; os tokens acima são do BrandSystem, não amostras do gradiente inteiro.',y)
 y=block('Hierarquia para celular','Feed 1080 x 1350: margem proposta de 80 px; título 64-76 px, apoio 38-44 px, chamada 32-38 px. Uma ideia por slide. Logo 72 px ou maior. Vídeo/Stories 1080 x 1920: revisar sobreposição da interface de cada canal na prévia de publicação.',y)
 y=block('Legibilidade antes da decoração',f"Texto escuro sobre fundo claro. Chamada branca sobre azul: contraste calculado de {data['contrast']['white_blue']:.2f}:1. Branco sobre magenta: {data['contrast']['white_magenta']:.2f}:1; evitar esse par em texto pequeno. As razões não certificam acessibilidade do produto inteiro.",y)
 y=page('Programação editorial','Quatro semanas, três peças por semana','Calendário relativo. Terças e quintas às 12h; sábados às 18h, horário de Brasília. Janelas candidatas, sem evidência de melhor horário.')
 header=['SEMANA / DIA','PEÇA','FORMATO / TEMA']
 for x,t in zip([42,166,222],header):label(t,x,y)
 y-=26
 for p in data['posts']:
  c.setStrokeColor(LINE);c.line(42,y-38,W-42,y-38)
  para(f"{p['week']} / {p['day']} {p['time']}",42,y,117,9.2)
  para(p['id'],166,y,46,10,'JakartaB',BLUE)
  para(p['format_label']+' | '+p['theme'],222,y,330,9.5)
  y-=40
 y=block('Ajuste antes da Semana 1','Selecione uma data de início compatível com a equipe. Revise feriados, novidades do produto e disponibilidade de atendimento. Se houver Insights, ajuste as janelas e registre a decisão; não transforme a proposta em horário universal.',y-8)
 y=page('Canais e produção','Adaptar a mensagem ao lugar','Uma pessoa de marketing pode produzir em lotes; a cadência precisa caber no tempo real disponível.')
 y=block('Instagram','Feed e carrossel em 4:5. Legenda completa nas páginas de cada peça. Configurar o link da bio para o site oficial antes da publicação; não tratar URL na legenda como botão. Usar texto alternativo coerente com a arte final.',y)
 y=block('Facebook','Publicar a versão própria da legenda, com URL direta. Ajustar a composição à prévia do canal. Identificar links com UTM quando houver medição compatível; a existência do parâmetro não garante que analytics estejam configurados.',y)
 y=block('Reels e TikTok','Os três roteiros são verticais, com 30 segundos cada. Pessoa real, fala natural, situação nos primeiros segundos, produto visível e chamada final. Legendar as falas. Usar trilha própria/licenciada para uso comercial; não assumir direitos sobre áudio em tendência. No TikTok, confirmar elegibilidade do link do perfil ou usar o endereço falado shopair.com.br.',y)
 y=block('Stories: dois por semana','Quarta: retomar o tema da terça com uma pergunta. Sexta: preparar a peça de sábado com enquete ou cardápio de dúvidas. Os oito textos e respostas estão na página de acompanhamento. Aplicar apenas recursos que existam na conta.',y)
 y=block('Rotina de trabalho','Segunda: separar material e conferir recursos do produto. Terça: finalizar/publicar a primeira peça aprovada. Quinta: segunda peça. Sábado: terceira. Revisar contatos no próximo período atendido pela equipe. Uma revisão semanal compara desempenho sem mudar todas as variáveis ao mesmo tempo.',y)
 y=page('Produto e evidência','O que pode entrar na comunicação','Escopo editorial baseado no site público e na inspeção autorizada do código. Não é uma certificação funcional de todos os módulos.')
 for title,text in data['scope']:
  y=block(title,text,y)
 y=block('Demonstração não é prova social','A prévia pública e as vitrines ilustrativas podem explicar a proposta. Seus produtos e valores de exemplo não são faturamento nem clientes da ShopAir. Ao gravar, manter rótulo “Prévia ilustrativa” e usar somente material sem dados pessoais.',y)
 y=block('Antes de anunciar uma novidade','O responsável pelo produto confirma recurso, plano, disponibilidade e limite. Recurso anunciado no site não é automaticamente comprovado em uma operação real. Não promover prazo, preço ou integração específica sem conferir condições vigentes.',y)
 for post in data['posts']:
  y=page(post['id']+' | '+post['format_label'],post['headline'],f"Semana {post['week']} | {post['day']} {post['time']} | {post['audience']}")
  art(post,42,y,232,290,post.get('slides',[None])[0] if post.get('slides') else None)
  yy=label('Intenção da peça',294,y-4)
  yy=para(post['intent'],294,yy-12,259,10.5)-17
  yy=label('Por que este texto',294,yy)
  yy=para(post['porque'],294,yy-12,259,10.2)-17
  yy=label('Direção de arte',294,yy)
  para(post['art_direction'],294,yy-12,259,9.3,bottom=y-290)
  y-=305
  y=label('Legenda Instagram | texto para publicação',42,y)-12
  y=para(post['legenda_instagram'],42,y,W-84,10.1)-17
  y=label('Legenda Facebook | texto para publicação',42,y)-12
  y=para(post['legenda_facebook'],42,y,W-84,10.1)-15
  y=para('Métrica principal: '+post['metric']+'\nBase factual: '+', '.join(post['source_ids'])+'. Conceito visual: proposta, não captura funcional.',42,y,W-84,8.2,'Jakarta',GRAY)
  if post['format']=='carrossel':
   y=page(post['id']+' | texto da sequência','O carrossel, slide a slide','Cada quadro abaixo contém o texto integral da peça. Os conceitos respeitam a logo e o contraste da marca.')
   for i,sl in enumerate(post['slides']):
    x=42+(i%2)*264;top=y-(i//2)*270
    para(f'SLIDE {i+1:02d}',x,top,232,8,'JakartaB',BLUE)
    art(post,x,top-20,200,250,sl)
   para('Produção: mesma grade nos quatro slides; apoio legível no celular. A chamada na imagem orienta a ação, sem ser um botão clicável. Texto alternativo deve mencionar a sequência e os conteúdos.',42,y-552,W-84,9.2)
  if post['format']=='video':
   y=page(post['id']+' | roteiro de gravação','Trinta segundos, uma situação','Vertical 1080 x 1920. Prévia ilustrativa identificada durante toda captura do produto; nenhuma ação de compra.')
   for scene in post['cenas']:
    label(f"{scene['inicio']:02d}s - {scene['fim']:02d}s",42,y)
    yy=para('Fala: '+scene['fala'],128,y,425,11,'JakartaB',DARK)-5
    yy=para('Imagem: '+scene['tela'],128,yy,425,9.5)
    y=min(y-72,yy-18)
   y=block('Capa e adaptação por canal',post['texto_capa']+'\nInstagram: última chamada e legenda remetem ao link da bio. TikTok: substituir somente o destino final por “Conheça em shopair.com.br” se não houver link utilizável no perfil. O restante mantém o mesmo argumento.',y)
   para('Descrição visual proposta: '+post['alt_text'],42,y,W-84,9.5)
 y=page('Acompanhamento','Oito Stories e respostas úteis','Extensões da campanha. Textos para revisão e uso manual; perguntas públicas sem solicitar dados pessoais.')
 for story in data['stories']:
  y=block(f"S{story['week']} | {story['day']}",story['text']+'\nInteração: '+story['interaction'],y)
 y=page('Conversas','A postagem começa uma conversa','Respostas comerciais que acolhem a dúvida sem inventar escopo, preço ou prazo.')
 for response in data['responses']:
  y=block(response['question'],response['reply'],y)
 y=block('Encaminhamento','Registrar a dúvida e a necessidade sem copiar dados privados para o corpus. Preço, condição e suporte são confirmados pela equipe. Reclamação não vira depoimento; encaminhar com consentimento e acompanhar a resposta.',y)
 y=page('Medição e decisão','Medir interesse, não inventar resultado','A campanha ainda não foi publicada. Não há métricas de desempenho realizadas nesta entrega.')
 for title,text in data['measurement']:
  y=block(title,text,y)
 y=page('Operação e autoria','Da proposta à publicação','O material está pronto para revisão comercial e produção. Contas, permissões e data de início continuam sob responsabilidade da empresa.')
 for title,text in data['operations']:
  y=block(title,text,y)
 y=block('Ensinamentos registrados nesta sessão','Diferenciar métricas de resultados; não inferir ausência de recursos em concorrentes; preservar escopo dos módulos; adaptar chamadas ao canal; entregar texto e roteiro completos. O feedback e a lição de consulta são persistidos separadamente dos pesos. A qualificação geral continua condicionada a avaliação independente.',y)
 y=page('Referências verificáveis','Pesquisa, produto e identidade','Fontes primárias. Conteúdo consultado para análise; não constitui autorização automática de treinamento.')
 for i,source in enumerate(data['sources']):
  if i==5:y=page('Referências verificáveis | continuação','Contexto e boas práticas','Datas e população das pesquisas preservadas; resultados da campanha ainda não medidos.')
  y=para(source['id']+' | '+source['label'],42,y,W-84,10,'JakartaB',DARK)-3
  y=rich('<link href="'+escape(source['url'],{'"':'&quot;'})+'" color="#2452ff">'+escape(source['url'])+'</link>',42,y,W-84,8.3)-4
  y=para(source['note'],42,y,W-84,8.7,'Jakarta',GRAY)-14
 c.save()
 (ROOT/'paginas.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'PDF created: {n} pages; {OUT.stat().st_size} bytes')

if __name__=='__main__':main()

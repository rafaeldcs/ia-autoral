'use client';
import {useEffect,useState} from 'react';
import {api} from './client';
type Score={passed:number;total:number};
type Case={id:string;kind:string;prompt:string;generated:string;passed:boolean;accepted:boolean;referencePass?:boolean;mutantKilled?:boolean;reason?:string};
type Report={state:string;counts:{train:number};steps?:number;beforeEvaluation?:Score;referenceEvaluation?:Score;memorizationDiagnostic?:Score;evaluation?:Score&{byKind:Record<string,Score>;cases:Case[]};limitations:string};
const names:Record<string,string>={boundary:'Limites',exception:'Exceções',calculation:'Cálculos',authentication:'Autenticação HTTP',authorization:'Permissões HTTP',concurrency:'Conflito de versão',count:'Criação de itens',xss:'Conteúdo HTML',keyboard:'Navegação por teclado'};
export function CodeTesting(){
 const [data,setData]=useState<Report|null>(null);
 useEffect(()=>{let active=true;api<Report>('/experiment/code-testing').then(d=>{if(active)setData(d)}).catch(()=>{});return()=>{active=false}},[]);
 if(!data)return null;
 return <section className="planning">
  <div className="section-heading"><div><span className="eyebrow">CÓDIGO GERADO PELA IA LOCAL</span><h2>Testes que precisam encontrar o defeito</h2><p>{data.counts.train} exemplos de xUnit e Playwright. Continuação dos próprios pesos da IA, com avaliação separada.</p></div><span className="status-pill progress">{data.state==='evaluated'?'Avaliação concluída':'Em avaliação'}</span></div>
  <div className="metric-grid">
   <div><span>Casos novos · antes</span><strong>{data.beforeEvaluation?`${data.beforeEvaluation.passed}/${data.beforeEvaluation.total}`:'—'}</strong></div>
   <div><span>Casos novos · depois</span><strong>{data.evaluation?`${data.evaluation.passed}/${data.evaluation.total}`:'—'}</strong></div>
   <div><span>Referências do professor</span><strong>{data.referenceEvaluation?`${data.referenceEvaluation.passed}/${data.referenceEvaluation.total}`:'—'}</strong><p className="subtle">Elaboradas pelo Codex; não contam como capacidade da IA local.</p></div>
  </div>
  <p>Um acerto exige atender ao pedido, passar no programa correto e falhar quando o defeito é introduzido. Somente respostas aceitas pela triagem são executadas em contêiner isolado, sem acesso à rede externa.</p>
  {data.memorizationDiagnostic&&<p className="subtle">Repetição de exercícios já vistos no treino: {data.memorizationDiagnostic.passed}/{data.memorizationDiagnostic.total}. Isso mede reprodução, não solução de casos novos.</p>}
  {data.evaluation&&<div className="metric-grid">{Object.entries(data.evaluation.byKind).map(([kind,s])=><div key={kind}><span>{names[kind]??kind}</span><strong>{s.passed}/{s.total}</strong></div>)}</div>}
  <div className="experiment-note"><strong>Resultado limitado aos exercícios avaliados.</strong><p>{data.limitations} Os casos reservados usam novos parâmetros das mesmas famílias de exemplos. Correções registradas em arquivo não alteram os pesos automaticamente.</p></div>
  {data.evaluation&&<details className="panel"><summary>Inspecionar as respostas reais e seus resultados</summary>{data.evaluation.cases.map(c=><div className="learning-case" key={c.id}><strong>{names[c.kind]} · {c.id} · {c.passed?'Detectou o defeito':'Não aprovado'}</strong><p>{c.prompt}</p><pre>{c.generated}</pre><small>{c.accepted?`Programa correto: ${c.referencePass?'passou':'falhou'}. Defeito detectado: ${c.mutantKilled?'sim':'não'}.`:`Não executado: ${c.reason==='requested_case_not_implemented'?'não usou os parâmetros solicitados':c.reason}`}</small></div>)}</details>}
 </section>
}

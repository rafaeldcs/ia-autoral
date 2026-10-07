'use client';
import {useEffect,useState} from 'react';
import {api} from './client';
type Report={cases:{id:string;prompt:string;response:string;usable:boolean;reason:string}[];training:{steps:number;trainPassed:number;trainTotal:number;testPassed:number;testTotal:number;regressionPassed:number;regressionTotal:number;activated:boolean};reference:{checks:number;unitTests:number;flowP95Ms:number};notice:string};
export function ProfessionalExperiment(){
  const [data,setData]=useState<Report|null>(null),[error,setError]=useState('');
  useEffect(()=>{let active=true;api<Report>('/experiment/professional').then(d=>{if(active)setData(d)}).catch(e=>{if(active)setError(e.message)});return()=>{active=false}},[]);
  if(!data)return error?<p role="status">O relatório do desafio profissional ainda não está disponível.</p>:<p role="status">Carregando desafio profissional…</p>;
  return <section className="planning"><div className="section-heading"><div><span className="eyebrow">AVALIAÇÃO NOVA · PEDIDOS NÃO TREINADOS</span><h2>A IA consegue evoluir um projeto profissional?</h2><p>{data.notice}</p></div></div>
    <div className="metric-grid report-metrics"><div><span>Respostas utilizáveis</span><strong>{data.cases.filter(c=>c.usable).length}/{data.cases.length}</strong></div><div><span>Código aplicado da IA</span><strong>0</strong></div><div><span>Testes da referência Codex</span><strong>{data.reference.checks}</strong></div><div><span>Fluxo local · p95</span><strong>{data.reference.flowP95Ms} ms</strong></div></div>
    <div className="panel"><h3>Treino corretivo: {data.training.steps} passos nos pesos próprios</h3><p>Exemplos ensinados: {data.training.trainPassed}/{data.training.trainTotal}. Pedidos reservados: {data.training.testPassed}/{data.training.testTotal}. Regressão: {data.training.regressionPassed}/{data.training.regressionTotal}. O candidato não foi ativado.</p><p>As melhorias Scrum/Kanban foram implementadas e testadas por Codex. Compilação e testes dessa referência não qualificam o modelo local.</p></div>
    {data.cases.map(c=><details className="panel" key={c.id}><summary>{c.prompt}</summary><h3>Resposta original do modelo local</h3><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{c.response}</pre><p>{c.reason}</p></details>)}
  </section>;
}

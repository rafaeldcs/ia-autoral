'use client';
import {useEffect, useState} from 'react';
import {api} from './client';

export type WorkflowProject = {id:string; method:'scrum'|'kanban'; wipLimit:number; workflowVersion:number};

export function WorkflowSettings({project, manage, wip, onSaved}: {
  project:WorkflowProject; manage:boolean; wip:number; onSaved:(value:Partial<WorkflowProject>)=>void;
}) {
  const [method,setMethod]=useState(project.method);
  const [limit,setLimit]=useState(project.wipLimit);
  const [busy,setBusy]=useState(false),[message,setMessage]=useState('');
  useEffect(()=>{setMethod(project.method);setLimit(project.wipLimit);setMessage('')},[project]);
  async function save() {
    setBusy(true);setMessage('');
    try {
      const result=await api<Partial<WorkflowProject>>(`/projects/${project.id}/workflow`,'PUT',{
        method,wipLimit:limit,version:project.workflowVersion
      });
      onSaved(result);setMessage('Método atualizado.');
    } catch(error) {setMessage((error as Error).message)} finally {setBusy(false)}
  }
  return <section className="workflow-settings" aria-label="Método do projeto">
    <div><strong>{project.method==='kanban'?'Kanban · fluxo contínuo':'Scrum · entregas por sprint'}</strong>
      <p>{project.method==='kanban'?`${wip} de ${project.wipLimit} vagas em uso. O limite soma Em andamento e Em revisão.`:'Planeje uma meta na aba Sprints e associe as tarefas de cada ciclo.'}</p>
    </div>
    {manage&&<details><summary>Configurar método</summary><div className="workflow-form">
      <label>Método<select aria-label="Método de trabalho" value={method} onChange={e=>setMethod(e.target.value as 'scrum'|'kanban')}><option value="scrum">Scrum</option><option value="kanban">Kanban</option></select></label>
      {method==='kanban'&&<label>Limite em andamento<input aria-label="Limite de trabalho em andamento" type="number" min={1} max={100} value={limit} onChange={e=>setLimit(Number(e.target.value))}/></label>}
      <button className="button secondary" disabled={busy||!Number.isInteger(limit)||limit<1||limit>100} onClick={save}>{busy?'Salvando…':'Salvar método'}</button>
    </div><p>Para mudar para Kanban, encerre as sprints pendentes. O histórico será preservado.</p></details>}
    {message&&<p role="status">{message}</p>}
  </section>;
}

type Day={day:string;backlog:number;todo:number;progress:number;review:number;done:number};
type Flow={isSimulation:boolean;wip:number;throughput14Days:number;cycleMedianHours:number|null;cycleP85Hours:number|null;cycleSamples:number;oldestAgeHours:number|null;daily:Day[]};
const stages=[['done','Concluído','#238879'],['review','Em revisão','#9561bd'],['progress','Em andamento','#5368d7'],['todo','A fazer','#9aa8bd'],['backlog','Backlog','#dce2ed']] as const;
function duration(hours:number|null) {
  if(hours===null)return 'Sem amostra';
  if(hours<1/60)return '< 1 min';
  return hours<1?`${Math.round(hours*60)} min`:hours<24?`${hours.toLocaleString('pt-BR',{maximumFractionDigits:1})} h`:`${(hours/24).toLocaleString('pt-BR',{maximumFractionDigits:1})} dias`;
}
export function FlowReport({project,onOpen}:{project:string;onOpen:()=>void}) {
  const [data,setData]=useState<Flow|null>(null),[error,setError]=useState('');
  useEffect(()=>{let live=true;setData(null);setError('');api<Flow>(`/projects/${project}/flow`).then(d=>{if(live)setData(d)}).catch(e=>{if(live)setError(e.message)});return()=>{live=false}},[project]);
  if(error)return <p role="alert">{error}</p>;
  if(!data)return <p role="status">Calculando fluxo…</p>;
  const maximum=Math.max(1,...data.daily.map(d=>stages.reduce((sum,[key])=>sum+d[key],0)));
  const x=(i:number)=>40+i/Math.max(1,data.daily.length-1)*680;
  const y=(n:number)=>220-n/maximum*185;
  return <section className="planning flow-report" aria-labelledby="flow-title">
    {data.isSimulation&&<p className="simulation-notice" role="note">Simulação identificada: tarefas, pessoas e datas deste projeto são fictícias. Os indicadores são calculados desses eventos de demonstração e não representam entregas de clientes.</p>}
    <div className="section-heading"><div><span className="eyebrow">SAÚDE DO FLUXO</span><h2 id="flow-title">Onde o trabalho precisa de atenção?</h2><p>Dados do histórico registrado no PostgreSQL · janela diária em UTC.</p></div><button className="button secondary" onClick={onOpen}>Ver tarefas do projeto</button></div>
    <div className="metric-grid report-metrics">
      {([['Em andamento',String(data.wip)],['Entregues / 14 dias',String(data.throughput14Days)],['Ciclo mediano',duration(data.cycleMedianHours)],['Item ativo mais antigo',duration(data.oldestAgeHours)]]).map(([label,value])=><div key={label}><span>{label}</span><strong>{value}</strong></div>)}
    </div>
    <div className="panel"><h3>Fluxo acumulado · últimos 14 dias</h3>
      <p className="subtle">A espessura das faixas mostra quantos itens estavam em cada etapa ao fim do dia. Uma faixa crescente indica acúmulo.</p>
      <svg className="flow-chart" viewBox="0 0 760 265" role="img" aria-label="Gráfico de fluxo acumulado; valores exatos na tabela abaixo">
        <text x="5" y="30">{maximum}</text><text x="15" y="225">0</text>
        {stages.map(([key,label,color],index)=>{
          const lower=(d:Day)=>stages.slice(0,index).reduce((sum,[k])=>sum+d[k],0);
          const upper=data.daily.map((d,i)=>`${x(i)},${y(lower(d)+d[key])}`);
          const bottom=data.daily.map((d,i)=>`${x(i)},${y(lower(d))}`).reverse();
          return <polygon key={key} points={[...upper,...bottom].join(' ')} fill={color}><title>{label}</title></polygon>;
        })}
        <text x="40" y="250">{data.daily[0]?.day}</text><text x="720" y="250" textAnchor="end">{data.daily.at(-1)?.day}</text>
      </svg>
      <ul className="flow-legend">{stages.map(([key,label,color])=><li key={key}><i style={{background:color}}/>{label}</li>)}</ul>
      <details><summary>Ver dados acessíveis do gráfico</summary><div className="table-scroll" tabIndex={0} role="region" aria-label="Dados diários do fluxo"><table><caption>Quantidade de tarefas por etapa no final de cada dia UTC</caption><thead><tr><th>Dia</th>{stages.map(([key,label])=><th key={key}>{label}</th>)}</tr></thead><tbody>{data.daily.map(d=><tr key={d.day}><th>{d.day}</th>{stages.map(([key])=><td key={key}>{d[key]}</td>)}</tr>)}</tbody></table></div></details>
    </div>
    <p className="subtle">{data.cycleSamples} tarefas concluídas com início registrado. P85 do ciclo: {duration(data.cycleP85Hours)}. Ciclo e idade contam desde a primeira entrada em Em andamento; reaberturas permanecem no intervalo. Conclusões sem início conhecido não entram no ciclo. Entregues conta itens distintos, inclusive se reabertos depois. Histórico anterior à coleta não é inventado. Estes dados não medem produtividade individual.</p>
  </section>;
}

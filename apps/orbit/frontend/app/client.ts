export type Account={id:string;name:string;email:string;role:'admin'|'manager'|'member'|'viewer'};
export type Sprint={id:string;name:string;goal:string;state:string;startDate:string;endDate:string;committedPoints:number;completedPoints:number;issueCount:number};
export const roles:Record<string,string>={admin:'Administrador',manager:'Gestor',member:'Colaborador',viewer:'Leitor'};
export async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'});
 const text=await response.text();let data;try{data=text?JSON.parse(text):{}}catch{throw Error('Resposta inválida do servidor.')}
 if(!response.ok){if(response.status===401&&!path.startsWith('/auth/'))window.dispatchEvent(new Event('orbit-session-expired'));throw Error(data.error||'Não foi possível concluir.')};return data;
}

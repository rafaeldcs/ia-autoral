const {test,expect}=require('/opt/node_modules/@playwright/test');
const fs=require('fs');
test('generated functional test',async({page,browser})=>{
 const base='http://127.0.0.1:3100';
 const password=require('crypto').randomBytes(24).toString('hex');
 const admin=page.context(),contexts={admin};
 async function request(role,path,data,method){
  return contexts[role].request.fetch(base+'/api'+path,{method:method||(data===undefined?'GET':'POST'),data});
 }
 async function data(role,path,body,method){const r=await request(role,path,body,method);if(!r.ok())throw Error('Fixture action '+path+' status '+r.status());return r.json();}
 await data('admin','/auth/setup',{name:'QA',email:'admin@example.test',password,role:'admin'});
 for(const role of ['viewer','member','manager']){
  // Account provisioning is a fixture precondition, not a scored model assertion.
  if(process.env.LAB_FAULT==='password'){
   // This scenario only needs the administrator; avoid corrupt fixture setup.
   break;
  }
  await data('admin','/users',{name:role,email:role+'@example.test',password,role});
  contexts[role]=await browser.newContext();
  await data(role,'/auth/login',{email:role+'@example.test',password});
 }
 let current='admin',counter=0;
 const projects={};
 const sprintBody=()=>({name:'Sprint '+(++counter),goal:'Entrega testada',startDate:new Date().toISOString().slice(0,10),endDate:new Date(Date.now()+86400000*14).toISOString().slice(0,10)});
 const h={
  async login(role){current=role;await data(role,'/auth/login',{email:role+'@example.test',password});},
  async me(){return (await request(current,'/auth/me')).status();},
  async logout(){await data(current,'/auth/logout',{});},
  async password(id,lengths){const result=[];for(const n of lengths)result.push((await request('admin','/users',{name:'Password probe',email:'length'+id+'-'+n+'@example.test',password:'a'.repeat(n),role:'viewer'})).status());return result;},
  async project(key){const p=await data('admin','/projects',{name:key,key});projects[p.id]=key;return p.id;},
  async sprint(p,role){return (await request(role,'/projects/'+p+'/sprints',sprintBody())).status();},
  async newSprint(p){return (await data('manager','/projects/'+p+'/sprints',sprintBody())).id;},
  async start(s){return (await request('manager','/sprints/'+s+'/start',{})).status();},
  async finish(s){return (await request('manager','/sprints/'+s+'/complete',{})).status();},
  async issue(p,title){return (await data('admin','/projects/'+p+'/issues',{title,status:'todo',storyPoints:3})).id;},
  async progress(t){const item=await data('admin','/issues/'+t);await data('admin','/issues/'+t,{...item,status:'progress'},'PUT');},
  async done(t){const item=await data('admin','/issues/'+t);await data('admin','/issues/'+t,{...item,status:'done'},'PUT');},
  async status(t){const r=await request('admin','/issues/'+t);return r.ok()?(await r.json()).status:'missing';},
  async reload(p){await page.goto(base);await page.getByRole('button',{name:projects[p],exact:true}).click();await page.reload();await page.getByRole('heading',{name:projects[p],exact:true}).waitFor();},
  async kanban(key,limit){const p=await h.project(key);await data('admin','/projects/'+p+'/workflow',{method:'kanban',wipLimit:limit,version:1},'PUT');return p;},
  async active(p){return (await request('admin','/projects/'+p+'/issues',{title:'Active '+(++counter),status:'progress'})).status();},
  async throughput(p){return (await data('admin','/projects/'+p+'/flow')).throughput14Days;},
  async board(key){const p=await h.project(key);await h.issue(p,'Visible item');await h.reload(p);if(process.env.LAB_FAULT==='mobile')await page.addStyleTag({content:'body{min-width:1500px!important}'});},
  async restart(){fs.writeFileSync('/tmp/lab/restart','restart\n');for(let i=0;i<150;i++){if(fs.existsSync('/tmp/lab/restarted'))return;await new Promise(r=>setTimeout(r,100));}throw Error('Restart did not finish');}
 };
 // The original model body follows without edits. Helpers never supply its assertions.

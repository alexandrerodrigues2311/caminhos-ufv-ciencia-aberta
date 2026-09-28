/* Motor de dados: usado no painel, nos testes e na simulação reproduzível. */
(function(root){
'use strict';
const VERSION='ufv-mobilidade-3.0.0';
const present=v=>v!==null&&v!==undefined&&v!==''&&v!=='NA';
const numeric=v=>typeof v==='number'&&Number.isFinite(v);
const median=a=>{a=a.filter(numeric).sort((x,y)=>x-y);return a.length?(a[(a.length-1)>>1]+a[a.length>>1])/2:null};
function rng(seed){return()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function keys(q){return q.type==='matrix'?q.modes.flatMap((_,m)=>q.items.map((_,i)=>`${q.id}_m${m+1}_i${i+1}`)):q.type==='scale'?q.items.map((_,i)=>`${q.id}_i${i+1}`):[q.id]}
function generate(schema,count=400,seed=956835){
 const rand=rng(seed),pick=a=>a[Math.floor(rand()*a.length)],by=Object.fromEntries(schema.questions.map(q=>[q.id,q])),records=[];
 for(let i=0;i<count;i++){
  const answers={},cyclist=rand()<.22,skill=rand()<.84;
  for(const q of schema.questions){
   if(q.type==='matrix'||q.type==='scale'){keys(q).forEach(k=>answers[k]=rand()<.08?'NA':1+Math.floor(rand()*5));continue;}
   if(q.type==='scenario')continue;
   if(q.type==='radio')answers[q.id]=pick(q.options);
   else if(q.type==='multi'){answers[q.id]=[pick(q.options)];}
   else if(q.type==='number')answers[q.id]=1+Math.floor(rand()*10);
   else if(q.type==='location')answers[q.id]={neighborhood:pick(['Setor sintético A','Setor sintético B','Setor sintético C','Setor sintético D'])};
   else if(q.type==='textarea')answers[q.id]=pick(['SIMULAÇÃO: melhorar a continuidade das rotas.','SIMULAÇÃO: oferecer local seguro para estacionar.','SIMULAÇÃO: aprender a pedalar com confiança.',null]);
   else answers[q.id]=q.id==='q14'?'Acesso fictício '+pick(['A','B','C']):'Destino fictício '+pick(['A','B','C']);
  }
  answers.q1='Sim';answers.q2=18+Math.floor(rand()*47);answers.q3=pick([by.q3.options[0],by.q3.options[0],...by.q3.options]);
  answers.q6=1+Math.floor(rand()*5);answers.q10=skill?pick(by.q10.options.slice(1)):by.q10.options[0];
  answers.q10a=skill?pick(by.q10a.options.slice(1,5)):by.q10a.options[0];
  answers.q16=cyclist?pick(by.q16.options.slice(1,3)):pick(['A pé','Carro, dirigindo','Ônibus','Ônibus','Moto, dirigindo','Carona de carro ou moto']);
  if(cyclist)answers.q10=by.q10.options[3];
  answers.q17=5+Math.floor(rand()*66);answers.q18=['A pé','Bicicleta comum'].includes(answers.q16)?0:Math.round(rand()*1600)/100;
  answers.q11a=by.q11a.options[0];answers.q12=pick(['2','3','4','5']);answers.q19=[answers.q16==='Ônibus'?'Ônibus':cyclist?answers.q16:'A pé'];
  answers.q37=['A pé','Bicicleta comum','Bicicleta elétrica'].includes(answers.q16)?null:answers.q37;
  answers.q41=cyclist?1+Math.floor(rand()*5):0;
  const infra=1+Math.floor(rand()*5),safety=Math.max(1,Math.min(5,Math.round(.55*infra+rand()*3)));
  for(let k=1;k<=3;k++){answers['q43_i'+k]=Math.max(1,Math.min(5,infra+Math.round(rand()*2-1)));answers['q44_i'+k]=Math.max(1,Math.min(5,safety+Math.round(rand()*2-1)));}
  answers.q42=by.q42.options[Math.max(0,Math.min(4,Math.round(.5*safety+(cyclist?1:0)+rand()*2-1)))];
  answers.q11={neighborhood:pick(['Setor sintético A','Setor sintético B','Setor sintético C','Setor sintético D']),point:{lat:Number((-20.75+(rand()-.5)*.05).toFixed(3)),lng:Number((-42.875+(rand()-.5)*.055).toFixed(3)),source:'synthetic',precision:'synthetic_only'}};
  for(let k=50;k<=63;k++)if(!(answers.q19||[]).includes(by['q'+k].alternative))answers['q'+k]=null;
  const tendency=(cyclist?.8:0)+(skill?.1:-1.2)+(rand()-.5)*1.5;
  schema.questions.filter(q=>q.type==='scenario').forEach((q,j)=>{
   const infrastructure=[0,0,0,.3,.3,.3,.85,.85,.85][j];
   const slope=[0,-.4,-.95,-.4,-.95,0,-.95,0,-.4][j];
   const utility=tendency+infrastructure+slope-(parseFloat(q.time)-10)*.045;
   answers[q.id]=rand()<.04?null:q.options[rand()<1/(1+Math.exp(-utility))?0:1];
  });
  Object.keys(answers).filter(k=>!['q1','q2'].includes(k)).forEach(k=>{if(rand()<.025)answers[k]=null});
  const order=schema.questions.filter(q=>q.type==='scenario').map(q=>q.id);for(let k=order.length-1;k>0;k--){const j=Math.floor(rand()*(k+1));[order[k],order[j]]=[order[j],order[k]];}
  const start=new Date(Date.UTC(2026,8,1+Math.floor(i/8),9+Math.floor(rand()*10),Math.floor(rand()*60)));
  records.push({schema_version:VERSION,response_id:`SIM-${seed}-${String(i+1).padStart(4,'0')}`,is_demo:true,is_synthetic:true,design_version:schema.design_version,tcle_version:'SIMULACAO-SEM-PARTICIPANTE',started_at:start.toISOString(),consented_at:start.toISOString(),completed_at:new Date(+start+300000+rand()*900000).toISOString(),scenario_order:order,answers});
 }
 return {format:'caminhos-ufv-dataset-v1',schema_version:VERSION,kind:'synthetic',seed,description:'Dados artificiais para testar interface e cálculos. Sem valor como evidência empírica.',records};
}
function validate(data,schema){
 const records=Array.isArray(data)?data:data?.records,errors=[],warnings=[],ids=new Set(),allowed=new Set(schema.questions.flatMap(q=>[...keys(q),...(q.other?[q.id+'_other']:[])]));
 if(!Array.isArray(records)||!records.length)return {ok:false,errors:['O arquivo precisa conter uma lista não vazia de respostas.'],warnings:[]};
 if(records.length>20000)return {ok:false,errors:['Limite de 20.000 participantes por arquivo.'],warnings:[]};
 records.forEach((r,i)=>{
  const tag=`Registro ${i+1}`;
  if(r.schema_version!==VERSION)errors.push(`${tag}: versão incompatível. Não misture a versão antiga com a atual.`);
  if(typeof r.response_id!=='string'||!r.response_id||r.response_id.length>100)errors.push(`${tag}: código inválido.`);
  if(ids.has(r.response_id))errors.push(`${tag}: código duplicado.`);ids.add(r.response_id);
  if(typeof r.is_synthetic!=='boolean'||typeof r.is_demo!=='boolean')errors.push(`${tag}: informe is_synthetic e is_demo como booleanos.`);
  if(r.is_synthetic&&!r.is_demo)errors.push(`${tag}: simulação precisa estar marcada como demonstração.`);
  if(!r.answers||Array.isArray(r.answers)||typeof r.answers!=='object'){errors.push(`${tag}: answers inválido.`);return;}
  if(r.answers.q1!=='Sim'||!Number.isInteger(r.answers.q2)||r.answers.q2<18||r.answers.q2>120)errors.push(`${tag}: consentimento ou idade inválidos.`);
  if(!Number.isFinite(Date.parse(r.completed_at)))errors.push(`${tag}: data de conclusão inválida.`);
  for(const [k,v] of Object.entries(r.answers))if(!allowed.has(k))errors.push(`${tag}: campo desconhecido ${k}.`);
  for(const q of schema.questions){for(const k of keys(q)){
   const v=r.answers[k];if(v===null||v===undefined||v==='')continue;
   if(['matrix','scale'].includes(q.type)){if(v!=='NA'&&(!Number.isInteger(v)||v<1||v>5))errors.push(`${tag}: escala inválida em ${k}.`);}
   else if(q.type==='number'&&(!numeric(v)||v<q.min||(q.max&&v>q.max)||(q.step===1&&!Number.isInteger(v))))errors.push(`${tag}: número inválido em ${k}.`);
   else if(['radio','scenario'].includes(q.type)&&!q.options.includes(v))errors.push(`${tag}: alternativa inválida em ${k}.`);
   else if(q.type==='multi'&&(!Array.isArray(v)||v.some(x=>!q.options.includes(x))||new Set(v).size!==v.length||(q.limit&&v.length>q.limit)||(v.length>1&&v.some(x=>q.exclusive?.includes(x)))))errors.push(`${tag}: seleção múltipla inválida em ${k}.`);
   else if(['text','textarea'].includes(q.type)&&(typeof v!=='string'||v.length>(q.type==='text'?250:2000)))errors.push(`${tag}: texto inválido em ${k}.`);
   else if(q.type==='location'){if(typeof v!=='object'||Array.isArray(v)){errors.push(`${tag}: localização inválida.`);continue;}if(v.point&&(!numeric(v.point.lat)||!numeric(v.point.lng)||Math.abs(v.point.lat)>90||Math.abs(v.point.lng)>180))errors.push(`${tag}: coordenadas inválidas.`);}
  }}
 });
 const kinds=new Set(records.map(r=>r.is_synthetic?'synthetic':r.is_demo?'demo':'real'));
 if(kinds.size>1)errors.push('O arquivo mistura dados reais, testes ou simulações. Separe as bases antes de importar.');
 if(records.length<30)warnings.push('Base pequena: comparações e modelos podem ser instáveis.');
 return {ok:errors.length===0,errors:errors.slice(0,30),warnings,records,kind:[...kinds][0]};
}
function frequency(rows,key){const map=new Map();let valid=0;for(const r of rows){const v=r.answers[key];if(!present(v))continue;valid++;(Array.isArray(v)?v:[v]).forEach(x=>map.set(String(x),(map.get(String(x))||0)+1));}return {valid,missing:rows.length-valid,items:[...map].map(([label,n])=>({label,n,pct:valid?100*n/valid:0})).sort((a,b)=>b.n-a.n)}}
function summarize(rows,schema){const modes=frequency(rows,'q16'),active=rows.filter(r=>['A pé','Bicicleta comum','Bicicleta elétrica'].includes(r.answers.q16)).length;let chosen=0,tasks=0;for(const q of schema.questions.filter(q=>q.type==='scenario'))for(const r of rows){const v=r.answers[q.id];if(q.options.includes(v)){tasks++;if(v===q.options[0])chosen++;}}return {n:rows.length,modes,active: modes.valid?100*active/modes.valid:null,time:median(rows.map(r=>r.answers.q17)),cost:median(rows.map(r=>r.answers.q18)),tasks,chosen,stated:tasks?100*chosen/tasks:null};}
function csv(rows){const columns=['schema_version','response_id','is_demo','is_synthetic','design_version','tcle_version','started_at','consented_at','completed_at','scenario_order','answers'];const cell=v=>'"'+String(v??'').replace(/"/g,'""')+'"';return '\ufeff'+[columns.join(','),...rows.map(r=>columns.map(k=>cell(typeof r[k]==='object'?JSON.stringify(r[k]):r[k])).join(','))].join('\r\n')}
function parseCSV(text){text=text.replace(/^\ufeff/,'');const rows=[];let row=[],value='',quote=false;for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quote&&text[i+1]==='"'){value+='"';i++;}else quote=!quote;}else if(c===','&&!quote){row.push(value);value='';}else if((c==='\n'||c==='\r')&&!quote){if(c==='\r'&&text[i+1]==='\n')i++;row.push(value);if(row.some(Boolean))rows.push(row);row=[];value='';}else value+=c;}if(quote)throw Error('CSV com aspas sem fechamento.');if(value||row.length){row.push(value);rows.push(row);}const header=rows.shift();if(!header?.includes('answers'))throw Error('Use o CSV exportado pelo painel, com a coluna answers em JSON.');return rows.map((a,i)=>{if(a.length!==header.length)throw Error('Número de colunas divergente na linha '+(i+2));const r=Object.fromEntries(header.map((k,j)=>[k,a[j]]));r.answers=JSON.parse(r.answers);r.scenario_order=JSON.parse(r.scenario_order||'[]');for(const k of ['is_demo','is_synthetic']){if(!['true','false'].includes(r[k]))throw Error(k+' inválido');r[k]=r[k]==='true';}return r;});}
// Logit binário exploratório dos pacotes declarados; ridge fixo, sem p-valores.
function scenarioModel(rows,schema){
 const qs=schema.questions.filter(q=>q.type==='scenario'),x=[],y=[],people=new Set();
 const roads=[...new Set(qs.map(q=>q.road))],slopes=[...new Set(qs.map(q=>q.slope))],bikes=[...new Set(qs.map(q=>q.bike))];
 for(const r of rows)for(const q of qs)if(q.options.includes(r.answers[q.id])){people.add(r.response_id);x.push([1,(parseFloat(q.time)-15)/5,...roads.slice(1).map(v=>+(q.road===v)),...slopes.slice(1).map(v=>+(q.slope===v)),...bikes.slice(1).map(v=>+(q.bike===v))]);y.push(+(r.answers[q.id]===q.options[0]));}
 if(people.size<30||y.reduce((a,b)=>a+b,0)<20||y.filter(v=>v===0).length<20)return {error:'Para ajustar este modelo exploratório, são necessários ao menos 30 participantes e 20 escolhas em cada alternativa.'};
 const fit=(xx,yy)=>{let b=Array(xx[0].length).fill(0);for(let t=0;t<900;t++){const g=b.map((v,j)=>j?.02*v:0);for(let i=0;i<xx.length;i++){const z=xx[i].reduce((s,v,j)=>s+v*b[j],0),e=1/(1+Math.exp(-Math.max(-30,Math.min(30,z))))-yy[i];xx[i].forEach((v,j)=>g[j]+=e*v/xx.length);}b=b.map((v,j)=>v-.35*g[j]);}return b;};
 const beta=fit(x,y);return {people:people.size,tasks:y.length,coefficients:['Intercepto','Tempo: +5 minutos',...roads.slice(1).map(v=>'Via: '+v),...slopes.slice(1).map(v=>'Relevo: '+v),...bikes.slice(1).map(v=>'Pacote: '+v)].map((label,i)=>({label,beta:beta[i],odds:Math.exp(beta[i])})),reference:[roads[0],slopes[0],bikes[0]].join(' · '),note:'Regressão logística com penalização L2 fixa (0,02), sem intervalos ou testes de hipótese. Respostas repetidas por pessoa: não interpretar o número de tarefas como amostra independente. O ajuste é descritivo; para inferência usar modelo de painel ou incerteza agrupada por participante. Preço e bicicleta são um pacote, sem estimativa de disposição a pagar.'};
}
function modalModel(rows,schema){
 const records=rows.filter(r=>present(r.answers.q16)&&numeric(r.answers.q2)),by=Object.fromEntries(schema.questions.map(q=>[q.id,q]));
 const counts=frequency(records,'q16').items,classes=counts.filter(v=>v.n>=20).map(v=>v.label);
 if(classes.length<2)return {error:'São necessárias ao menos duas categorias de transporte com 20 participantes cada. Categorias raras não são agrupadas automaticamente.'};
 const eligible=records.filter(r=>classes.includes(r.answers.q16)),random=rng(8421264),ordered=eligible.map(r=>({r,u:random()})).sort((a,b)=>a.u-b.u).map(v=>v.r);
 const train=[],test=[];for(const c of classes){const group=ordered.filter(r=>r.answers.q16===c),cut=Math.floor(group.length*.8);train.push(...group.slice(0,cut));test.push(...group.slice(cut));}
 const catIds=['q3','q5','q10'],featureNames=['Intercepto','Idade (+10 anos)',...catIds.flatMap(id=>by[id].options.slice(1).map(o=>id+': '+o)),...by.q9.options.filter(v=>v!=='Nenhum').map(v=>'Disponibilidade: '+v)];
 const vector=r=>[1,(r.answers.q2-30)/10,...catIds.flatMap(id=>by[id].options.slice(1).map(o=>+(r.answers[id]===o))),...by.q9.options.filter(v=>v!=='Nenhum').map(v=>+(r.answers.q9||[]).includes(v))];
 const usable=r=>catIds.every(id=>by[id].options.includes(r.answers[id]))&&Array.isArray(r.answers.q9),tr=train.filter(usable),te=test.filter(usable);
 if(te.length<15||tr.length<60||classes.some(c=>tr.filter(r=>r.answers.q16===c).length<10))return {error:'Faltam casos completos para treino e teste após excluir valores ausentes dos preditores.'};
 const xx=tr.map(vector),yy=tr.map(r=>classes.indexOf(r.answers.q16)),K=classes.length,P=xx[0].length,W=Array.from({length:K},()=>Array(P).fill(0));
 const probs=x=>{const z=W.map(w=>w.reduce((s,v,j)=>s+v*x[j],0)),m=Math.max(...z),e=z.map(v=>Math.exp(v-m)),sum=e.reduce((a,b)=>a+b);return e.map(v=>v/sum)};
 for(let step=0;step<550;step++){const g=W.map(w=>w.map((v,j)=>j?.025*v:0));xx.forEach((x,i)=>{const p=probs(x);for(let k=0;k<K;k++)for(let j=0;j<P;j++)g[k][j]+=(p[k]-+(yy[i]===k))*x[j]/xx.length;});for(let k=0;k<K;k++)for(let j=0;j<P;j++)W[k][j]-=.22*g[k][j];}
 const cm=Array.from({length:K},()=>Array(K).fill(0)),trainCounts=classes.map(c=>tr.filter(r=>r.answers.q16===c).length),baseClass=trainCounts.indexOf(Math.max(...trainCounts));let loss=0,baseCorrect=0,baseLoss=0;
 te.forEach(r=>{const p=probs(vector(r)),actual=classes.indexOf(r.answers.q16),pred=p.indexOf(Math.max(...p));cm[actual][pred]++;loss-=Math.log(Math.max(p[actual],1e-12));baseLoss-=Math.log(trainCounts[actual]/tr.length);baseCorrect+=+(actual===baseClass);});
 const perClass=classes.map((label,k)=>{const support=cm[k].reduce((a,b)=>a+b),pred=cm.reduce((s,row)=>s+row[k],0),recall=support?cm[k][k]/support:0,precision=pred?cm[k][k]/pred:0;return {label,support,recall,precision,f1:precision+recall?2*precision*recall/(precision+recall):0}});
 return {train:tr.length,test:te.length,excluded:rows.length-tr.length-te.length,classes,confusion:cm,perClass,accuracy:cm.reduce((s,row,k)=>s+row[k],0)/te.length,balancedAccuracy:perClass.reduce((s,v)=>s+v.recall,0)/K,macroF1:perClass.reduce((s,v)=>s+v.f1,0)/K,logloss:loss/te.length,baselineAccuracy:baseCorrect/te.length,baselineLogloss:baseLoss/te.length,features:featureNames.slice(1),note:'Classificador multinomial (softmax) com penalização L2=0,025. Divisão estratificada 80/20 por participante, semente 8421264; treinamento em 550 passos, sem seleção de hiperparâmetros no teste. Não é um modelo de utilidade com atributos de todas as alternativas. Acurácia avalia classificação do modo relatado, não adoção futura. Despesas e tempo do modo escolhido não são usados como preditores, evitando uma comparação circular.'};
}
root.UFV={VERSION,present,numeric,median,rng,keys,generate,validate,frequency,summarize,csv,parseCSV,scenarioModel,modalModel};
})(globalThis);

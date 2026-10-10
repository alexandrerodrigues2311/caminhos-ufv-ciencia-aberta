"""Analysis for the revised UFV questionnaire. No cross-version recoding."""
import os,json,hashlib,hmac,base64,time,warnings
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.model_selection import StratifiedKFold
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import balanced_accuracy_score,roc_auc_score,brier_score_loss,log_loss
SEED=8421264
VERSION='ufv-mobilidade-4.2.0'

def clean(v):
 if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
 if isinstance(v,(np.integer,)):return int(v)
 if isinstance(v,(float,np.floating)):return float(v) if np.isfinite(v) else None
 return v

def frame(records):
 rows=[]
 for r in records:
  a=r['answers'];choice=a.get('qChange')
  rows.append(dict(id=r['response_id'],target=int(choice.startswith('Sim')) if isinstance(choice,str) else np.nan,age=a.get('q2'),role=a.get('q3'),income=a.get('q5'),housing=a.get('qHousing'),skill=a.get('q10'),mode=a.get('q16')))
 return pd.DataFrame(rows).replace({None:np.nan})

def ml(records):
 df=frame(records).dropna(subset=['target']);y=df.target.astype(int).to_numpy();counts=pd.Series(y).value_counts()
 if len(df)<80 or len(counts)!=2 or counts.min()<20:raise ValueError('ML requer 80 respostas válidas e pelo menos 20 em cada classe de disposição para mudança.')
 cols=['age','role','income','housing','skill','mode'];X=df[cols]
 pre=ColumnTransformer([('numeric',Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True,add_indicator=True)),('scale',StandardScaler())]),['age']),('categories',Pipeline([('impute',SimpleImputer(strategy='constant',fill_value='Sem resposta')),('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),cols[1:])])
 models={'Referência de prevalência':DummyClassifier(strategy='prior'),'Regressão logística':LogisticRegression(C=1,max_iter=1500,random_state=SEED),'Random forest':RandomForestClassifier(n_estimators=100,max_depth=4,min_samples_leaf=10,random_state=SEED,n_jobs=1)}
 folds=list(StratifiedKFold(5,shuffle=True,random_state=SEED).split(X,y));out=[]
 for name,model in models.items():
  pred=np.zeros(len(df));scores=[]
  for train,test in folds:
   pipe=Pipeline([('preparation',pre),('model',model)]);pipe.fit(X.iloc[train],y[train]);p=pipe.predict_proba(X.iloc[test])[:,1];pred[test]=p;scores.append(balanced_accuracy_score(y[test],p>=.5))
  out.append(dict(model=name,n=len(df),balanced_accuracy=balanced_accuracy_score(y,pred>=.5),auc=roc_auc_score(y,pred),brier=brier_score_loss(y,pred),log_loss=log_loss(y,pred),fold_balanced_accuracy=scores))
 return dict(target='qChange: Sim versus Não; disposição autorrelatada, não mudança observada',n=len(df),excluded=len(records)-len(df),class_counts=counts.to_dict(),models=out,interpretation='Compare cada modelo com a referência de prevalência. Desempenho em validação interna não demonstra transportabilidade, causalidade ou utilidade operacional. Hiperparâmetros fixados; sem busca no conjunto de teste. qChance, qBarriers e cenários não entram nos preditores para evitar dependência do desfecho.')

def scenarios(records):
 rows=[]
 for r in records:
  a=r['answers'];current=a.get('q16')
  if not current:continue
  for i in range(1,7):
   value=a.get('qSituation'+str(i))
   if value is not None:rows.append(dict(id=r['response_id'],scenario=str(i),change=int(not value.startswith('Continuaria') and value!=current)))
 df=pd.DataFrame(rows)
 if df.empty or df.id.nunique()<40 or df.change.nunique()<2:raise ValueError('Cenários requerem 40 participantes com respostas e variação nas escolhas.')
 counts=df.groupby('scenario').change.agg(['count','sum']);
 if len(counts)<6 or (counts['sum']<5).any() or ((counts['count']-counts['sum'])<5).any():raise ValueError('Cada cenário precisa de pelo menos cinco respostas em cada categoria binária.')
 fit=smf.gee('change ~ C(scenario)',groups='id',data=df,family=sm.families.Binomial(),cov_struct=sm.cov_struct.Exchangeable()).fit()
 if not getattr(fit,'converged',True):raise ValueError('GEE não convergiu.')
 ci=fit.conf_int();terms=[dict(term=k,log_odds=fit.params[k],odds_ratio=np.exp(fit.params[k]),ci_low=np.exp(ci.loc[k,0]),ci_high=np.exp(ci.loc[k,1]),p=fit.pvalues[k]) for k in fit.params.index]
 return dict(participants=df.id.nunique(),observations=len(df),terms=terms,by_scenario=counts.reset_index().to_dict('records'),interpretation='Contrastes associativos entre situações, em relação à situação 1, com correlação das respostas da mesma pessoa e variância robusta. A escolha foi reduzida a mudança versus manutenção; a distribuição original por alternativa deve acompanhar o resultado. Não são efeitos causais nem elasticidades.')

def moderation(records):
 df=frame(records).dropna(subset=['target','age','skill','mode']);df['knows_cycle']=(~df.skill.str.startswith('Não')).astype(int);df['active_mode']=df['mode'].isin(['A pé','Bicicleta comum','Bicicleta ou patinete elétrico']).astype(int);df['age10']=(df.age-30)/10
 counts=df.groupby(['knows_cycle','active_mode','target']).size()
 if len(df)<100 or len(counts)!=8 or counts.min()<5:raise ValueError('Interação requer 100 casos completos e pelo menos cinco casos por célula habilidade × modo × desfecho.')
 fit=smf.logit('target ~ knows_cycle * active_mode + age10',data=df).fit(disp=False,maxiter=150)
 if not fit.mle_retvals.get('converged'):raise ValueError('Modelo de interação não convergiu.')
 ci=fit.conf_int();terms=[dict(term=k,odds_ratio=np.exp(fit.params[k]),ci_low=np.exp(ci.loc[k,0]),ci_high=np.exp(ci.loc[k,1]),p=fit.pvalues[k]) for k in fit.params.index]
 return dict(n=len(df),excluded=len(records)-len(df),terms=terms,interpretation='Interação exploratória na escala logit entre saber pedalar (q10) e modo ativo atual, ajustada apenas por idade. q10 combina habilidade e frequência; não mede uma competência latente validada. A interação não prova moderação causal. Confundimento por vínculo e renda ainda precisa ser avaliado no plano final.')

def run(payload):
 records=payload.get('records',[])
 if not isinstance(records,list) or not 1<=len(records)<=2000:raise ValueError('Selecione entre 1 e 2.000 registros.')
 if any(r.get('schema_version')!=VERSION or not isinstance(r.get('answers'),dict) for r in records):raise ValueError('Use exclusivamente o instrumento '+VERSION)
 ids=[r.get('response_id') for r in records]
 if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):raise ValueError('Identificadores inválidos ou duplicados.')
 if any(r.get('is_demo') not in [True,False] or r.get('is_synthetic') not in [True,False] or (r.get('is_synthetic') and not r.get('is_demo')) for r in records):raise ValueError('Tipo de base inválido.')
 kinds={('synthetic' if r.get('is_synthetic') else 'demo' if r.get('is_demo') else 'real') for r in records}
 if len(kinds)!=1:raise ValueError('Separe simulação, teste e coleta real.')
 if any(r['answers'].get('q1')!='Sim' or not isinstance(r['answers'].get('q2'),int) or not 18<=r['answers']['q2']<=120 for r in records):raise ValueError('Verifique consentimento e idade.')
 schema=json.loads((Path(__file__).resolve().parent.parent/'public'/'questionario-v4.schema.json').read_text(encoding='utf-8-sig'))
 for r in records:
  a=r['answers']
  for q in schema['questions']:
   v=a.get(q['id']);condition=q.get('when')
   if condition:
    parent=a.get(condition['id']);visible=isinstance(parent,str) and parent.startswith(condition['prefix']) if 'prefix' in condition else parent==condition.get('value')
    if not visible and v is not None:raise ValueError('Resposta condicional incompatível: '+q['id'])
   if v is None:continue
   if q['type']=='radio' and v not in q['options']:raise ValueError('Alternativa inválida: '+q['id'])
   if q['type']=='multi' and (not isinstance(v,list) or any(x not in q['options'] for x in v) or len(v)!=len(set(v)) or len(v)>q.get('limit',len(q['options']))):raise ValueError('Seleção inválida: '+q['id'])
   if q['type']=='number' and (not isinstance(v,int) or isinstance(v,bool) or v<q.get('min',0) or v>q.get('max',1000000)):raise ValueError('Número inválido: '+q['id'])
 method=payload.get('method');methods={'ml':ml,'scenarios':scenarios,'moderation':moderation}
 if method not in methods:raise ValueError('Método indisponível. Mediação causal não é identificada pelo desenho atual.')
 result=methods[method](records)
 return clean(dict(method=method,version=VERSION,kind=next(iter(kinds)),seed=SEED,result=result,fingerprint=hashlib.sha256(json.dumps(records,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),warning='DADOS FICTÍCIOS: resultados exclusivos para demonstração.' if kinds=={'synthetic'} else 'Associações da amostra; não implicam causalidade ou representatividade.'))

class handler(BaseHTTPRequestHandler):
 def do_POST(self):
  try:
   if self.headers.get('Origin','').split('://')[-1]!=self.headers.get('Host'):return self.reply(403,{'error':'Origem não autorizada.'})
   size=int(self.headers.get('Content-Length',0))
   if size>3500000:return self.reply(413,{'error':'Base muito extensa.'})
   p=json.loads(self.rfile.read(size));records=p.get('records',[])
   if os.environ.get('COLLECTION_RELEASED')=='true' or any(not r.get('is_demo') for r in records):
    cookies=dict(x.strip().split('=',1) for x in self.headers.get('Cookie','').split(';') if '=' in x);body,sig=cookies.get('ufv_admin','').split('.')
    secret=os.environ.get('SESSION_SECRET','')
    if len(secret)<32:raise ValueError('Sessão não configurada.')
    expected=base64.urlsafe_b64encode(hmac.new(secret.encode(),body.encode(),hashlib.sha256).digest()).decode().rstrip('=')
    data=json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
    if not hmac.compare_digest(sig,expected) or data.get('exp',0)<time.time()*1000 or data.get('role')!='admin':return self.reply(401,{'error':'Entre novamente na administração.'})
   self.reply(200,run(p))
  except ValueError as e:self.reply(400,{'error':str(e)})
  except FileNotFoundError:self.reply(503,{'error':'O esquema do questionário não foi incluído no ambiente de análise.'})
  except Exception as e:
   print(json.dumps({'analysis_error_type':type(e).__name__}),flush=True)
   self.reply(422,{'error':'O ajuste falhou. Verifique casos válidos, variação e categorias do recorte.'})
 def reply(self,status,value):
  self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(json.dumps(value,ensure_ascii=False,allow_nan=False).encode())
 def log_message(self,*args):pass
if __name__=='__main__':
 import sys
 print(json.dumps(run(json.load(sys.stdin)),ensure_ascii=False,allow_nan=False))

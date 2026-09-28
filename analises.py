"""Análises reproduzíveis. Sem gravação de respostas ou coordenadas em logs."""
import json,math,warnings,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import rankdata
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier,GradientBoostingClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import balanced_accuracy_score,f1_score,log_loss,brier_score_loss,confusion_matrix
import statsmodels.api as sm

SEED=8421264
def clean(v):
 if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple,np.ndarray)):return [clean(x) for x in v]
 if isinstance(v,(np.integer,)):return int(v)
 if isinstance(v,(float,np.floating)):return float(v) if np.isfinite(v) else None
 return v
def score(a):
 return float(a) if isinstance(a,(int,float)) and not isinstance(a,bool) and np.isfinite(a) else np.nan
def meanitems(a,q):
 vals=[score(a.get(f'{q}_i{i}')) for i in [1,2,3]]
 return float(np.mean(vals)) if all(np.isfinite(vals)) else np.nan
def frames(records):
 conf=['Nada confiante','Pouco confiante','Moderadamente confiante','Muito confiante','Totalmente confiante']
 intent=['Muito baixa','Baixa','Moderada','Alta','Muito alta']
 rows=[]
 for r in records:
  a=r['answers'];rows.append(dict(id=r['response_id'],age=score(a.get('q2')),role=a.get('q3'),income=a.get('q5'),skill=a.get('q10'),confidence=conf.index(a['q10a'])+1 if a.get('q10a') in conf else np.nan,infra=meanitems(a,'q43'),safety=meanitems(a,'q44'),intent=intent.index(a['q42'])+1 if a.get('q42') in intent else np.nan,days=score(a.get('q41')),mode=a.get('q16')))
 return pd.DataFrame(rows)
def ml(records):
 df=frames(records).dropna(subset=['mode']);df=df[df['mode']!=''];df['target']=df['mode'].isin(['Bicicleta comum','Bicicleta elétrica']).astype(int)
 if len(df)<80 or df.target.value_counts().min()<20 or df.target.nunique()<2:raise ValueError('ML: são necessários 80 casos e pelo menos 20 pessoas por classe.')
 numeric=['age','confidence','infra','safety'];categorical=['role','income','skill'];cols=numeric+categorical
 X=df[cols].copy().replace({None:np.nan});y=df.target.to_numpy();groups=df.id.to_numpy()
 pre=ColumnTransformer([('num',Pipeline([('impute',SimpleImputer(strategy='median',add_indicator=True)),('scale',StandardScaler())]),numeric),('cat',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('encode',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),categorical)])
 models={'Referência de prevalência':DummyClassifier(strategy='prior'),'Logística regularizada':LogisticRegression(C=1,max_iter=1000,random_state=SEED),'Random forest':RandomForestClassifier(n_estimators=100,max_depth=4,min_samples_leaf=8,random_state=SEED,n_jobs=1),'Gradient boosting':GradientBoostingClassifier(n_estimators=60,max_depth=2,min_samples_leaf=10,learning_rate=.05,random_state=SEED)}
 folds=list(StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=SEED).split(X,y,groups));out=[]
 for name,model in models.items():
  prob=np.zeros(len(df));fold_metrics=[]
  for train,test in folds:
   if set(groups[train])&set(groups[test]):raise ValueError('Vazamento entre participantes detectado.')
   pipe=Pipeline([('prepare',pre),('model',model)]);pipe.fit(X.iloc[train],y[train]);prob[test]=pipe.predict_proba(X.iloc[test])[:,1]
   fold_metrics.append(float(balanced_accuracy_score(y[test],prob[test]>=.5)))
  pred=prob>=.5;cal=[]
  for low in np.arange(0,1,.2):
   ix=(prob>=low)&(prob<low+.2 if low<.8 else prob<=1)
   if ix.sum():cal.append(dict(predicted=float(prob[ix].mean()),observed=float(y[ix].mean()),n=int(ix.sum())))
  out.append(dict(model=name,balanced_accuracy=balanced_accuracy_score(y,pred),macro_f1=f1_score(y,pred,average='macro'),log_loss=log_loss(y,prob,labels=[0,1]),brier=brier_score_loss(y,prob),confusion=confusion_matrix(y,pred,labels=[0,1]).tolist(),fold_balanced=fold_metrics,calibration=cal))
 best=min(out[1:],key=lambda v:v['log_loss']);base=out[0]
 return dict(n=len(df),excluded=len(records)-len(df),target='Bicicleta comum ou elétrica no modo atual versus outros meios',features=cols,folds=5,models=out,interpretation=f"O menor log loss entre os modelos candidatos foi obtido por {best['model']}. "+('Superou' if best['log_loss']<base['log_loss'] else 'Não superou')+' a referência de prevalência neste conjunto. A seleção pelo mesmo desempenho de validação é exploratória; requer confirmação em amostra independente.',note='Hiperparâmetros fixados antes do ajuste; imputação e codificação dentro de cada dobra. Dias de uso e intenção foram excluídos dos preditores para evitar proximidade excessiva com o alvo. Não prevê adoção futura. Dispersão entre dobras não é intervalo de confiança.')
def mediation(records,boot=500):
 d=frames(records).dropna(subset=['age','infra','safety','intent']);n=len(d)
 if n<80:raise ValueError('Mediação: são necessários 80 casos completos nos blocos de infraestrutura, segurança, intenção e idade.')
 x=d.infra.to_numpy();m=d.safety.to_numpy();y=d.intent.to_numpy();age=(d.age.to_numpy()-30)/10
 def fit(ix,rank=False):
  xx=x[ix];mm=m[ix];yy=rankdata(y[ix]) if rank else y[ix];aa=age[ix]
  A=np.column_stack([np.ones(len(ix)),xx,aa]);B=np.column_stack([np.ones(len(ix)),xx,mm,aa]);C=np.column_stack([np.ones(len(ix)),xx,aa])
  if np.linalg.matrix_rank(A)<3 or np.linalg.matrix_rank(B)<4:raise ValueError('Sem variação suficiente para mediação.')
  a=np.linalg.lstsq(A,mm,rcond=None)[0][1];b=np.linalg.lstsq(B,yy,rcond=None)[0];total=np.linalg.lstsq(C,yy,rcond=None)[0][1]
  return np.array([a,b[2],a*b[2],b[1],total])
 values=fit(np.arange(n));rng=np.random.default_rng(SEED);draw=[]
 for _ in range(boot):
  try:draw.append(fit(rng.integers(0,n,n)))
  except ValueError:pass
 if len(draw)<boot*.9:raise ValueError('Mediação instável nas reamostragens. Amplie ou revise o recorte.')
 ci=np.percentile(draw,[2.5,97.5],axis=0)
 estimates=[dict(term=term,estimate=values[j],low=ci[0,j],high=ci[1,j]) for j,term in enumerate(['a: infraestrutura → segurança','b: segurança → intenção','Associação indireta a×b','Associação direta','Associação total'])]
 return dict(n=n,excluded=len(records)-n,bootstrap=len(draw),estimates=estimates,rank_sensitivity_indirect=fit(np.arange(n),True)[2],note='Regressões lineares exploratórias dos escores médios completos q43 e q44 e intenção ordinal q42, ajustadas por idade. Bootstrap por pessoa. q43 é um resumo de componentes, não uma escala latente validada. A sensibilidade por postos usa outra unidade e serve para conferir o sinal. Dados transversais não identificam mediação causal; confundimento, seleção e temporalidade permanecem.',interpretation='O intervalo da associação indireta '+('inclui zero; não há direção estatisticamente definida neste ajuste.' if ci[0,2]<=0<=ci[1,2] else 'não inclui zero neste ajuste exploratório. Isso não comprova mecanismo causal.'))
def panel(records,schema):
 df=frames(records).set_index('id');qs=[q for q in schema['questions'] if q['type']=='scenario'];roads=list(dict.fromkeys(q['road'] for q in qs));slopes=list(dict.fromkeys(q['slope'] for q in qs));bikes=list(dict.fromkeys(q['bike'] for q in qs));rows=[]
 for r in records:
  c=df.loc[r['response_id'],'confidence']
  if not np.isfinite(c):continue
  for q in qs:
   v=r['answers'].get(q['id'])
   if v not in q['options']:continue
   row=dict(id=r['response_id'],choice=int(v==q['options'][0]),time=(float(q['time'].split()[0])-15)/5,confidence=c-3)
   for i,label in enumerate(roads[1:]):row[f'via_{i+1}']=int(q['road']==label)
   for i,label in enumerate(slopes[1:]):row[f'relevo_{i+1}']=int(q['slope']==label)
   for i,label in enumerate(bikes[1:]):row[f'pacote_{i+1}']=int(q['bike']==label)
   row['via_x_confianca']=row.get('via_2',row.get('via_1',0))*(c-3);rows.append(row)
 d=pd.DataFrame(rows)
 if d.empty or d.id.nunique()<60 or d.choice.nunique()<2 or d.choice.value_counts().min()<30:raise ValueError('Painel: são necessários 60 participantes e 30 escolhas em cada alternativa.')
 x=sm.add_constant(d.drop(columns=['id','choice']).astype(float),has_constant='add')
 if np.linalg.matrix_rank(x)<x.shape[1]:raise ValueError('O desenho não identifica todos os termos neste recorte.')
 with warnings.catch_warnings():
  warnings.simplefilter('ignore');fit=sm.GEE(d.choice,x,groups=d.id,family=sm.families.Binomial(),cov_struct=sm.cov_struct.Exchangeable()).fit(maxiter=100)
 if not fit.converged or not np.isfinite(fit.params).all() or not np.isfinite(fit.bse).all():raise ValueError('GEE não convergiu de forma estável. Revise o recorte.')
 ci=fit.conf_int();terms=[dict(term=k,beta=fit.params[k],low=ci.loc[k,0],high=ci.loc[k,1],odds=np.exp(fit.params[k])) for k in x.columns]
 # Probabilidades padronizadas com demais atributos fixos nas linhas observadas.
 preds=[]
 for c in [-2,0,2]:
  for road in [0,1]:
   xx=x.copy();xx['confidence']=c
   for col in [v for v in xx.columns if v.startswith('via_') and v!='via_x_confianca']:xx[col]=0
   xx['via_2' if 'via_2' in xx else 'via_1']=road;xx['via_x_confianca']=road*c
   preds.append(dict(confidence=c+3,protected=road,probability=float(fit.predict(xx).mean())))
 return dict(people=d.id.nunique(),tasks=len(d),coefficients=terms,predictions=preds,working_correlation=float(fit.cov_struct.dep_params),references=dict(road=roads[0],slopes=slopes,bikes=bikes,roads=roads),note='GEE logístico marginal com correlação de trabalho permutável e covariância robusta por participante. Não é mixed logit e não estima distribuição de preferências. Interação pré-especificada entre a terceira categoria de via e confiança (q10a). Preço e bicicleta seguem pacotes do desenho original; não há disposição a pagar isolada.',interpretation='A interação descreve diferenças na associação entre via e escolha conforme a confiança. Compare probabilidades padronizadas; não interprete odds ratio como variação percentual direta da probabilidade.')
def run(payload):
 records=payload.get('records',[])
 if not isinstance(records,list) or not 1<=len(records)<=2000:raise ValueError('Selecione entre 1 e 2.000 participantes.')
 ids=[r.get('response_id') for r in records]
 if len(set(ids))!=len(ids):raise ValueError('Códigos duplicados: análise interrompida.')
 if any(r.get('schema_version')!='ufv-mobilidade-3.0.0' or not isinstance(r.get('answers'),dict) for r in records):raise ValueError('Use exclusivamente a versão 3 do instrumento.')
 kinds={('synthetic' if r.get('is_synthetic') else 'demo' if r.get('is_demo') else 'real') for r in records}
 if len(kinds)!=1:raise ValueError('Separe dados reais e testes.')
 method=payload.get('method');schema={'questions': [{'id': 'q28', 'number': 28, 'type': 'scenario', 'title': 'Como você viria ao campus nesta situação?', 'road': 'Na rua, junto com os carros', 'time': '10 min', 'slope': 'Plano', 'bike': 'Própria (ou emprestada) – grátis', 'options': ['Bicicleta nas condições apresentadas', 'Manteria meu deslocamento habitual'], 'hint': 'Os atributos descrevem um pacote. O custo se refere a uma ida. A manutenção do deslocamento habitual inclui as condições já relatadas.'}, {'id': 'q29', 'number': 29, 'type': 'scenario', 'title': 'Como você viria ao campus nesta situação?', 'road': 'Na rua, junto com os carros', 'time': '15 min', 'slope': 'Subidas moderadas', 'bike': 'Compartilhada comum – R$ 1,00', 'options': ['Bicicleta nas condições apresentadas', 'Manteria meu deslocamento habitual'], 'hint': 'Os atributos descrevem um pacote. O custo se refere a uma ida. A manutenção do deslocamento habitual inclui as condições já relatadas.'}, {'id': 'q30', 'number': 30, 'type': 'scenario', 'title': 'Como você viria ao campus nesta situação?', 'road': 'Na rua, junto com os carros', 'time': '20 min', 'slope': 'Subidas fortes', 'bike': 'Compartilhada elétrica – R$ 2,00', 'options': ['Bicicleta nas condições apresentadas', 'Manteria meu deslocamento habitual'], 'hint': 'Os atributos descrevem um pacote. O custo se refere a uma ida. A manutenção do deslocamento habitual inclui as condições já relatadas.'}, {'id': 'q31', 'number': 31, 'type': 'scenario', 'title': 'Como você viria ao campus nesta situação?', 'road': 'Ciclofaixa pintada', 'time': '10 min', 'slope': 'Subidas moderadas', 'bike': 'Compartilhada elétrica – R$ 2,00', 'options': ['Bicicleta nas condições apresentadas', 'Manteria meu deslocamento habitual'], 'hint': 'Os atributos descrevem um pacote. O custo se refere a uma ida. A manutenção do deslocamento habitual inclui as condições já relatadas.'}, {'id': 'q32', 'number': 32, 'type': 'scenario', 'title': 'Como você viria ao campus nesta situação?', 'road': 'Ciclofaixa pintada', 'time': '15 min', 'slope': 'Subidas fortes', 'bike': 'Própria (ou emprestada) – grátis', 'options': ['Bicicleta nas condições apresentadas', 'Manteria meu deslocamento habitual'], 'hint': 'Os atributos descrevem um pacote. O custo se refere a uma ida. A manutenção do deslocamento habitual inclui as condições já relatadas.'}, {'id': 'q33', 'number': 33, 'type': 'scenario', 'title': 'Como você viria ao campus nesta situação?', 'road': 'Ciclofaixa pintada', 'time': '20 min', 'slope': 'Plano', 'bike': 'Compartilhada comum – R$ 1,00', 'options': ['Bicicleta nas condições apresentadas', 'Manteria meu deslocamento habitual'], 'hint': 'Os atributos descrevem um pacote. O custo se refere a uma ida. A manutenção do deslocamento habitual inclui as condições já relatadas.'}, {'id': 'q34', 'number': 34, 'type': 'scenario', 'title': 'Como você viria ao campus nesta situação?', 'road': 'Ciclovia separada por meio-fio', 'time': '10 min', 'slope': 'Subidas fortes', 'bike': 'Compartilhada comum – R$ 1,00', 'options': ['Bicicleta nas condições apresentadas', 'Manteria meu deslocamento habitual'], 'hint': 'Os atributos descrevem um pacote. O custo se refere a uma ida. A manutenção do deslocamento habitual inclui as condições já relatadas.'}, {'id': 'q35', 'number': 35, 'type': 'scenario', 'title': 'Como você viria ao campus nesta situação?', 'road': 'Ciclovia separada por meio-fio', 'time': '15 min', 'slope': 'Plano', 'bike': 'Compartilhada elétrica – R$ 2,00', 'options': ['Bicicleta nas condições apresentadas', 'Manteria meu deslocamento habitual'], 'hint': 'Os atributos descrevem um pacote. O custo se refere a uma ida. A manutenção do deslocamento habitual inclui as condições já relatadas.'}, {'id': 'q36', 'number': 36, 'type': 'scenario', 'title': 'Como você viria ao campus nesta situação?', 'road': 'Ciclovia separada por meio-fio', 'time': '20 min', 'slope': 'Subidas moderadas', 'bike': 'Própria (ou emprestada) – grátis', 'options': ['Bicicleta nas condições apresentadas', 'Manteria meu deslocamento habitual'], 'hint': 'Os atributos descrevem um pacote. O custo se refere a uma ida. A manutenção do deslocamento habitual inclui as condições já relatadas.'}]}
 if method=='ml':result=ml(records)
 elif method=='mediation':result=mediation(records)
 elif method=='panel':result=panel(records,schema)
 else:raise ValueError('Método inválido.')
 return clean(dict(method=method,kind=next(iter(kinds)),seed=SEED,result=result,fingerprint=hashlib.sha256(json.dumps(records,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16],warning='SIMULAÇÃO: nenhum resultado descreve a população de Viçosa.' if kinds=={'synthetic'} else 'Associações da amostra; não implicam causalidade ou representatividade.'))

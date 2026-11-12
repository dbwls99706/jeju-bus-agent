"""Restricted local query planner. Never accepts executable code or generated numbers."""
import os,re,threading
LABELS={'A':'time','B':'weekday','C':'month','D':'user_type'}
_LOCK=threading.Lock();_CACHE=None
SYSTEM='''질문에 맞는 분석 도구를 하나 고르세요. A=시간대 비교, B=요일 비교, C=월별 추이, D=이용자 유형 비교. 답은 A B C D 중 한 글자만 쓰세요. 예: 어느 시간대에 많이 타나요? 답:A. 예: 평일과 주말은 어떻게 다른가요? 답:B. 예: 매달 어떻게 변했나요? 답:C. 예: 경로와 일반은 차이가 있나요? 답:D.'''
def local_plan(question):
 global _CACHE
 path=os.environ.get('BUS_MODEL_DIR')
 if not path:return None
 with _LOCK:
  import torch
  from transformers import AutoTokenizer,AutoModelForCausalLM
  torch.set_num_threads(4)
  if _CACHE is None:
   tok=AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False)
   model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,trust_remote_code=False,use_safetensors=True,dtype=torch.bfloat16 if os.environ.get('BUS_MODEL_DTYPE')=='bfloat16' else torch.float32)
   model.eval();_CACHE=(tok,model)
  tok,model=_CACHE
  text=tok.apply_chat_template([{'role':'system','content':SYSTEM},{'role':'user','content':question}],tokenize=False,add_generation_prompt=True)
  inputs=tok([text],return_tensors='pt')
  with torch.inference_mode():out=model.generate(**inputs,max_new_tokens=5,do_sample=False)
  answer=tok.decode(out[0][inputs['input_ids'].shape[-1]:],skip_special_tokens=True).strip()
  if answer not in LABELS:raise ValueError('unrecognized plan')
  return LABELS[answer]
def normalize_question(q):return re.sub(r'\s+','',q)

DIMENSION_CUES={
 'weekday':('요일','주말','평일','토요일','일요일','일주일'),
 'month':('매달','월별','추이','월마다','월간','연중','추세','월단위','한달씩'),
 'user_type':('유형','연령','일반과','경로와','어린이와','청소년과','나이대','이용자구분'),
 'time':('시간','구간','아침','저녁','오후','새벽','출근','퇴근','밤','하루중'),
}
def dimension_tags(q):
 q=normalize_question(q)
 return [dim for dim,cues in DIMENSION_CUES.items() if any(w in q for w in cues)]
def rule_plan(q):
 tags=dimension_tags(q)
 return tags[0] if tags else None
def plan(q):
 expected=rule_plan(q);warning=None
 try: proposed=local_plan(q)
 except Exception:proposed=None;warning='로컬 AI 계획을 해석하지 못해 규칙 모드로 전환했습니다.'
 if proposed and expected and proposed!=expected:
  return expected,'rules_guarded','AI 계획과 명시적 질문 항목이 달라 규칙으로 교정했습니다.'
 if proposed:return proposed,'local_ai',warning
 return expected or 'time','rules',warning

class QuestionScopeError(ValueError):pass
def validate_scope(q):
 q=normalize_question(q)
 if re.search(r'20\d{2}년|\d{1,2}월|지난달|지난해|올해|작년|최근\s*\d+',q):raise QuestionScopeError('질문의 날짜 표현은 자동 적용하지 않습니다. 화면의 시작일·종료일을 먼저 설정하고 비교 기준을 질문하세요.')
 tags=[{'time':'시간대','weekday':'요일','month':'월','user_type':'유형'}[t] for t in dimension_tags(q)]
 if len(tags)>1:raise QuestionScopeError('현재 한 번에 한 가지 기준만 분석합니다. '+', '.join(tags)+'를 함께 제한하는 교차 분석은 지원하지 않습니다. 기준 하나를 골라 다시 질문하세요.')
 if re.search(r'(평일|주말|아침|저녁|새벽|오후|출근|퇴근|월요일|화요일|수요일|목요일|금요일|토요일|일요일)(에)?만',q) or re.search(r'\d{1,2}\s*시',q):
  raise QuestionScopeError('현재 특정 요일·시간만 거르는 조건은 지원하지 않습니다. 날짜·유형은 화면 필터에서 선택하고, 시간대 또는 요일 전체 비교를 요청하세요.')

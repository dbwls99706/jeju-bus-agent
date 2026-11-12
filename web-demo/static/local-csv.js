/* Local-only CSV inspection. No network, storage or AI calls. */
(function(root){
'use strict';
const MAX_BYTES=5*1024*1024, MAX_ROWS=100000;
const HEADERS=['base_date','day_of_week','base_hour','user_type','user_count'];
const SLOTS=['01시-06시','07시-09시','10시-12시','13시-15시','16시-18시','19시-21시','22시-24시'];
const DAYS=['월','화','수','목','금','토','일'];
function parseRecords(text){
 if(typeof text!=='string'||new TextEncoder().encode(text).length>MAX_BYTES)throw Error('CSV는 UTF-8 기준 5MB 이하여야 합니다.');
 text=text.replace(/^\uFEFF/,'');
 const rows=[];let row=[],field='',quoted=false,closed=false;
 function endField(){row.push(field);field='';closed=false;if(row.length>5)throw Error('CSV 열은 지정된 5개여야 합니다.');}
 function endRow(){endField();if(row.some(x=>x!==''))rows.push(row);row=[];if(rows.length>MAX_ROWS+1)throw Error('최대 100,000행까지 분석할 수 있습니다.');}
 for(let i=0;i<text.length;i++){
  const c=text[i];
  if(quoted){if(c==='"'){if(text[i+1]==='"'){field+='"';i++;}else{quoted=false;closed=true;}}else field+=c;continue;}
  if(c==='"'){if(field!==''||closed)throw Error('CSV 따옴표 형식이 올바르지 않습니다.');quoted=true;}
  else if(c===',')endField();
  else if(c==='\n'||c==='\r'){if(c==='\r'&&text[i+1]==='\n')i++;endRow();}
  else {if(closed)throw Error('닫는 따옴표 뒤에 구분자가 필요합니다.');field+=c;}
 }
 if(quoted)throw Error('CSV 따옴표가 닫히지 않았습니다.');
 if(field!==''||row.length||closed)endRow();
 return rows;
}
function summarize(text){
 const records=parseRecords(text),header=records.shift();
 if(!header||header.length!==5||new Set(header).size!==5||!HEADERS.every(h=>header.includes(h)))throw Error('필수 열: '+HEADERS.join(', '));
 if(!records.length)throw Error('분석할 데이터 행이 없습니다.');
 const idx=Object.fromEntries(header.map((h,i)=>[h,i]));
 const out={rows:records.length,total:0,minDate:'',maxDate:'',byHour:Object.fromEntries(SLOTS.map(x=>[x,0])),byWeekday:Object.fromEntries(DAYS.map(x=>[x,0])),hourRows:Object.fromEntries(SLOTS.map(x=>[x,0])),weekdayRows:Object.fromEntries(DAYS.map(x=>[x,0])),types:[],dates:0};
 const dates=new Set(),types=new Set(),keys=new Set();
 for(let i=0;i<records.length;i++){
  const r=records[i],fail=m=>{throw Error((i+2)+'행: '+m);};
  if(r.length!==5)fail('열 수가 다릅니다.');
  const d=r[idx.base_date],day=r[idx.day_of_week],slot=r[idx.base_hour],type=r[idx.user_type],raw=r[idx.user_count];
  if(!/^\d{8}$/.test(d))fail('날짜는 YYYYMMDD 형식이어야 합니다.');
  const iso=d.slice(0,4)+'-'+d.slice(4,6)+'-'+d.slice(6),dt=new Date(iso+'T00:00:00Z');
  if(!Number.isFinite(dt.getTime())||dt.toISOString().slice(0,10)!==iso)fail('존재하지 않는 날짜입니다.');
  if(DAYS[(dt.getUTCDay()+6)%7]!==day)fail('날짜와 요일이 일치하지 않습니다.');
  if(!SLOTS.includes(slot))fail('지원하지 않는 시간 구간입니다.');
  if(!type.trim()||type.length>100)fail('이용자 유형은 1~100자여야 합니다.');
  if(!/^\d+$/.test(raw)||!Number.isSafeInteger(Number(raw)))fail('이용량은 안전 범위 내의 음이 아닌 정수여야 합니다.');
  const n=Number(raw),key=JSON.stringify([d,slot,type]);
  if(keys.has(key))fail('같은 날짜·시간·유형이 중복되었습니다.');keys.add(key);
  if(!Number.isSafeInteger(out.total+n))fail('합계가 안전한 정수 범위를 넘습니다.');
  out.total+=n;out.byHour[slot]+=n;out.byWeekday[day]+=n;out.hourRows[slot]++;out.weekdayRows[day]++;dates.add(iso);types.add(type);
  if(!out.minDate||iso<out.minDate)out.minDate=iso;if(iso>out.maxDate)out.maxDate=iso;
 }
 out.dates=dates.size;out.types=Array.from(types).sort();return out;
}
function mount(){
 const host=document.getElementById('local-csv-panel');if(!host)return;
 function node(tag,text,attrs={}){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;for(const [k,v]of Object.entries(attrs))el.setAttribute(k,v);return el;}
 host.classList.add('local-csv-panel');host.setAttribute('aria-labelledby','local-csv-title');
 host.append(node('h2','내 CSV 로컬 분석 · AI 미사용',{id:'local-csv-title'}));
 host.append(node('p','내 컴퓨터의 CSV를 브라우저 메모리에서만 읽습니다. 파일과 계산 결과를 서버에 전송하거나 저장하지 않습니다. 아래 합성 체험과 별개이며, AI가 아니라 정해진 계산식으로 집계합니다.'));
 host.append(node('p','UTF-8 CSV · 최대 5MB / 100,000행 · 필수 열: '+HEADERS.join(', '),{class:'local-csv-help'}));
 const label=node('label','분석할 CSV 파일 선택',{for:'local-csv-file'}),input=node('input',undefined,{id:'local-csv-file',type:'file',accept:'.csv,text/csv'});
 const clear=node('button','파일·결과 지우기',{type:'button'}),status=node('p','파일을 선택하면 바로 검사합니다.',{role:'status','aria-live':'polite'}),result=node('div',undefined,{class:'local-csv-result'});
 host.append(label,input,clear,status,result);let generation=0;
 clear.addEventListener('click',()=>{generation++;input.value='';result.replaceChildren();status.textContent='파일과 결과를 화면에서 지웠습니다.';input.focus();});
 input.addEventListener('change',async()=>{
  const token=++generation,file=input.files&&input.files[0];result.replaceChildren();if(!file)return;
  status.textContent='파일을 이 브라우저에서 검사하고 있습니다.';
  try{
   if(file.size>MAX_BYTES)throw Error('파일은 5MB 이하여야 합니다.');
   const bytes=await file.arrayBuffer();if(token!==generation)return;
   let text;try{text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);}catch(e){throw Error('UTF-8로 저장된 CSV를 선택하세요.');}
   const s=summarize(text);if(token!==generation)return;
   const fmt=n=>n.toLocaleString('ko-KR');
   result.append(node('h3','내 파일의 관측 집계'),node('p',`${fmt(s.rows)}행 · ${s.minDate} ~ ${s.maxDate} · 관측일 ${fmt(s.dates)}일`));
   result.append(node('p',`관측 이용량 합계: ${fmt(s.total)} · 유형: ${s.types.join(', ')}`));
   result.append(node('p','누락 행은 0명으로 채우지 않습니다. 기록이 없는 범주는 ‘미기록’으로 표시하며, 기록이 있는 범주에도 일부 날짜·유형이 빠져 있을 수 있습니다. 관측일 수와 유형 구성이 달라 직접적인 혼잡도·수요 비교에는 사용할 수 없습니다.'));
   for(const [caption,values,counts]of [['시간대별 관측 합계',s.byHour,s.hourRows],['요일별 관측 합계',s.byWeekday,s.weekdayRows]]){
    const table=node('table'),cap=node('caption',caption),thead=node('thead'),tr=node('tr');tr.append(node('th','구분',{scope:'col'}),node('th','관측 이용량 합계',{scope:'col'}));thead.append(tr);const body=node('tbody');
    for(const [k,v]of Object.entries(values)){const row=node('tr');row.append(node('th',k,{scope:'row'}),node('td',counts[k]?fmt(v):'미기록'));body.append(row);}table.append(cap,thead,body);result.append(table);
   }
   status.textContent='로컬 분석 완료. 파일은 서버로 전송하지 않았습니다.';
  }catch(e){if(token===generation)status.textContent='분석하지 못했습니다. '+e.message;}
 });
}
if(typeof module!=='undefined'&&module.exports)module.exports={parseRecords,summarize,MAX_BYTES,MAX_ROWS};
if(typeof document!=='undefined'){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();}
})(typeof window==='undefined'?globalThis:window);

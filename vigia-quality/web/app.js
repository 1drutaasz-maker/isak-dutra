"use strict";
const $=id=>document.getElementById(id), num=x=>Number(x).toLocaleString("pt-BR",{maximumFractionDigits:2});
function sample(n,start=0){return Array.from({length:n},(_,j)=>{const i=j+start;return{batch_id:"L-"+String(i+1).padStart(4,"0"),temperature_c:41+(i%11-5)*.21,ph:4.55+(i%9-4)*.025,duration_min:175+(i%13-6)*2,yield_pct:92+(i%7-3)*.22}})}
let reference=sample(120), candidates=sample(16,120);
candidates[2]={...candidates[2],temperature_c:78,ph:7.2,duration_min:310,batch_id:"L-ALERTA-01"};
candidates[9]={...candidates[9],temperature_c:19,ph:3.1,yield_pct:64,batch_id:"L-ALERTA-02"};
async function csv(file){if(file.size>2e6)throw new Error("CSV limitado a 2 MB.");const lines=(await file.text()).trim().replace(/^\uFEFF/,"").split(/\r?\n/).filter(Boolean),header=lines.shift().trim().split(",").map(x=>x.trim().toLowerCase()),keys=["batch_id","temperature_c","ph","duration_min","yield_pct"];if(keys.some(x=>!header.includes(x)))throw new Error("Colunas esperadas: "+keys.join(","));return lines.map(line=>{const cols=line.split(","),row={};keys.forEach(k=>row[k]=k==="batch_id"?cols[header.indexOf(k)].trim():Number(cols[header.indexOf(k)]));if(!row.batch_id||keys.slice(1).some(k=>!Number.isFinite(row[k])))throw new Error("Dados inválidos no arquivo.");return row})}
for(const [input,target,min] of [["referenceFile","reference",50],["candidateFile","candidates",1]]){
 $(input).addEventListener("change",async e=>{const file=e.target.files?.[0];if(!file)return;try{const items=await csv(file);if(items.length<min)throw new Error("É necessário pelo menos "+min+" lote(s).");if(target==="reference")reference=items;else candidates=items;$("sample").textContent="CSV: "+file.name.toUpperCase();$("message").textContent="Arquivo carregado: "+items.length+" lotes."; $("report").hidden=true;}catch(ex){$("message").textContent=ex.message}})
}
function plot(rows){
 const host=$("plot");host.replaceChildren();const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");svg.setAttribute("viewBox","0 0 600 250");svg.setAttribute("role","img");svg.setAttribute("aria-label","Distribuição por pH e temperatura");
 const values=rows.map(x=>x.measurements),phs=values.map(x=>x.ph),temps=values.map(x=>x.temperature_c);
 const minx=Math.min(...phs)-.25,maxx=Math.max(...phs)+.25,miny=Math.min(...temps)-2,maxy=Math.max(...temps)+2;
 const el=(name,attrs)=>{const n=document.createElementNS("http://www.w3.org/2000/svg",name);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));return n};
 for(let g=0;g<5;g++){const y=17+g*51;svg.append(el("line",{x1:41,y1:y,x2:580,y2:y}));const t=el("text",{x:0,y:y+4});t.textContent=num(maxy-(maxy-miny)*g/4);svg.append(t)}
 rows.forEach(r=>{const m=r.measurements,x=46+(m.ph-minx)/(maxx-minx)*525,y=220-(m.temperature_c-miny)/(maxy-miny)*195,c=el("circle",{cx:x,cy:y,r:r.anomaly?6:4,fill:r.anomaly?"#ffaf87":"#79e3dd",opacity:r.anomaly?1:.72});const tip=el("title",{});tip.textContent=r.batch_id+" · pH "+m.ph+" · "+m.temperature_c+" °C";c.append(tip);svg.append(c)});
 const axis=el("text",{x:510,y:247});axis.textContent="pH →";svg.append(axis);host.append(svg);
}
$("run").addEventListener("click",async()=>{
 const b=$("run");b.disabled=true;b.textContent="ANALISANDO...";$("message").textContent="";
 try{
  const response=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({reference,candidates,sensitivity:Number($("sensitivity").value)})});
  const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==="string"?data.detail:"Verifique os valores do CSV.");
  $("report").hidden=false;$("total").textContent=num(data.summary.analyzed_batches);$("flagged").textContent=num(data.summary.flagged_batches);$("rate").textContent=num(data.summary.flagged_rate_pct)+"%";$("reference").textContent=num(data.summary.reference_batches);
  $("headline").textContent=data.summary.flagged_batches?"Desvios detectados.":"Padrão estável.";
  $("summary").textContent=data.summary.flagged_batches?"O modelo identificou "+data.summary.flagged_batches+" lote(s) com padrões atípicos em relação à referência. Investigue os sinais e valide com procedimentos internos.":"Nenhum dos lotes analisados foi marcado como anômalo, com a sensibilidade selecionada. Isso não garante conformidade.";
  const sorted=[...data.batches].sort((a,b)=>Number(b.anomaly)-Number(a.anomaly)||a.decision_score-b.decision_score);
  const table=$("rows");table.replaceChildren();for(const r of sorted){const tr=document.createElement("tr");
   for(const value of [r.batch_id,r.anomaly?"INVESTIGAR":"REGULAR",num(r.decision_score),r.signals.map(s=>s.metric+": "+num(s.deviation)+"×").join(" / ")]){const td=document.createElement("td");if(value==="INVESTIGAR"||value==="REGULAR"){const tag=document.createElement("span");tag.className=value==="INVESTIGAR"?"risk":"ok";tag.textContent=value;td.append(tag)}else{td.textContent=value}tr.append(td)}table.append(tr)}
  plot(data.batches);$("report").scrollIntoView({behavior:"smooth"});
 }catch(ex){$("message").textContent="Falha: "+ex.message}finally{b.disabled=false;b.textContent="ANALISAR LOTES ↗"}
});

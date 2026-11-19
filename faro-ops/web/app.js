"use strict";
const $ = id => document.getElementById(id);
const number = n => Number(n).toLocaleString("pt-BR",{maximumFractionDigits:1});
function demoData(){
  const start=new Date(Date.UTC(2026,6,1)), rows=[];
  for(let i=0;i<120;i++){
    const d=new Date(start.getTime()+i*86400000);
    const weekday=d.getUTCDay(), weekend=weekday===0||weekday===6?-11:0;
    const units=Math.max(0,Math.round(32+i*.18+weekend+Math.sin(i*.47)*5+(i%13===0?8:0)));
    rows.push({date:d.toISOString().slice(0,10),units});
  }
  return rows;
}
let history=demoData();
const error=msg=>$("message").textContent=msg;
$("csv").addEventListener("change",async e=>{
  const file=e.target.files?.[0];if(!file)return;
  if(file.size>1024*1024){error("CSV muito grande. Limite: 1 MB.");return;}
  const text=await file.text();const lines=text.trim().replace(/^\uFEFF/,"").split(/\r?\n/).filter(Boolean);
  if(lines.length<29||lines.length>2001){error("O arquivo precisa ter entre 28 e 2000 registros, além do cabeçalho.");return;}
  const header=lines.shift().toLowerCase().replace(/\s/g,"").split(",");
  const di=header.indexOf("date"),ui=header.indexOf("units");
  if(di<0||ui<0){error("Colunas obrigatórias: date,units.");return;}
  const parsed=lines.map(l=>{const c=l.split(",");return {date:c[di],units:Number(c[ui])}});
  if(parsed.some(r=>!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||!Number.isFinite(r.units)||r.units<0)){
    error("Datas inválidas ou vendas não numéricas.");return;
  }
  history=parsed;$("dataStatus").textContent="● "+file.name.toUpperCase()+" / "+parsed.length+" DIAS";
  error("Dados importados. Clique em analisar.");$("results").hidden=true;
});
const tag=(tag,attrs={})=>{const el=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));return el;};
function chart(points){
 const root=$("chart");root.replaceChildren();const svg=tag("svg",{viewBox:"0 0 640 245",role:"img","aria-label":"Previsões diárias de demanda com limites heurísticos"});
 const max=Math.max(...points.map(p=>p.upper_heuristic),1)*1.12;
 for(let g=0;g<5;g++){const y=15+g*48;svg.append(tag("line",{x1:30,y1:y,x2:627,y2:y}));const t=tag("text",{x:0,y:y+4});t.textContent=number(max*(1-g/4));svg.append(t)}
 const barwidth=570/points.length;
 points.forEach((p,i)=>{
   const x=40+i*barwidth+barwidth*.16, h=(p.units/max)*195,y=207-h;
   const rect=tag("rect",{x,y,width:barwidth*.65,height:h,rx:2,fill:"#9df5cc",opacity:".9"});
   const tooltip=tag("title");tooltip.textContent=p.date+": "+number(p.units)+" unidades (faixa "+number(p.lower_heuristic)+"–"+number(p.upper_heuristic)+")";rect.append(tooltip);svg.append(rect);
   if(i%Math.max(1,Math.ceil(points.length/7))===0){const t=tag("text",{x:x,y:231});t.textContent=p.date.slice(5);svg.append(t);}
 });
 root.append(svg);
}
$("run").addEventListener("click",async()=>{
 const button=$("run");button.disabled=true;button.textContent="PROCESSANDO MODELO...";error("");
 const payload={sku:$("sku").value.trim(),stock:Number($("stock").value),lead_days:Number($("lead").value),horizon:Number($("horizon").value),history};
 try{
   const response=await fetch("/api/forecast",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
   const body=await response.json();
   if(!response.ok){const msg=typeof body.detail==="string"?body.detail:"Confira os parâmetros e o histórico.";throw new Error(msg)}
   $("results").hidden=false;$("reportDate").textContent="GERADO EM "+new Date().toLocaleString("pt-BR");
   $("demand").textContent=number(body.forecast.reduce((s,p)=>s+p.units,0));
   $("reorder").textContent=number(body.inventory.reorder_point);
   $("purchase").textContent=number(body.inventory.suggested_purchase);
   $("mae").textContent=number(body.metrics.mae);
   $("comparison").textContent="BASELINE: "+number(body.metrics.naive_mae)+" • "+body.metrics.validation_days+" DIAS DE TESTE";
   $("statusCaption").textContent=body.inventory.status==="REPOR"?"REPOSIÇÃO NECESSÁRIA":"ESTOQUE SUFICIENTE";
   $("insightTitle").textContent=body.inventory.status==="REPOR"?"Risco de ruptura detectado.":"Operação sob controle.";
   $("insight").textContent=body.inventory.status==="REPOR"?
     "A previsão indica demanda superior à cobertura atual, considerando o prazo de reposição e a margem de segurança. Considere comprar "+number(body.inventory.suggested_purchase)+" unidades.":
     "O estoque cobre o ponto de reposição estimado. Continue acompanhando a demanda e a qualidade da previsão.";
   $("safety").textContent=number(body.inventory.safety_stock)+" un.";
   $("leadDemand").textContent=number(body.inventory.forecast_demand_in_lead_time)+" un.";
   $("validation").textContent=body.metrics.validation_days+" dias";
   chart(body.forecast);$("results").scrollIntoView({behavior:"smooth",block:"start"});
 }catch(e){error("Falha na análise: "+e.message)}finally{button.disabled=false;button.textContent="ANALISAR DEMANDA ↗"}
});

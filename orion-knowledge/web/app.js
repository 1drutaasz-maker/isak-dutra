"use strict";
const $=id=>document.getElementById(id);
async function api(path,options={}){
 const res=await fetch(path,{headers:{"Content-Type":"application/json"},...options});
 const data=await res.json().catch(()=>({}));
 if(!res.ok)throw new Error(typeof data.detail==="string"?data.detail:"Falha na solicitação ("+res.status+").");
 return data;
}
const msg=(id,text)=>$(id).textContent=text;
async function refresh(){
 const [status,docs]=await Promise.all([api("/api/status"),api("/api/documents")]);
 $("status").textContent="● "+(status.mode==="llm_plus_retrieval"?"LLM + RETRIEVAL":"RETRIEVAL ONLY");
 $("docCount").textContent=docs.length;
 const list=$("docs");list.replaceChildren();
 if(!docs.length){const p=document.createElement("p");p.className="message";p.textContent="Nenhum documento cadastrado.";list.append(p)}
 for(const d of docs){
  const line=document.createElement("div");line.className="doc";
  const info=document.createElement("div"),b=document.createElement("b"),small=document.createElement("small");
  b.textContent=d.title;small.textContent=d.chunks+" TRECHO(S) INDEXADO(S)";info.append(b,small);
  const del=document.createElement("button");del.textContent="EXCLUIR";
  del.setAttribute("aria-label","Excluir "+d.title);
  del.addEventListener("click",async()=>{
   if(!confirm("Excluir "+d.title+"?"))return;
   try{await api("/api/documents/"+encodeURIComponent(d.id),{method:"DELETE"});await refresh()}catch(e){msg("docMessage",e.message)}
  });line.append(info,del);list.append(line);
 }
}
$("documentForm").addEventListener("submit",async e=>{
 e.preventDefault();const button=e.currentTarget.querySelector("button");button.disabled=true;msg("docMessage","");
 try{const result=await api("/api/documents",{method:"POST",body:JSON.stringify({title:$("docTitle").value,content:$("docContent").value})});
  e.currentTarget.reset();msg("docMessage","Documento indexado em "+result.chunks+" trecho(s).");await refresh();
 }catch(ex){msg("docMessage",ex.message)}finally{button.disabled=false}
});
$("askForm").addEventListener("submit",async e=>{
 e.preventDefault();const button=$("ask");button.disabled=true;button.textContent="ANALISANDO...";
 msg("askMessage","");
 try{
  const result=await api("/api/ask",{method:"POST",body:JSON.stringify({question:$("question").value.trim(),top_k:4})});
  $("response").hidden=false;$("answerText").textContent=result.answer;
  $("mode").textContent=result.mode==="llm_plus_retrieval"?"GENERATED WITH SOURCES":result.mode==="no_evidence"?"NO EVIDENCE":"RETRIEVAL ONLY / NO LLM";
  const container=$("sources");container.replaceChildren();
  for(const s of result.sources){
   const div=document.createElement("div");div.className="source";
   const title=document.createElement("strong");title.textContent=s.document;
   const meta=document.createElement("small");meta.textContent="TRECHO "+s.section+" • RELEVÂNCIA "+Math.round(s.score*100)+"% (similaridade)";
   const excerpt=document.createElement("p");excerpt.textContent=s.excerpt;div.append(title,meta,excerpt);container.append(div);
  }
 }catch(ex){msg("askMessage",ex.message)}finally{button.disabled=false;button.innerHTML="CONSULTAR BASE <b>↗</b>"}
});
$("seed").addEventListener("click",async()=>{
 const sample=["Documento fictício da empresa Laboratório Aurora. Objetivo: padronizar o controle interno de lotes e temperaturas.",
 "No recebimento de cada lote de leite, o responsável deve conferir integridade da embalagem, quantidade recebida, identificação do fornecedor e temperatura registrada.",
 "Registrar o código do lote, data de recebimento e horário no sistema interno antes do armazenamento.",
 "Produtos com divergência devem ser identificados e segregados preventivamente em área definida, aguardando avaliação do responsável técnico. Não liberar lotes com registros incompletos.",
 "Para rastreabilidade, cada etapa precisa manter o mesmo identificador do lote e apontar responsável, horário e quantidade movimentada.",
 "Se houver falha no registro de temperatura, o supervisor de qualidade deve ser notificado e deve decidir a destinação conforme procedimento interno. Este conteúdo é fictício e não estabelece requisitos legais."].join(" ");
 try{
  await api("/api/documents",{method:"POST",body:JSON.stringify({title:"Laboratório Aurora — Procedimento fictício de lotes",content:sample})});
  msg("docMessage","Exemplo fictício cadastrado. Pergunte: como tratar divergências de lote?");await refresh();
 }catch(e){msg("docMessage",e.message)}
});
refresh().catch(e=>msg("docMessage","Não foi possível conectar ao servidor: "+e.message));

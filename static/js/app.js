async function postJSON(url, data={}) {
  const response = await fetch(url, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data)});
  const payload = await response.json().catch(()=>({error:"Unexpected server response."}));
  if (!response.ok) throw new Error(payload.error || "Request failed.");
  return payload;
}
function byId(id){return document.getElementById(id)}
document.addEventListener("DOMContentLoaded", () => {
  const answerBtn=byId("submit-answer");
  if(answerBtn) answerBtn.addEventListener("click", async()=>{
    const result=byId("answer-result"); result.textContent="Checking your deduction...";
    try{const data=await postJSON("/api/answer",{case_id:answerBtn.dataset.case,answer:byId("answer").value});
      result.textContent=data.message+(data.correct?` You earned ${data.score} points. Total XP: ${data.xp}.`:"");
      result.style.color=data.correct?"#76d4a9":"#e3bd79";
    }catch(e){result.textContent=e.message;}
  });
  const hintBtn=byId("get-hint");
  if(hintBtn) hintBtn.addEventListener("click",async()=>{
    const out=byId("hint-result");out.textContent="Consulting the case file...";
    try{const d=await postJSON(`/api/hint/${hintBtn.dataset.case}`);out.textContent=d.hint+(typeof d.remaining==="number"?` (${d.remaining} hints left)`:"");}
    catch(e){out.textContent=e.message;}
  });
  const send=byId("send-chat");
  if(send) send.addEventListener("click",async()=>{
    const input=byId("chat-message"), log=byId("chat-log"), msg=input.value.trim();if(!msg)return;
    const user=document.createElement("div");user.className="bubble user";user.textContent=msg;log.appendChild(user);input.value="";
    const wait=document.createElement("div");wait.className="bubble bot";wait.textContent="Detective AI is reviewing the evidence...";log.appendChild(wait);log.scrollTop=log.scrollHeight;
    try{const d=await postJSON("/api/chat",{case_id:send.dataset.case,message:msg});wait.textContent=d.reply;byId("ai-mode").textContent=`Assistant mode: ${d.ai_mode}`;}
    catch(e){wait.textContent=e.message;}
    log.scrollTop=log.scrollHeight;
  });
  const gen=byId("generate-ai-case");
  if(gen) gen.addEventListener("click",async()=>{
    const out=byId("generate-result");out.textContent="Generating a new case...";
    try{const d=await postJSON("/api/generate-case",{category:"Murder Mystery",difficulty:"Medium"});out.textContent=`Created: ${d.title}. Refresh to see it.`;}
    catch(e){out.textContent=e.message;}
  });
  const create=byId("create-room");
  if(create) create.addEventListener("click",async()=>{
    const id=byId("case-select").value;if(!id){byId("created-code").textContent="No cases available.";return;}
    try{const d=await postJSON("/api/rooms",{case_id:id});byId("created-code").textContent=`ROOM CODE: ${d.code}`;watchRoom(d.code);}
    catch(e){byId("created-code").textContent=e.message;}
  });
  const join=byId("join-room");
  if(join) join.addEventListener("click",async()=>{
    try{const d=await postJSON("/api/rooms/join",{code:byId("join-code").value.trim()});byId("join-result").textContent=`Joined room ${d.code}`;watchRoom(d.code);}
    catch(e){byId("join-result").textContent=e.message;}
  });
});
let roomTimer=null;
function watchRoom(code){
  if(roomTimer)clearInterval(roomTimer);
  const refresh=async()=>{try{const r=await fetch(`/api/rooms/${code}`);const d=await r.json();if(!r.ok)throw new Error(d.error);
    byId("room-status").textContent=`Room ${d.code} · ${d.case_title} · ${d.status}`;
    byId("room-players").innerHTML="";
    d.players.forEach(p=>{const row=document.createElement("div");row.className="rank-row";const name=document.createElement("strong");name.textContent=p.username;const score=document.createElement("span");score.textContent=`${p.score} points`;row.append(name,score);byId("room-players").appendChild(row);});
  }catch(e){byId("room-status").textContent=e.message;}};
  refresh();roomTimer=setInterval(refresh,4000);
}

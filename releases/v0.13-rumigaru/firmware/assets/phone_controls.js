let sessionToken=null,online=false,working=false,previewTimer=null,partCatalog=null;
const slots=['head','body','arms','legs','horns','tail','eyes','wings'];
const slotNames=['頭','体','腕','足','角','しっぽ','目','羽'];
async function api(path){const r=await fetch(path,{signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error('端末に接続できません');return r.json()}
function actionButton(label,fn){const b=el('button',label,'remote-action');b.disabled=!online||working||!!state?.phone_busy||!!window.ROAM_SAVED_STATE;b.onclick=async()=>{if(working)return;working=true;b.disabled=true;try{await fn()}catch(e){$('status').textContent=e.message}finally{working=false;document.querySelectorAll('.remote-action').forEach(x=>x.disabled=!!x.dataset.blocked||!online||!!state?.phone_busy||!!window.ROAM_SAVED_STATE);}};return b}
async function writeApi(path,data){if(!online||!sessionToken||window.ROAM_SAVED_STATE)throw Error('端末のWi-Fiにつないで同期してください');const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Roam-Token':sessionToken},body:JSON.stringify({...data,request_id:Date.now().toString(36)+'-'+Math.random().toString(36).slice(2)}),signal:AbortSignal.timeout(30000)});const result=await r.json();if(!r.ok)throw Error(result.error||'反映できませんでした');return result}
async function action(name,p){const result=await writeApi('/api/action',{action:name,uid:p?.uid,stage:p?.evolution});await sync();$('status').textContent=result.message}
function careControls(p){const box=el('div'),bar=el('div',undefined,'bar');box.append(el('p','ごはん '+state.inventory.food+'個 · 回復薬 '+state.inventory.potion+'個'+(state.sleeping?' · おやすみ中':''),'muted'),bar);for(const [key,label]of [['feed','ごはん'],['play','遊ぶ'],['train','訓練'],['rest',state.sleeping?'起こす':'休む'],['potion','回復薬']]){const b=actionButton(label,()=>action(key,p));const blocked=key==='feed'&&(!state.inventory.food||p.fullness>=100)||key==='potion'&&(!state.inventory.potion||p.hp>=p.stats.hp)||['play','train'].includes(key)&&state.sleeping||key==='train'&&(p.energy<20||p.fullness<10);if(blocked){b.dataset.blocked='1';b.disabled=true}bar.append(b)}if(p.evolution<2&&p.level>=20)bar.append(actionButton('進化する',async()=>{if(confirm('この仲間を進化させますか？'))await action('evolve',p)}));return box}
function eggControls(e){const box=el('article',undefined,'card');box.append(el('h2','たまご · 第'+e.child.generation+'世代'),el('p',e.remaining?'孵化まであと '+e.remaining+'秒（同期で更新）':'孵化できます！'));const bar=el('div',undefined,'bar');box.append(bar);for(const [key,label]of [['hatch','卵をかえす'],['incubate','孵化を早める']]){const b=actionButton(label,async()=>{const r=await writeApi('/api/action',{action:key,egg_uid:e.child.uid});await sync();$('status').textContent=r.message});if(key==='hatch'&&e.remaining>0||key==='incubate'&&(!state.inventory.incubator||!e.remaining)){b.dataset.blocked='1';b.disabled=true}bar.append(b)}return box}

function selectionControl(p){return actionButton(state.pet?.uid===p.uid?'育成中':'この仲間を育てる',()=>action('switch',p))}
function field(label,input){const n=el('label',undefined,'field');n.append(el('span',label),input);return n}
function selectOptions(options){const s=el('select');for(const [value,label]of options){const o=el('option',label);o.value=value;s.append(o)}return s}
function numberInput(value,min,max){const n=el('input');n.type='number';n.value=value;n.min=min;n.max=max;n.step=1;return n}
function paintIndexed(canvas,pixels,palette){const ctx=canvas.getContext('2d'),im=ctx.createImageData(64,64);for(let i=0;i<4096;i++){const n=typeof pixels==='string'?parseInt(pixels.slice(i*2,i*2+2),16):pixels[i];const color=palette[n]||[0,0,0];im.data.set([...color,n?255:0],i*4)}ctx.putImageData(im,0,0)}
async function renderParts(view){
 if(previewTimer){clearInterval(previewTimer);previewTimer=null}
 view.append(el('h2','キャラパーツ工房'),el('p','透過PNGを追加して、仲間の頭や羽を着せ替えできます。遺伝子・能力は変わりません。装着はこの進化段階だけに適用されます。','muted'));
 if(!online||window.ROAM_SAVED_STATE){view.append(el('p','端末に接続して同期してください。'));return}
 const pets=[...(state.pet?[state.pet]:[]),...state.caught];if(!pets.length){view.append(el('p','仲間を迎えてから利用できます。'));return}
 try{partCatalog=await api('/api/parts')}catch(e){view.append(el('p',e.message));return}
 const box=el('section',undefined,'card');view.append(box);
 const target=selectOptions(pets.map(p=>[p.uid,(p.display_name||p.subtype||types[p.type])+' Lv.'+p.level+' / '+p.uid.slice(-5)]));
 const slot=selectOptions(slots.map((s,i)=>[s,slotNames[i]]));
 box.append(field('装着する仲間',target),field('部位',slot));
 const library=el('div');box.append(library);
 const name=el('input');name.maxLength=24;name.placeholder='例：ほのおのツノ';
 const file=el('input');file.type='file';file.accept='image/png';
 const count=selectOptions([[1,'1コマ（静止画）'],[2,'2コマ'],[3,'3コマ'],[4,'4コマ']]);
 const size=numberInput(64,1,64),posX=numberInput(0,0,63),posY=numberInput(0,0,63);
 box.append(el('h2','PNGから新しく追加'),field('パーツ名',name),field('PNG画像',file),el('p','動く画像は同じ大きさのコマを横に並べてください。透明部分を残し、端末の12色に変換します。','muted'),field('画像のコマ数',count));
 const row=el('div',undefined,'stats');row.append(field('横幅（ドット）',size),field('横の位置',posX),field('縦の位置',posY));box.append(row);
 const canvas=el('canvas');canvas.width=canvas.height=64;canvas.className='part-preview';box.append(canvas);
 const hint=el('p','画像を選ぶと合成した姿が表示されます。','muted');box.append(hint);
 let bitmap=null,layers=null,frames=[],generation=0,uploading=false;
 const pet=()=>pets.find(p=>p.uid===target.value);
 async function refresh(){const gen=++generation;frames=[];layers=null;upload.disabled=true;hint.textContent='プレビューを読み込んでいます…';try{const data=await api('/api/layers?id='+encodeURIComponent(target.value)+'&slot='+slot.value);if(gen!==generation||tab!=='parts')return;layers=data;convert();await list()}catch(e){hint.textContent=e.message}}
 function convert(){frames=[];upload.disabled=true;if(!layers)return;try{
   if(!bitmap){paintIndexed(canvas,layers.behind,layers.palette);hint.textContent='PNG画像を選んでください。';return}
   const n=Number(count.value),w=Number(size.value),x=Number(posX.value),y=Number(posY.value),sourceWidth=bitmap.width/n;
   if(![w,x,y].every(Number.isInteger)||w<1||w>64||x<0||y<0||x>63||y>63||bitmap.width%n)throw Error('コマ数と位置を確認してください');
   const h=Math.max(1,Math.round(w*bitmap.height/sourceWidth));if(x+w>64||y+h>64)throw Error('画像が枠からはみ出します。幅や位置を調整してください');
   const temp=document.createElement('canvas');temp.width=temp.height=64;const ctx=temp.getContext('2d',{willReadFrequently:true});ctx.imageSmoothingEnabled=false;
   for(let f=0;f<n;f++){ctx.clearRect(0,0,64,64);ctx.drawImage(bitmap,f*sourceWidth,0,sourceWidth,bitmap.height,x,y,w,h);const rgba=ctx.getImageData(0,0,64,64).data,indices=new Uint8Array(4096);for(let i=0;i<4096;i++){if(rgba[i*4+3]<128)continue;let best=1,distance=Infinity;for(let j=1;j<layers.palette.length;j++){const c=layers.palette[j],d=(rgba[i*4]-c[0])**2+(rgba[i*4+1]-c[1])**2+(rgba[i*4+2]-c[2])**2;if(d<distance){distance=d;best=j}}indices[i]=best}frames.push(indices)}
   if(!frames.some(f=>f.some(v=>v)))throw Error('透明な画像です。描画されたPNGを選んでください');
   hint.textContent='合成プレビュー · '+n+'コマ / '+w+'×'+h+'ドット';upload.disabled=uploading||!online;drawPreview(0);
 }catch(e){frames=[];hint.textContent=e.message}}
 function drawPreview(f){if(!layers||!frames.length)return;const pixels=new Uint8Array(4096);for(let i=0;i<4096;i++)pixels[i]=parseInt(layers.front.slice(i*2,i*2+2),16)||frames[f%frames.length][i]||parseInt(layers.behind.slice(i*2,i*2+2),16);paintIndexed(canvas,pixels,layers.palette)}
 async function list(){library.replaceChildren();const selected=partCatalog.equipped[target.value+':'+pet().evolution]?.[slot.value];const available=partCatalog.items.filter(i=>i.slot===slot.value);library.append(el('p','保存済み '+partCatalog.items.length+' / 24個','muted'));for(const item of available){const row=el('div',undefined,'bar');row.append(el('span',item.name+' · '+item.frames+'コマ'+(selected===item.id?'（装着中）':'')),actionButton('装着',async()=>{await writeApi('/api/parts/equip',{uid:pet().uid,stage:pet().evolution,slot:slot.value,id:item.id});await sync()}),actionButton('削除',async()=>{if(!confirm('「'+item.name+'」を削除しますか？ 装着している仲間からも取り外されます。'))return;await writeApi('/api/parts/delete',{id:item.id});await sync()}));library.append(row)}if(selected)library.append(actionButton('取り外して元の姿に戻す',async()=>{await writeApi('/api/parts/equip',{uid:pet().uid,stage:pet().evolution,slot:slot.value,id:null});await sync()}));}
 const upload=el('button','このパーツを保存');upload.disabled=true;box.append(upload);
 upload.onclick=async()=>{if(uploading||!frames.length)return;if(!name.value.trim()){hint.textContent='パーツ名を入力してください';return}uploading=true;upload.disabled=true;try{const result=await writeApi('/api/parts/upload',{name:name.value.trim(),slot:slot.value,frames:frames.length,pixels:frames.map(f=>Array.from(f,v=>v.toString(16).padStart(2,'0')).join('')).join('')});await sync();$('status').textContent=result.message}catch(e){hint.textContent=e.message+'。同期して保存済み一覧を確認してください。'}finally{uploading=false;upload.disabled=!frames.length||!online}};
 file.onchange=async()=>{const f=file.files[0];if(!f)return;frames=[];upload.disabled=true;try{if(f.size>4*1024*1024)throw Error('PNGは4MB以下にしてください');const next=await createImageBitmap(f);if(next.width>2048||next.height>2048){next.close();throw Error('画像は2048×2048以下にしてください')}if(bitmap)bitmap.close();bitmap=next;convert()}catch(e){hint.textContent=e.message}};
 for(const input of[count,size,posX,posY])input.oninput=convert;
 target.onchange=refresh;slot.onchange=refresh;
 let frame=0;previewTimer=setInterval(()=>{if(tab!=='parts'||!canvas.isConnected){clearInterval(previewTimer);previewTimer=null;return}drawPreview(frame++)},240);
 await refresh();
}

function renameControls(p){const box=el('section',undefined,'card');const input=el('input');input.value=p.nickname||'';input.maxLength=8;input.placeholder=p.species_name||'名前';box.append(field('育成キャラの名前',input),el('p','ひらがな・カタカナ・英数字で8文字まで。空欄で保存すると種族名に戻ります。','muted'),actionButton('名前を保存',async()=>{const result=await writeApi('/api/action',{action:'rename',uid:p.uid,stage:p.evolution,nickname:input.value});await sync();$('status').textContent=result.message}));return box}

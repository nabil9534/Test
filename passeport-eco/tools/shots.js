// Planche de contrôle : une image par scène, prise juste avant la fin de chaque scène.
const {chromium}=require('playwright');const path=require('path');
(async()=>{const slug=process.argv[2];const b=await chromium.launch();
 const p=await b.newPage({viewport:{width:360,height:640}});const errs=[];p.on('pageerror',e=>errs.push(e.message));
 await p.goto('file://'+path.resolve(__dirname,'../build/'+slug+'.html'));await p.evaluate(()=>document.fonts.ready);
 const sc=await p.evaluate(()=>{playing=false;return scenes.map(s=>[s.start,s.dur])});
 const files=[];for(let i=0;i<sc.length;i++){const tt=sc[i][0]+sc[i][1]-250;
  await p.evaluate(x=>{t=x;render()},tt);await p.waitForTimeout(2300);
  const f=`/tmp/claude-0/-home-user-Test/5cb67a39-7ed1-505b-bb1e-465be2057c48/scratchpad/${slug}_${i}.png`;await p.screenshot({path:f});files.push(f)}
 console.log(JSON.stringify(files));if(errs.length)console.error('ERR',errs);await b.close()})();

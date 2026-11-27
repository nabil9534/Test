// Rendu image par image d'un épisode en MP4 muet (1080×1920, 30 i/s) + export des effets sonores.
// Usage : node tools/record.js <slug>
const {chromium}=require('playwright');const {spawn}=require('child_process');const fs=require('fs');const path=require('path');
const FPS=30, slug=process.argv[2], root=path.resolve(__dirname,'..');
(async()=>{
 const b=await chromium.launch();const p=await b.newPage({viewport:{width:540,height:960},deviceScaleFactor:2});
 await p.goto('file://'+root+'/build/'+slug+'.html');await p.evaluate(()=>document.fonts.ready);
 const info=await p.evaluate(()=>{playing=false;t=0;document.getElementById('again').style.display='none';
   window.__seen=new WeakSet();
   window.__step=function(nt,dt){t=nt;render();
     document.getAnimations().forEach(a=>{
       const tg=a.effect&&a.effect.target;
       if(tg&&tg.closest&&tg.closest('.tick')){a.pause();a.currentTime=nt;return}
       if(!__seen.has(a)){__seen.add(a);a.pause();a.currentTime=0}else{a.pause();a.currentTime=(a.currentTime||0)+dt}});};
   return {total:TOTAL,sfx:SFX,scenes:scenes.map(s=>({start:s.start,dur:s.dur}))};});
 fs.writeFileSync(root+'/build/'+slug+'.sfx.json',JSON.stringify(info));
 const out=root+'/build/'+slug+'.silent.mp4';
 const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(FPS),'-i','-','-c:v','libx264','-pix_fmt','yuv420p','-crf','18','-preset','medium','-vf','scale=1080:1920',out],{stdio:['pipe','ignore','inherit']});
 const N=Math.ceil(info.total/1000*FPS)+FPS;
 for(let k=0;k<N;k++){const nt=Math.min(info.total,k*1000/FPS);
   await p.evaluate(([nt,dt])=>__step(nt,dt),[nt,1000/FPS]);
   const buf=await p.screenshot({type:'png'});
   if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));}
 ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log(slug,'frames',N);
})();

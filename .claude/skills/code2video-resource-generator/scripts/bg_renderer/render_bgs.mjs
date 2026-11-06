// node render_bgs.mjs <specs_dir_or_file.json> <out_dir>   — renders each setting spec to bg_<id>.png (1920x1080)
import http from 'http'; import fs from 'fs'; import path from 'path'; import {fileURLToPath} from 'url'; import {createRequire} from 'module';
const here=path.dirname(fileURLToPath(import.meta.url)); const require=createRequire(import.meta.url);
const puppeteer=require('puppeteer-core');
const [,, specArg, outDir]=process.argv; if(!specArg||!outDir){console.error('usage: node render_bgs.mjs <specs> <out_dir>');process.exit(1)}
const files=fs.statSync(specArg).isDirectory()?fs.readdirSync(specArg).filter(f=>f.endsWith('.json')).map(f=>path.join(specArg,f)):[specArg];
fs.mkdirSync(outDir,{recursive:true});
const kitDir=path.resolve(here,'../../assets/kenney-glb');
const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.glb':'model/gltf-binary','.json':'application/json'};
const srv=http.createServer((q,r)=>{const u=decodeURIComponent(q.url.split('?')[0]);let f;
  if(u.startsWith('/kenney/'))f=path.join(kitDir,u.slice(8)); else if(u.startsWith('/spec/'))f=path.resolve(specArg.endsWith('.json')?path.dirname(specArg):specArg,u.slice(6)); else f=path.join(here,u==='/'?'render.html':u);
  fs.readFile(f,(e,d)=>{if(e){r.writeHead(404);r.end();return}r.writeHead(200,{'content-type':mime[path.extname(f)]||'application/octet-stream'});r.end(d)})}).listen(0);
await new Promise(r=>srv.on('listening',r)); const port=srv.address().port;
const chromeCandidates=[process.env.CHROME_PATH,'C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe','/usr/bin/google-chrome','/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].filter(Boolean);
const exe=chromeCandidates.find(p=>fs.existsSync(p)); if(!exe){console.error('No Chrome/Edge found; set CHROME_PATH');process.exit(2)}
const b=await puppeteer.launch({executablePath:exe,headless:'new',args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-sandbox']});
let fail=0;
for(const f of files){const id=path.basename(f,'.json');const pg=await b.newPage();await pg.setViewport({width:1920,height:1080});
  pg.on('pageerror',e=>console.log(id,'PAGEERR',e.message));
  const rel=path.basename(f); const spec=JSON.parse(fs.readFileSync(f,'utf8'));
  const passes=spec.layers?[['full',''],['far','_far'],['mid','_mid'],['near','_near']]:[['full','']];
  for(const [ps,suf] of passes){
    const page=await b.newPage();await page.setViewport({width:spec.width||1920,height:spec.height||1080});page.on('pageerror',e=>console.log(id,'PAGEERR',e.message));
    await page.goto(`http://localhost:${port}/render.html?spec=/spec/${rel}&pass=${ps}`);
    try{await page.waitForFunction('window.__done===true',{timeout:90000});const c=await page.$('canvas');await c.screenshot({path:path.join(outDir,`bg_${id}${suf}.png`),omitBackground:true});console.log('ok',id+suf)}catch(e){console.log('FAIL',id+suf);fail++}
    await page.close()}
  await pg.close()}
await b.close();srv.close();process.exit(fail?3:0);

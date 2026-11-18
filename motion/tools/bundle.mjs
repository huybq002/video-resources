// bundle the engine into dist/engine.js (one IIFE file the page loads)
import { build } from 'esbuild';
import { fileURLToPath } from 'url'; import path from 'path';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
await build({ entryPoints: [path.join(root, 'engine/index.js')], bundle: true, format: 'iife', outfile: path.join(root, 'dist/engine.js'),
  loader: { '.json': 'json' }, define: { 'process.env.NODE_ENV': '"production"' }, minify: false, sourcemap: false, logLevel: 'warning', target: 'chrome120' });
await build({ entryPoints: [path.join(root, 'engine/score.js')], bundle: true, format: 'iife', outfile: path.join(root, 'dist/score.js'), logLevel: 'warning', target: 'chrome120' });
console.log('engine + score bundled');

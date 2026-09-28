import fs from 'node:fs';
import './engine.js';
const schema=JSON.parse(fs.readFileSync(new URL('./questionario.schema.json',import.meta.url),'utf8'));
const data=globalThis.UFV.generate(schema,400,956835);
if(data.records.length!==400||!data.records.every(r=>r.is_synthetic))throw Error('Falha na identificação sintética');
fs.writeFileSync('simulacao-regenerada.json',JSON.stringify(data,null,2));
console.log('400 registros exclusivamente sintéticos gerados em simulacao-regenerada.json');

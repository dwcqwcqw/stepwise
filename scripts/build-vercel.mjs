import { mkdir, copyFile } from 'node:fs/promises';
await mkdir('public/static', { recursive: true });
await copyFile('services/web/static/index.html', 'public/index.html');
for (const name of ['app.js', 'styles.css'])
  await copyFile(`services/web/static/${name}`, `public/static/${name}`);
console.log('Stepwise frontend built from the shared application source.');

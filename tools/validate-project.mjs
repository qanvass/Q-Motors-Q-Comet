import { access, readFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const root = process.cwd();
const projectPath = path.join(root, 'vehicles/qcomet/project.json');
const concepts = path.join(root, 'vehicles/qcomet/source/concepts');
const required = [
  'q comet all four sides.png',
  'q comet front rear top.png',
  'Q Comet Front view showroom.png',
  'q comet wheel headlight tail light on and off.png',
  'q comet cabin dash.png',
  'q comet dash board.png'
];

const failures = [];
let project;

try {
  project = JSON.parse(await readFile(projectPath, 'utf8'));
} catch (error) {
  failures.push(`Cannot read project.json: ${error.message}`);
}

if (project) {
  if (project.id !== 'qcomet') failures.push('Project id must be qcomet.');
  if (project.displayName !== 'Q Comet') failures.push('Display name must be Q Comet.');
  if (project.gameplay?.doors !== 4) failures.push('Q Comet v1 must have four doors.');
  if (project.gameplay?.seats !== 4) failures.push('Q Comet v1 must have four seats.');
  if (!String(project.dimensionsMeters?.status).includes('PROVISIONAL')) {
    failures.push('Provisional dimensions must not be silently treated as approved.');
  }
}

for (const filename of required) {
  try {
    await access(path.join(concepts, filename));
  } catch {
    failures.push(`Missing concept sheet: ${filename}`);
  }
}

if (failures.length) {
  console.error('Q Comet validation failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Q Comet scaffold is internally consistent.');
console.log('Reminder: this validates project structure, not FiveM readiness.');

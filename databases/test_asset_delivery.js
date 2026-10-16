const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(__dirname, 'static/databases/databases.js'), 'utf8');
assert(fs.readFileSync(path.join(root, 'static/databases/databases.js'), 'utf8') === source,
    'The checked-in served asset must include the tested controller fixes');
for (const file of ['baseTemplate/templates/baseTemplate/index.html',
    'databases/templates/databases/createDatabase.html',
    'databases/templates/databases/phpMyAdmin.html',
    'databases/templates/databases/mysqlmanager.html']) {
    const template = fs.readFileSync(path.join(root, file), 'utf8');
    assert(template.includes("databases/databases.js' %}?v={{ CP_VERSION }}-db-ui-20261016"),
        file + ' must invalidate previously cached 3.0.7 database controllers');
}
console.log('Database asset delivery checks passed: collected-source parity and all four script cache keys.');

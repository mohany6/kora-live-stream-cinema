const fs = require('fs');

function checkFile(filepath) {
  console.log(`\n=== Checking JavaScript in ${filepath} ===`);
  const content = fs.readFileSync(filepath, 'utf8');
  const regex = /<script([^>]*)>([\s\S]*?)<\/script>/gi;
  let match;
  let count = 0;
  let hasErrors = false;

  while ((match = regex.exec(content)) !== null) {
    count++;
    const attrs = match[1];
    let body = match[2].trim();

    if (attrs.includes('application/ld+json')) {
      try {
        JSON.parse(body);
        console.log(`  Script #${count} (JSON-LD): VALID JSON`);
      } catch (e) {
        console.error(`  Script #${count} (JSON-LD): INVALID JSON:`, e.message);
        hasErrors = true;
      }
      continue;
    }

    if (attrs.includes('src=')) {
      console.log(`  Script #${count} (external): ${attrs.trim()}`);
      continue;
    }

    if (!body) continue;

    // Strip CDATA markers
    body = body.replace(/^\s*\/\/<!\[CDATA\[/, '').replace(/\/\/\]\]>\s*$/, '');

    try {
      new Function(body);
      console.log(`  Script #${count} (inline, ${body.length} chars): SYNTAX OK`);
    } catch (err) {
      console.error(`  Script #${count} (inline): SYNTAX ERROR:`, err.message);
      console.error(err.stack);
      hasErrors = true;
      const lines = body.split('\n');
      console.error('  Lines:');
      for (let i = 0; i < Math.min(lines.length, 30); i++) {
        console.error(`    ${i+1}: ${lines[i]}`);
      }
    }
  }

  if (hasErrors) {
    console.error(`FAILED: ${filepath} has syntax errors!`);
    process.exit(1);
  } else {
    console.log(`SUCCESS: All ${count} scripts in ${filepath} passed syntax check!`);
  }
}

checkFile('blogger_theme/theme_preview.html');
checkFile('blogger_theme/kora_pro_blogger_theme.xml');

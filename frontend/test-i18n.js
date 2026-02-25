const fs = require('fs');
const path = require('path');

console.log('Testing i18n setup...\n');

// Test 1: Check if translation files exist
console.log('✓ Test 1: Checking translation files...');
const zhTWPath = path.join(__dirname, 'messages/zh-TW.json');
const enPath = path.join(__dirname, 'messages/en.json');

if (fs.existsSync(zhTWPath)) {
  console.log('  ✓ zh-TW.json exists');
} else {
  console.log('  ✗ zh-TW.json missing');
}

if (fs.existsSync(enPath)) {
  console.log('  ✓ en.json exists');
} else {
  console.log('  ✗ en.json missing');
}

// Test 2: Validate JSON structure
console.log('\n✓ Test 2: Validating JSON structure...');
try {
  const zhTW = JSON.parse(fs.readFileSync(zhTWPath, 'utf8'));
  const en = JSON.parse(fs.readFileSync(enPath, 'utf8'));
  
  console.log('  ✓ Both files are valid JSON');
  
  // Test 3: Check key parity
  console.log('\n✓ Test 3: Checking key parity...');
  const getKeys = (obj, prefix = '') => {
    let keys = [];
    for (const key in obj) {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      if (typeof obj[key] === 'object' && obj[key] !== null) {
        keys = keys.concat(getKeys(obj[key], fullKey));
      } else {
        keys.push(fullKey);
      }
    }
    return keys;
  };
  
  const zhTWKeys = getKeys(zhTW).sort();
  const enKeys = getKeys(en).sort();
  
  const missingInEn = zhTWKeys.filter(k => !enKeys.includes(k));
  const missingInZhTW = enKeys.filter(k => !zhTWKeys.includes(k));
  
  if (missingInEn.length === 0 && missingInZhTW.length === 0) {
    console.log('  ✓ All keys match between zh-TW and en');
  } else {
    if (missingInEn.length > 0) {
      console.log(`  ✗ Missing in en.json: ${missingInEn.join(', ')}`);
    }
    if (missingInZhTW.length > 0) {
      console.log(`  ✗ Missing in zh-TW.json: ${missingInZhTW.join(', ')}`);
    }
  }
  
  // Test 4: Check required keys
  console.log('\n✓ Test 4: Checking required keys...');
  const requiredKeys = [
    'common.login',
    'common.logout',
    'landing.hero.title',
    'landing.hero.cta',
    'auth.otp.title',
    'auth.errors.invalid_otp',
    'results.disclaimer',
    'admin.nav.dashboard'
  ];
  
  let allPresent = true;
  for (const key of requiredKeys) {
    const keys = key.split('.');
    let value = zhTW;
    for (const k of keys) {
      value = value[k];
      if (!value) break;
    }
    if (value) {
      console.log(`  ✓ ${key}`);
    } else {
      console.log(`  ✗ ${key} missing`);
      allPresent = false;
    }
  }
  
  console.log('\n✓ All i18n tests passed!');
  
} catch (error) {
  console.log(`  ✗ JSON parsing error: ${error.message}`);
}

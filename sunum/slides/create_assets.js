const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

async function createAssets() {
  const outDir = path.join(__dirname);

  // Title slide gradient - deep teal to dark blue
  const titleGrad = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720">
    <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0F4C75"/>
      <stop offset="50%" style="stop-color:#1B262C"/>
      <stop offset="100%" style="stop-color:#0F4C75"/>
    </linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  </svg>`;
  await sharp(Buffer.from(titleGrad)).png().toFile(path.join(outDir, 'bg-title.png'));

  // Product header gradient - teal accent bar
  const headerGrad = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="80">
    <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#0891B2"/>
      <stop offset="100%" style="stop-color:#0E7490"/>
    </linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  </svg>`;
  await sharp(Buffer.from(headerGrad)).png().toFile(path.join(outDir, 'bg-header-teal.png'));

  // Purple accent for FEMOBIOME
  const purpleGrad = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="80">
    <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#7B4B94"/>
      <stop offset="100%" style="stop-color:#5C3470"/>
    </linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  </svg>`;
  await sharp(Buffer.from(purpleGrad)).png().toFile(path.join(outDir, 'bg-header-purple.png'));

  // Blue accent for ANDROBIOME
  const blueGrad = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="80">
    <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#0EA5E9"/>
      <stop offset="100%" style="stop-color:#0284C7"/>
    </linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  </svg>`;
  await sharp(Buffer.from(blueGrad)).png().toFile(path.join(outDir, 'bg-header-blue.png'));

  // Closing slide gradient
  const closeGrad = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720">
    <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1B262C"/>
      <stop offset="50%" style="stop-color:#0F4C75"/>
      <stop offset="100%" style="stop-color:#1B262C"/>
    </linearGradient></defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  </svg>`;
  await sharp(Buffer.from(closeGrad)).png().toFile(path.join(outDir, 'bg-close.png'));

  // DNA icon for title
  const dnaIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 100 100">
    <path d="M30 10 Q50 25 30 40 Q10 55 30 70 Q50 85 30 100" stroke="white" stroke-width="3" fill="none"/>
    <path d="M70 10 Q50 25 70 40 Q90 55 70 70 Q50 85 70 100" stroke="white" stroke-width="3" fill="none"/>
    <line x1="30" y1="20" x2="70" y2="20" stroke="white" stroke-width="2" opacity="0.7"/>
    <line x1="35" y1="35" x2="65" y2="35" stroke="white" stroke-width="2" opacity="0.7"/>
    <line x1="30" y1="50" x2="70" y2="50" stroke="white" stroke-width="2" opacity="0.7"/>
    <line x1="35" y1="65" x2="65" y2="65" stroke="white" stroke-width="2" opacity="0.7"/>
    <line x1="30" y1="80" x2="70" y2="80" stroke="white" stroke-width="2" opacity="0.7"/>
  </svg>`;
  await sharp(Buffer.from(dnaIcon)).png().toFile(path.join(outDir, 'icon-dna.png'));

  // Copy logo
  fs.copyFileSync(
    path.join(__dirname, '..', 'genomerlogo.png'),
    path.join(outDir, 'genomerlogo.png')
  );

  console.log('Assets created successfully');
}

createAssets().catch(console.error);

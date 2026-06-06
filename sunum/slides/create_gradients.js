const sharp = require('sharp');
const path = require('path');

async function createGradient(filename, color1, color2, direction = 'diagonal') {
  let gradientDef;
  if (direction === 'diagonal') {
    gradientDef = `<linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">`;
  } else {
    gradientDef = `<linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="0%">`;
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="810">
    <defs>
      ${gradientDef}
        <stop offset="0%" style="stop-color:${color1}"/>
        <stop offset="100%" style="stop-color:${color2}"/>
      </linearGradient>
    </defs>
    <rect width="100%" height="100%" fill="url(#g)"/>
  </svg>`;
  await sharp(Buffer.from(svg)).png().toFile(path.join(__dirname, filename));
  console.log(`Created ${filename}`);
}

async function createAccentBar(filename, color, width, height) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
    <rect width="100%" height="100%" fill="${color}" rx="0" ry="0"/>
  </svg>`;
  await sharp(Buffer.from(svg)).png().toFile(path.join(__dirname, filename));
  console.log(`Created ${filename}`);
}

(async () => {
  await createGradient('bg-gradient-dark.png', '#0F1A2E', '#1B3A5C', 'diagonal');
  await createGradient('bg-gradient-close.png', '#0F1A2E', '#1B3A5C', 'diagonal');
  await createAccentBar('accent-purple.png', '#7B4B94', 8, 405);
  await createAccentBar('accent-teal.png', '#0891B2', 8, 405);
  await createAccentBar('accent-blue.png', '#0EA5E9', 8, 405);
  console.log('All assets created.');
})();

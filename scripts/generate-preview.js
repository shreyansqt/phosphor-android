#!/usr/bin/env node
/**
 * Generate an interactive HTML preview of all Phosphor icons
 */

const fs = require('fs');
const path = require('path');

const ICONS_DIR = path.join(__dirname, '../icons');
const REGISTRY_FILE = path.join(__dirname, '../icons.json');
const OUTPUT_FILE = path.join(__dirname, '../index.html');

function vdToSvg(vdXml) {
  // Extract viewBox dimensions
  const widthMatch = vdXml.match(/android:viewportWidth="([^"]+)"/);
  const heightMatch = vdXml.match(/android:viewportHeight="([^"]+)"/);
  const viewportWidth = widthMatch ? widthMatch[1] : '256';
  const viewportHeight = heightMatch ? heightMatch[1] : '256';
  const viewBox = `0 0 ${viewportWidth} ${viewportHeight}`;

  // Extract paths with their attributes
  const pathRegex = /<path\s+([^>]*)android:pathData="([^"]*)"\s*([^>]*)\/>/g;
  let match;
  const paths = [];

  while ((match = pathRegex.exec(vdXml)) !== null) {
    const fullAttrs = match[1] + ' android:pathData="' + match[2] + '" ' + match[3];
    const pathData = match[2];

    // Extract stroke width
    const strokeWidthMatch = fullAttrs.match(/android:strokeWidth="([^"]+)"/);
    const strokeWidth = strokeWidthMatch ? strokeWidthMatch[1] : '16';

    // Determine if stroke or fill
    const isStroke = fullAttrs.includes('android:strokeColor');

    if (isStroke) {
      paths.push(
        `  <path fill="none" stroke="currentColor" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" d="${pathData}" />`
      );
    } else {
      paths.push(`  <path fill="currentColor" d="${pathData}" />`);
    }
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="48" height="48" preserveAspectRatio="xMidYMid meet" overflow="visible">
${paths.join('\n')}
</svg>`;
}

function generatePreview() {
  const registry = JSON.parse(fs.readFileSync(REGISTRY_FILE, 'utf8'));
  const icons = registry.icons;

  const iconCards = icons
    .map((icon) => {
      const vdPath = path.join(ICONS_DIR, 'phosphor_' + icon.name + '.xml');
      let vdXml = '';
      try {
        vdXml = fs.readFileSync(vdPath, 'utf8');
      } catch (e) {
        return '';
      }

      const svg = vdToSvg(vdXml);
      const escaped = svg.replace(/"/g, '&quot;');

      return `
        <div class="icon-card" data-name="${icon.name}" data-keywords="${icon.keywords.join(', ')}">
          <div class="icon-preview">${svg}</div>
          <p class="icon-name">${icon.name}</p>
        </div>
      `;
    })
    .join('\n');

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Phosphor Icons for Android</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #fafafa;
      padding: 20px;
      color: #333;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
    }

    h1 {
      text-align: center;
      margin-bottom: 30px;
      font-size: 2em;
    }

    .search-box {
      margin-bottom: 30px;
      text-align: center;
    }

    .search-box input {
      padding: 12px 20px;
      font-size: 16px;
      border: 2px solid #ddd;
      border-radius: 8px;
      width: 100%;
      max-width: 400px;
      transition: border-color 0.2s;
    }

    .search-box input:focus {
      outline: none;
      border-color: #333;
    }

    .icon-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
      gap: 15px;
      margin-bottom: 40px;
    }

    .icon-card {
      background: white;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 15px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
    }

    .icon-card:hover {
      border-color: #333;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      transform: translateY(-2px);
    }

    .icon-card.hidden {
      display: none;
    }

    .icon-preview {
      width: 48px;
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #333;
      overflow: visible;
    }

    .icon-preview svg {
      width: 100%;
      height: 100%;
      overflow: visible;
    }

    .icon-name {
      font-size: 12px;
      color: #666;
      word-break: break-word;
      font-weight: 500;
    }

    .stats {
      text-align: center;
      color: #999;
      font-size: 14px;
      margin-bottom: 20px;
    }

    .no-results {
      text-align: center;
      color: #999;
      padding: 40px 20px;
      font-size: 16px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Phosphor Icons for Android</h1>
    
    <div class="search-box">
      <input 
        type="text" 
        id="search" 
        placeholder="Search icons by name..."
        autocomplete="off"
      />
    </div>

    <div class="stats">
      <span id="count">${icons.length}</span> icons
    </div>

    <div class="icon-grid" id="grid">
      ${iconCards}
    </div>

    <div class="no-results" id="no-results" style="display: none;">
      No icons found. Try a different search.
    </div>
  </div>

  <script>
    const grid = document.getElementById('grid');
    const cards = Array.from(document.querySelectorAll('.icon-card'));
    const search = document.getElementById('search');
    const count = document.getElementById('count');
    const noResults = document.getElementById('no-results');

    search.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase().trim();

      let visible = 0;
      cards.forEach((card) => {
        const name = card.dataset.name;
        const keywords = card.dataset.keywords;
        const matches = name.includes(query) || keywords.includes(query);

        if (matches && query.length > 0) {
          card.classList.remove('hidden');
          visible++;
        } else if (!query) {
          card.classList.remove('hidden');
          visible++;
        } else {
          card.classList.add('hidden');
        }
      });

      count.textContent = visible;
      noResults.style.display = visible === 0 && query ? 'block' : 'none';
    });

    // Allow clicking to copy icon name
    cards.forEach((card) => {
      card.addEventListener('click', () => {
        const name = 'phosphor_' + card.dataset.name;
        navigator.clipboard.writeText(name);
        const original = card.textContent;
        card.textContent = 'Copied!';
        setTimeout(() => {
          card.textContent = original;
        }, 1000);
      });
    });
  </script>
</body>
</html>`;

  fs.writeFileSync(OUTPUT_FILE, html);
  console.log('Preview generated: ' + OUTPUT_FILE);
}

generatePreview();

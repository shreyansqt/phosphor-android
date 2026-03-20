#!/usr/bin/env node
/**
 * Update the icon grid in index.html with current icons from icons.json and VD files
 * Preserves design/styling while only updating the grid content
 */

const fs = require('fs');
const path = require('path');

const ICONS_DIR = path.join(__dirname, '../icons');
const REGISTRY_FILE = path.join(__dirname, '../icons.json');
const OUTPUT_FILE = path.join(__dirname, '../index.html');

function vdToSvg(vdXml) {
  const widthMatch = vdXml.match(/android:viewportWidth="([^"]+)"/);
  const heightMatch = vdXml.match(/android:viewportHeight="([^"]+)"/);
  const viewportWidth = widthMatch ? widthMatch[1] : '256';
  const viewportHeight = heightMatch ? heightMatch[1] : '256';
  const viewBox = `0 0 ${viewportWidth} ${viewportHeight}`;

  const pathRegex = /<path\s+([^>]*)android:pathData="([^"]*)"\s*([^>]*)\/>/g;
  let match;
  const paths = [];

  while ((match = pathRegex.exec(vdXml)) !== null) {
    const fullAttrs = match[1] + ' android:pathData="' + match[2] + '" ' + match[3];
    const pathData = match[2];

    const strokeWidthMatch = fullAttrs.match(/android:strokeWidth="([^"]+)"/);
    const strokeWidth = strokeWidthMatch ? strokeWidthMatch[1] : '16';
    const isStroke = fullAttrs.includes('android:strokeColor');

    if (isStroke) {
      paths.push(
        `  <path fill="none" stroke="currentColor" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" d="${pathData}" />`
      );
    } else {
      paths.push(`  <path fill="currentColor" d="${pathData}" />`);
    }
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="256" height="256" preserveAspectRatio="xMidYMid meet">
${paths.join('\n')}
</svg>`;
}

function generateIcons() {
  const registry = JSON.parse(fs.readFileSync(REGISTRY_FILE, 'utf8'));
  const icons = registry.icons;

  const iconCards = icons
    .map((icon) => {
      const vdPath = path.join(ICONS_DIR, `phosphor_${icon.name}.xml`);
      let vdXml = '';
      try {
        vdXml = fs.readFileSync(vdPath, 'utf8');
      } catch (e) {
        return '';
      }

      const svg = vdToSvg(vdXml);
      const keywords = icon.keywords.filter(kw => kw !== icon.name).join(', ');
      return `
                    <div class="icon-card" onclick="copyXML('${icon.name}')" data-name="${icon.name}" data-keywords="${keywords}">
                        <div class="icon-preview">${svg}</div>
                        <p class="icon-name">${icon.name}</p>
                        <div class="copy-hint">Click to copy XML</div>
                    </div>
                `;
    })
    .join('\n');

  return { icons: icons.length, html: iconCards };
}

function updatePage() {
  const { icons: count, html: iconGrid } = generateIcons();
  let pageContent = fs.readFileSync(OUTPUT_FILE, 'utf8');

  // Update the grid content (between <!-- ICONS_START --> and <!-- ICONS_END -->)
  if (pageContent.includes('<!-- ICONS_START -->')) {
    const gridRegex = /<!-- ICONS_START -->[\s\S]*?<!-- ICONS_END -->/;
    pageContent = pageContent.replace(
      gridRegex,
      `<!-- ICONS_START -->\n${iconGrid}\n                <!-- ICONS_END -->`
    );
  } else {
    // Fallback: if markers don't exist, update the grid div
    const gridRegex = /<div class="icon-grid" id="grid">[\s\S]*?<\/div>/;
    pageContent = pageContent.replace(
      gridRegex,
      `<div class="icon-grid" id="grid">\n${iconGrid}\n        </div>`
    );
  }

  // Update icon count
  pageContent = pageContent.replace(
    /id="count">Loading icons\.\.\.<\/span>/,
    `id="count">${count} icons</span>`
  );

  fs.writeFileSync(OUTPUT_FILE, pageContent);
  console.log(`Preview updated: ${count} icons`);
}

updatePage();

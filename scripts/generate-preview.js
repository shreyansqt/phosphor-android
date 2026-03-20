#!/usr/bin/env node
/**
 * Update the icon grid in index.html with current icons from icons.json and VD files
 * Preserves design/styling while only updating the grid content
 */

const fs = require('fs');
const path = require('path');

const ICONS_DIR = path.join(__dirname, "..", "xmls"');
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

  // Also load VD files to inline
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
      
      // Escape XML for data attribute
      const vdEscaped = vdXml.replace(/"/g, '&quot;').replace(/\n/g, '');
      
      return `
                    <div class="icon-card" onclick="copyXML('${icon.name}')" data-name="${icon.name}" data-keywords="${keywords}" data-vd="${vdEscaped}">
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
  const startMarker = '<!-- ICONS_START -->';
  const endMarker = '<!-- ICONS_END -->';
  
  if (pageContent.includes(startMarker) && pageContent.includes(endMarker)) {
    const start = pageContent.indexOf(startMarker);
    const end = pageContent.indexOf(endMarker);
    if (start !== -1 && end !== -1) {
      const before = pageContent.substring(0, start + startMarker.length);
      const after = pageContent.substring(end);
      pageContent = before + '\n' + iconGrid + '\n                ' + after;
    }
  }

  // Update icon count
  pageContent = pageContent.replace(
    /id="count">[^<]*<\/span>/,
    `id="count">${count} icons</span>`
  );

  fs.writeFileSync(OUTPUT_FILE, pageContent);
  console.log(`Preview updated: ${count} icons`);
}

updatePage();

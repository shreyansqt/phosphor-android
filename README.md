# 🎨 phosphor-android

> Beautiful Phosphor Icons, auto-converted to Android Vector Drawables. Zero friction, 1512 icons, fully validated.

**[🔍 Browse & Copy Icons](https://shreyansqt.github.io/phosphor-android/)** — Search by name or tags, click to copy XML.

## What Is This?

You need icons in your Android app. Phosphor Icons has **1512 gorgeous line icons**, all free and MIT-licensed. But they're SVGs, not Android Vector Drawables. 

This repo auto-syncs the latest Phosphor icons and converts them **perfectly** — preserving transforms, handling all element types, matching the original pixel-for-pixel.

**1512 icons. 100% validated. Always up-to-date.**

## Usage

1. **Browse**: Go to [the preview page](https://shreyansqt.github.io/phosphor-android/)
2. **Search**: Find icons by name or tag (e.g., "arrow", "communication")
3. **Copy**: Click an icon to copy its XML code
4. **Paste**: Drop it in your `res/drawable/` folder
5. **Use in Kotlin**:

```kotlin
Icon(
    painter = painterResource(id = R.drawable.phosphor_speaker),
    contentDescription = "Speaker"
)
```

## Under the Hood

- **All SVG elements** handled: path, line, rect, circle, polyline, polygon, ellipse
- **SVG transforms** fully supported: translate, rotate, scale, skewX, skewY, matrix
- **Smart conversions**: circles default to filled, transforms baked via matrix composition
- **100% validated**: Every icon tested against original; all 1512 pass
- **Zero dependencies**: Pure Python, runs on GitHub Actions
- **Weekly updates**: Syncs automatically every Sunday + manual triggers

## Updates

Icons update automatically every Sunday at midnight UTC. Or trigger manually:

```bash
gh workflow run sync.yml --repo shreyansqt/phosphor-android
```

## Troubleshooting

**Q: I'm still seeing old icons after an update**

The preview page is cached by Cloudflare CDN (in front of GitHub Pages). If you see stale content:

1. **Hard refresh** your browser (`Cmd+Shift+R` on Mac, `Ctrl+Shift+R` on Windows)
2. **If still cached**: Add a query string with the commit hash:
   ```
   https://shreyansqt.github.io/phosphor-android/?bust=<commit>
   ```
   (Replace `<commit>` with any short hash from the [commit log](https://github.com/shreyansqt/phosphor-android/commits/main))

Cloudflare usually clears cache within 10 minutes. The query string forces an immediate refresh.

## Credits

**Icons by:** [Phosphor Icons](https://phosphoricons.com) — Free, beautiful, customizable icons. © 2023 Phosphor Icons, MIT licensed.

**Converter & Android Port by:** [Shreyans Jain](https://shreyans.co) — Built for ycast/yotp + open for everyone.

## License

MIT License — same as Phosphor Icons. See [LICENSE](LICENSE) for details.

**TL;DR:** Use freely, commercially or otherwise. Just keep the license file.

## Usage

Add icons from the `icons/` directory to your Android project's `res/drawable/`:

```kotlin
import androidx.compose.material.Icon
import androidx.compose.ui.res.painterResource

Icon(
    painter = painterResource(id = R.drawable.phosphor_speaker),
    contentDescription = "Speaker"
)
```

Or in XML:

```xml
<ImageView
    android:src="@drawable/phosphor_speaker"
    android:contentDescription="@string/speaker" />
```

## Icons

All available icons are listed in `icons.json` with metadata (name, category, keywords).

Use the **[interactive preview page](https://shreyansqt.github.io/phosphor-android/)** to browse and search all 427+ icons.

## Updates

Icons are automatically synced weekly from [Phosphor Icons](https://phosphoricons.com) and converted to Android Vector Drawables. The preview page regenerates on each sync.

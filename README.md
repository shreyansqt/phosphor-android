# phosphor-android

Auto-synced [Phosphor Icons](https://phosphoricons.com) converted to Android Vector Drawables.

🎨 **[Preview all icons →](https://shreyansqt.github.io/phosphor-android/)**

## License

This project is based on [Phosphor Icons](https://github.com/phosphor-icons/core), which is licensed under the [MIT License](LICENSE).

**Attribution:** Phosphor Icons © 2023 Phosphor Icons. All icon assets are derived from the original Phosphor Icons library and converted to Android Vector Drawable format.

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

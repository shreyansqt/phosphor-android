# phosphor-android

Auto-synced Phosphor icons converted to Android Vector Drawables.

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

All available icons are listed in `icons.json` with metadata (name, category, keywords, variants).

## Updates

Icons are automatically synced weekly from [Phosphor Icons](https://phosphoricons.com) and converted to Android Vector Drawables.

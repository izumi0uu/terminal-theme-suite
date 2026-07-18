# Wallpaper Sources

These original SVG compositions are the editable sources for the bundled terminal
wallpapers. They contain no third-party artwork, text, logos, or trademarks.

On macOS, regenerate the package PNG files with:

```bash
for source in artwork/wallpapers/*.svg; do
  name=$(basename "$source" .svg)
  sips -s format png "$source" \
    --out "src/terminal_theme_suite/data/backgrounds/$name.png"
done
```

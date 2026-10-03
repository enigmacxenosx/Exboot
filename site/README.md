# Exboot landing page

A static, responsive product landing page for Exboot. The page uses the repository's existing icon at `../assets/exboot_icon_master.png` and links download actions to the latest GitHub release.

## Preview locally

From the repository root:

```bash
python3 -m http.server 4173 --directory site --bind 0.0.0.0
```

Then open `http://localhost:4173`.

## Publish

The `site/` directory is self-contained and can be used as the publish directory for GitHub Pages or any static host.

# Exboot landing page plan

## Product goal
Create a high-converting product landing page for Exboot, a Windows desktop utility that creates bootable and multi-boot USB media from genuine images. The primary CTA is the current GitHub release download; secondary CTAs point to documentation and source.

## Design direction
- **Design movement:** dark technical editorial / command-center interface.
- **Core principles:** calm authority, high signal-to-noise, transparent safety, and tactile controls.
- **Color philosophy:** midnight navy grounds the page in reliability; Exboot teal communicates action and verification; a restrained magenta edge echoes the existing icon without overwhelming the product.
- **Layout paradigm:** asymmetric hero with an anchored product card and a diagonal signal line, followed by wide editorial sections rather than repetitive centered cards.
- **Signature elements:** cyan “signal” rule, oversized condensed section labels, and glowing status dots/terminal-style metadata.
- **Interaction philosophy:** every interaction should feel like a deliberate operator action; buttons use clear verbs and links expose the next step.
- **Animation:** subtle reveal-on-scroll, slow ambient glow, and no motion required for comprehension; honor reduced-motion preferences.
- **Typography:** Space Grotesk for interface and body copy, Archivo Narrow for compact technical labels and oversized numerals.
- **Brand essence:** A safer, clearer way for Windows power users and technicians to turn genuine images into dependable boot media. Personality: precise, capable, candid.
- **Voice:** direct, technically fluent, never hype-heavy. Example: “Build the USB you meant to build.” / “Know the disk. Confirm the mode. Then write.”
- **Wordmark / logo:** Exboot wordmark paired with the existing upward-arrow USB shield icon from `assets/exboot_icon_master.png`.
- **Signature brand color:** Exboot teal `#18d7c3`.

## Project structure
- `site/index.html`: semantic landing-page content and CTA links.
- `site/styles.css`: responsive visual system, layout, typography, states, and motion.
- `site/script.js`: mobile navigation, scroll reveal, year, and lightweight UI behavior.
- `site/manus-routes.json`: route manifest for the root static page.

## Constraints
- Reuse the repository's existing icon; no invented product claims.
- Be explicit that writing media erases the selected USB disk.
- Keep download links pointed to the latest GitHub release and source repository.

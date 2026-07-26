# nutsheLLM brand guide

## Brand idea

**Your context, in a nutsheLLM.**

nutsheLLM treats excess context as the shell and task-critical meaning as the
kernel. It can trim the shell only when evidence shows the kernel survived.

Nuto is the product's cheeky acorn optimizer. Nuto makes the safety ladder easier
to remember without replacing its technical explanation.

## Voice

- Clever, concise, and technically honest.
- Use nutshell language for introductions, transitions, and success moments.
- Use direct, calm language for errors, limits, and validation failures.
- Never imply that Nuto independently reasons, chats, or performs work outside the
  actual nutsheLLM pipeline.
- Never publish unmeasured savings or quality claims.

Preferred phrases:

- “Crack open a stress test.”
- “Nuto is trimming the shell…”
- “Kernel intact.”
- “If the kernel cracks, step back.”
- “Compress the shell. Guard the kernel. Prove the answer.”

## Visual system

| Token | Value | Role |
| --- | --- | --- |
| Espresso | `#160f0a` | Main background and deepest outlines |
| Soft espresso | `#1d140e` | Section backgrounds |
| Walnut | `#382318` | Nuto's cap and structural accents |
| Shell caramel | `#b96f3f` | Nuto's body and secondary brand color |
| Golden shell | `#dda15e` | Main actions and headline emphasis |
| Warm cream | `#f4e4c8` | Primary text and Nuto's face |
| Moss | `#a8b85f` | Protected kernel and successful evidence |
| Muted bark | `#ad967e` | Supporting text |
| Coral | `#e37a5b` | Failures and destructive actions |

Display copy uses Space Grotesk. Technical labels, metrics, and evidence use IBM
Plex Mono. Both fonts are bundled with the frontend.

## Mascot usage

The canonical source is the reusable `Nuto` React SVG component. Four poses are
available: `hero`, `running`, `success`, and `cautious`. The standalone mark is
available under `frontend/public/brand/`.

- Give the full character breathing room equal to at least one eye width.
- Do not recolor the kernel to anything other than moss.
- Do not use Nuto as a replacement for a validation status or error message.
- Use the simplified head mark below 64 pixels.
- Respect reduced-motion preferences whenever Nuto is animated.

## Submission assets

- Open Graph cover: `frontend/public/brand/og-cover.png` (`1200×630`)
- Devpost thumbnail: `frontend/public/brand/devpost-thumbnail.png` (`1800×1200`)
- Editable SVG sources live alongside both raster files.

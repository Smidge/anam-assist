---
name: Anam Assist community documentation
colors:
  canvas: "#ffffff"
  surface: "#f3f7f9"
  ink: "#172c38"
  secondary: "#47616e"
  accent: "#006d93"
  line: "#d5e1e7"
  diagram: "#102d3b"
  diagram-surface: "#1d4354"
  diagram-control: "#21495b"
  diagram-control-hover: "#28566c"
  diagram-border: "#638797"
  diagram-line: "#49636e"
  diagram-connector: "#557788"
  diagram-text: "#f2f9fc"
  diagram-secondary: "#bbd4df"
  diagram-muted: "#b6d3e0"
  diagram-inactive: "#c2dce8"
  diagram-dot: "#9adcf3"
  focus: "#1689bc"
  focus-on-dark: "#9fddf7"
  selection: "#c5ecfa"
  link-hover: "#004a66"
  button-hover: "#005777"
  scrollbar: "#849eab"
typography:
  body: "system-ui, sans-serif"
  code: "ui-monospace, monospace"
spacing:
  unit: 8px
  section: 96px
radius:
  panel: 16px
  control: 8px
---

# Visual decisions

A familiar Home Assistant community documentation page. Preserve the integration's blue accent and straightforward system typography. White reading surfaces, generous margins and thin rules keep installation instructions easy to follow. The Vercel reference informed restrained separators and clear hierarchy only; its gradients and brand marks are not used.

The public page has its own scope. It does not restyle the integration panel. Use a split introduction with an interactive, explicitly illustrative request flow. Follow with a compact compatibility strip, installation steps, architectural boundaries, privacy and native disclosure-based troubleshooting. One blue primary action. No decorative icon cards or invented live screenshots.

At narrow widths, stack the introduction and diagram. Navigation wraps without hiding destinations. Native links and disclosures work without JavaScript. Visible keyboard focus, reduced-motion support and comfortable touch targets are required.

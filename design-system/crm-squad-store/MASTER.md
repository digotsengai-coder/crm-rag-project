# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** CRM Squad Store
**Generated:** 2026-09-08 20:42:03
**Category:** Medical Clinic

---

## Global Rules

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#003285` | `--color-primary` |
| Secondary | `#00A67E` | `--color-secondary` |
| Accent | `#FF7F3E` | `--color-accent` |
| Info | `#3B82F6` | `--color-info` |
| Success | `#10B981` | `--color-success` |
| Warning | `#FF7F3E` | `--color-warning` |
| Error | `#EF4444` | `--color-error` |
| Background | `#FAFBFC` | `--color-bg` |
| Alternate Background | `#F0F4F8` | `--color-bg-alt` |
| Card Background | `#FFFFFF` | `--color-bg-card` |
| Dark Background | `#1E3A5F` | `--color-bg-dark` |
| Text | `#1A202C` | `--color-text` |
| Muted Text | `#4A5568` | `--color-text-muted` |
| Subtle Text | `#718096` | `--color-text-subtle` |
| Border | `#E2E8F0` | `--color-border` |

**Color Notes:** Follow the UI/UX Pro Max Medical Clinic demo palette exactly; use blue for primary actions, teal for trust signals, amber sparingly, and navy for dark information areas.

### Typography

- **Heading Font:** Plus Jakarta Sans
- **Body Font:** DM Sans
- **Mood:** medical, clean, accessible, professional, healthcare, trustworthy
- **Google Fonts:** [Plus Jakarta Sans + DM Sans](https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700&display=swap)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700&display=swap');
```

### Spacing Variables

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` / `0.25rem` | Tight gaps |
| `--space-sm` | `8px` / `0.5rem` | Icon gaps, inline spacing |
| `--space-md` | `16px` / `1rem` | Standard padding |
| `--space-lg` | `24px` / `1.5rem` | Section padding |
| `--space-xl` | `32px` / `2rem` | Large gaps |
| `--space-2xl` | `48px` / `3rem` | Section margins |
| `--space-3xl` | `64px` / `4rem` | Hero padding |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, buttons |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #003285;
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: #003285;
  border: 2px solid #003285;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}
```

### Cards

```css
.card {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-md);
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease;
}

.input:focus {
  border-color: #003285;
  outline: none;
  box-shadow: 0 0 0 3px #3B82F633;
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

---

## Style Guidelines

**Style:** Accessible & Ethical

**Keywords:** Accessible, inclusive interface, high contrast, large text (16px+), keyboard navigation, screen reader friendly, accessibility standards aware, focus state, semantic

**Best For:** Government, healthcare, education, inclusive products, large audience, legal compliance, public

**Key Effects:** Clear focus rings (3-4px), ARIA labels, skip links, responsive design, reduced motion, 44x44px touch targets

### Page Pattern

**Pattern Name:** Trust & Authority + Conversion

- **Conversion Strategy:** Security badges. Case studies. Transparent pricing. Low-friction form. Provide pause/stop and stop the logo carousel on focus, hover, and reduced motion. Previous/next controls provide the keyboard equivalent; pause offscreen/hidden and render a static logo set under reduced motion.
- **CTA Placement:** Contact Sales / Get Quote (primary) + Nav
- **Section Order:** Hero (mission/credibility) > Proof (logos, certs, stats) > Solution overview > Clear CTA path

---

## Anti-Patterns (Do NOT Use)

- ❌ Outdated interface
- ❌ Confusing booking
- ❌ AI purple/pink gradients

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile

# Design Quality Checklist — Spetser AI

## Visual Hierarchy
- [ ] Primary text: 16px minimum
- [ ] Headings: h1=24px, h2=20px, h3=18px
- [ ] Secondary text: 14px
- [ ] Caption text: 12px minimum
- [ ] Line height: 1.5 for body, 1.25 for headings

## Color & Contrast
- [ ] Text contrast ratio ≥ 4.5:1 (WCAG AA)
- [ ] Large text contrast ratio ≥ 3:1
- [ ] Brand color (#01696D) used consistently
- [ ] Error states use #DC2626
- [ ] Warning states use #F59E0B
- [ ] Dark mode has equivalent contrast

## Spacing & Layout
- [ ] Base spacing unit: 8px
- [ ] Consistent padding: 16px, 24px, 32px
- [ ] Card border-radius: 12px
- [ ] Button border-radius: 8px
- [ ] Input border-radius: 8px
- [ ] Grid gap: 16px

## Interactions
- [ ] Hover states on all interactive elements
- [ ] Focus states visible (keyboard navigation)
- [ ] Active/pressed states
- [ ] Disabled states (opacity 0.5 + cursor not-allowed)
- [ ] Loading states (spinner or skeleton)
- [ ] Transition duration: 200-300ms
- [ ] Easing: cubic-bezier(0.4, 0, 0.2, 1)

## Touch & Mobile
- [ ] Touch targets ≥ 44px
- [ ] Comfortable touch targets: 48px
- [ ] No horizontal scroll on mobile
- [ ] Bottom navigation thumb-friendly
- [ ] Input fields don't get hidden by keyboard

## Accessibility
- [ ] ARIA labels on icon-only buttons
- [ ] Alt text on images
- [ ] Keyboard navigation works
- [ ] Screen reader announcements for dynamic content
- [ ] Color is not the only indicator of state

## RTL Support
- [ ] Layout flips correctly with dir="rtl"
- [ ] Icons that indicate direction flip (arrows, chevrons)
- [ ] Text alignment adjusts
- [ ] Padding/margin logical properties used

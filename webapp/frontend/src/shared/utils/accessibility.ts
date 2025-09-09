// Accessibility utilities and helpers
import { DEV } from "@/constants";

// Generate unique IDs for form elements
export function generateId(prefix: string = "id"): string {
  return `${prefix}-${Math.random().toString(36).substr(2, DEV.ID_RANDOM_LENGTH)}`;
}

// Announce changes to screen readers
export function announceToScreenReader(
  message: string,
  priority: "polite" | "assertive" = "polite",
): void {
  const announcement = document.createElement("div");
  announcement.setAttribute("aria-live", priority);
  announcement.setAttribute("aria-atomic", "true");
  announcement.setAttribute("role", "status");
  announcement.style.position = "absolute";
  announcement.style.left = "-10000px";
  announcement.style.width = "1px";
  announcement.style.height = "1px";
  announcement.style.overflow = "hidden";

  document.body.appendChild(announcement);
  announcement.textContent = message;

  // Remove after announcement
  setTimeout(() => {
    if (announcement.parentNode) {
      announcement.parentNode.removeChild(announcement);
    }
  }, 1000); // 1 second cleanup timeout
}

// Keyboard navigation helpers
export const KEYBOARD_KEYS = {
  ENTER: "Enter",
  SPACE: " ",
  TAB: "Tab",
  ESCAPE: "Escape",
  ARROW_UP: "ArrowUp",
  ARROW_DOWN: "ArrowDown",
  ARROW_LEFT: "ArrowLeft",
  ARROW_RIGHT: "ArrowRight",
  HOME: "Home",
  END: "End",
} as const;

export function isActionKey(key: string): boolean {
  return key === KEYBOARD_KEYS.ENTER || key === KEYBOARD_KEYS.SPACE;
}

// Focus management
export function focusFirstFocusableElement(container: HTMLElement): boolean {
  const focusableElements = container.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
  );

  const firstElement = focusableElements[0] as HTMLElement;
  if (firstElement) {
    firstElement.focus();
    return true;
  }
  return false;
}

export function trapFocus(container: HTMLElement, event: KeyboardEvent): void {
  const focusableElements = Array.from(
    container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    ),
  ) as HTMLElement[];

  if (focusableElements.length === 0) return;

  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];

  if (!firstElement || !lastElement) return;

  if (event.key === KEYBOARD_KEYS.TAB) {
    if (event.shiftKey) {
      if (document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      }
    } else {
      if (document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }
  }
}

// ARIA helpers
export function setAriaExpanded(element: HTMLElement, expanded: boolean): void {
  element.setAttribute("aria-expanded", expanded.toString());
}

export function setAriaSelected(element: HTMLElement, selected: boolean): void {
  element.setAttribute("aria-selected", selected.toString());
}

export function setAriaPressed(element: HTMLElement, pressed: boolean): void {
  element.setAttribute("aria-pressed", pressed.toString());
}

// Color contrast helpers (WCAG AA compliance)
export function getContrastRatio(color1: string, color2: string): number {
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);

  if (!rgb1 || !rgb2) return 0;

  const l1 = getRelativeLuminance(rgb1.r, rgb1.g, rgb1.b);
  const l2 = getRelativeLuminance(rgb2.r, rgb2.g, rgb2.b);

  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);

  return (lighter + 0.05) / (darker + 0.05);
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1]!, 16),
        g: parseInt(result[2]!, 16),
        b: parseInt(result[3]!, 16),
      }
    : null;
}

function getRelativeLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });

  return 0.2126 * rs! + 0.7152 * gs! + 0.0722 * bs!;
}

export function isContrastCompliant(
  color1: string,
  color2: string,
  level: "AA" | "AAA" = "AA",
): boolean {
  const ratio = getContrastRatio(color1, color2);
  return level === "AA" ? ratio >= 4.5 : ratio >= 7;
}

// Reduced motion detection
export function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// High contrast mode detection
export function prefersHighContrast(): boolean {
  return window.matchMedia("(prefers-contrast: high)").matches;
}

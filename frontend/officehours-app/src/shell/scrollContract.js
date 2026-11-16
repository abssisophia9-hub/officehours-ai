/**
 * Scroll contract for role shells (.bh-frame / .bh-main):
 * - Document (html/body) does not scroll while a frame is mounted.
 * - .bh-main is the primary wheel/trackpad/keyboard scroller.
 * - No wheel listeners call preventDefault on the page.
 *
 * Returns null when healthy; otherwise a short failure reason.
 */
export function checkMainScrollContract(root = document) {
  const frame = root.querySelector?.(".bh-frame");
  if (!frame) return "no .bh-frame";

  const main = frame.querySelector(".bh-main");
  if (!main) return "no .bh-main";

  const style = root.defaultView?.getComputedStyle?.(main);
  if (!style) return "no computed style";

  const overflowY = style.overflowY;
  if (overflowY !== "auto" && overflowY !== "scroll") {
    // Nested desk panes intentionally hide main overflow (sa-desk / tar-desk).
    if (main.querySelector(".sa-desk, .tar-desk")) return null;
    return `bh-main overflow-y is ${overflowY}`;
  }

  const minHeight = style.minHeight;
  if (minHeight === "auto") {
    // Flex item needs min-height: 0 (or equivalent) to shrink and scroll.
    const height = main.getBoundingClientRect().height;
    const frameHeight = frame.getBoundingClientRect().height;
    if (height > frameHeight + 1) {
      return "bh-main taller than frame (min-height not constraining)";
    }
  }

  return null;
}

/** Dev-only: warn once if the shell violates the scroll contract. */
export function assertMainScrollContract() {
  if (typeof import.meta === "undefined" || !import.meta.env?.DEV) return;
  if (typeof window === "undefined") return;
  window.requestAnimationFrame(() => {
    const problem = checkMainScrollContract(document);
    if (problem) {
      console.warn(`[scroll-contract] ${problem}`);
    }
  });
}

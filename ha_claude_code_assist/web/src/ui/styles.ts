import { css } from "lit";

/** Every component starts from these: type, box model and the focus ring. */
export const base = css`
  :host {
    box-sizing: border-box;
    font-family: var(--hca-font);
    color: var(--hca-text);
  }
  *,
  *::before,
  *::after {
    box-sizing: inherit;
  }
  :focus-visible {
    outline: none;
    box-shadow: var(--hca-focus);
  }
`;

/** Native form controls with the app's look. */
export const controls = css`
  input:not([type="checkbox"]),
  select,
  textarea {
    width: 100%;
    font: inherit;
    font-size: var(--hca-text-md);
    color: var(--hca-text);
    background: var(--hca-surface);
    border: 1px solid var(--hca-border-strong);
    border-radius: var(--hca-radius-sm);
    padding: 8px 10px;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  input:focus-visible,
  select:focus-visible,
  textarea:focus-visible {
    border-color: var(--hca-accent);
  }
  [aria-invalid="true"] {
    border-color: var(--hca-error);
  }
  ::placeholder {
    color: var(--hca-text-muted);
  }
  :disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

/** Label above the control, hint and error below: the layout of every field. */
export const field = css`
  .field {
    display: grid;
    gap: var(--hca-space-1);
  }
  label {
    font-size: var(--hca-text-sm);
    font-weight: 600;
  }
  .hint {
    font-size: var(--hca-text-xs);
    line-height: 1.45;
    color: var(--hca-text-muted);
  }
  .error {
    font-size: var(--hca-text-xs);
    color: var(--hca-error);
  }
`;

/**
 * Icon — Lucide-style stroke icons, hand-traced for this kit.
 * Usage: <Icon name="upload" /> or <Icon name="bell" size={18} />
 */

const PATHS = {
  upload:   <><path d="M12 16V4M12 4l-5 5M12 4l5 5"/><path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"/></>,
  bell:     <><path d="M18 16v-5a6 6 0 10-12 0v5l-2 2v1h16v-1l-2-2z"/><path d="M10 21a2 2 0 004 0"/></>,
  search:   <><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></>,
  arrow:    <><path d="M5 12h14M13 5l7 7-7 7"/></>,
  plus:     <><path d="M12 5v14M5 12h14"/></>,
  download: <><path d="M12 4v12M5 11l7 7 7-7"/><path d="M4 21h16"/></>,
  sparkle:  <><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z"/></>,
  bolt:     <><path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/></>,
  file:     <><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/></>,
  layers:   <><path d="M12 2l9 5-9 5-9-5 9-5z"/><path d="M3 12l9 5 9-5"/><path d="M3 17l9 5 9-5"/></>,
  history:  <><path d="M3 12a9 9 0 109-9 9.7 9.7 0 00-6.4 2.6L3 8"/><path d="M3 3v5h5"/><path d="M12 8v5l3 2"/></>,
  chart:    <><path d="M3 20h18"/><path d="M7 16V10M12 16V6M17 16v-3"/></>,
  check:    <><path d="M5 12l5 5L20 7"/></>,
  clock:    <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  spark:    <><path d="M5 3v4M3 5h4M19 17v4M17 19h4M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2 2-5z"/></>,
  book:     <><path d="M4 4v16a2 2 0 002 2h14V4H6a2 2 0 00-2 2z" fill="none"/><path d="M9 4v18"/></>,
  settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3h.1a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5h.1a1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8v.1a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z"/></>,
  notebook: <><path d="M19 3H8a2 2 0 00-2 2v14a2 2 0 002 2h11V3z"/><path d="M3 7h3M3 12h3M3 17h3"/></>,
  excel:    <><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/><path d="M9 13l6 6M15 13l-6 6"/></>,
  trending: <><path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/></>,
  package:  <><path d="M21 16V8L12 3 3 8v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/></>,
  bookmark: <><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></>,
  grid:     <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
  play:     <><path d="M5 3l14 9-14 9V3z"/></>,
  x:        <><path d="M18 6L6 18M6 6l12 12"/></>,
};

export default function Icon({ name, size = 20, ...rest }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...rest}
    >
      {PATHS[name]}
    </svg>
  );
}

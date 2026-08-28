/**
 * Once the backend is deployed to Render, replace this with its public
 * HTTPS URL, e.g. 'https://ubis-backend.onrender.com' — then the app works
 * over any network, not just this Wi-Fi.
 *
 * Local-dev fallback: "localhost" means the phone itself, so it will never
 * find your laptop — use your computer's LAN IP instead (phone and laptop
 * must be on the same Wi-Fi network).
 */
export const API_BASE = 'http://192.168.31.167:8000';

export const EVIDENCE_KINDS = [
  { key: 'face', label: 'Face photo', hint: 'Frontal, well-lit, one face in frame' },
  { key: 'fingerprint', label: 'Fingerprint', hint: 'Scanner image or dataset file' },
  { key: 'tattoo', label: 'Tattoo / scar', hint: 'Close-up with a scale reference' },
  { key: 'belonging', label: 'Belonging', hint: 'Clothing, bag, phone, documents' },
  { key: 'other', label: 'Other evidence', hint: 'Anything else relevant' },
] as const;


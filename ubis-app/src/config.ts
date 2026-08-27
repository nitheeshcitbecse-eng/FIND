/**
 * IMPORTANT: set API_BASE to your computer's LAN IP address.
 *
 * "localhost" means the phone itself, so it will never find your laptop.
 * Find your IP on Ubuntu with:   hostname -I
 * Then use e.g. http://192.168.1.42:8000
 *
 * Your phone and laptop must be on the same Wi-Fi network.
 */
export const API_BASE = 'http://192.168.31.167:8000';

export const EVIDENCE_KINDS = [
  { key: 'face', label: 'Face photo', hint: 'Frontal, well-lit, one face in frame' },
  { key: 'fingerprint', label: 'Fingerprint', hint: 'Scanner image or dataset file' },
  { key: 'tattoo', label: 'Tattoo / scar', hint: 'Close-up with a scale reference' },
  { key: 'belonging', label: 'Belonging', hint: 'Clothing, bag, phone, documents' },
  { key: 'other', label: 'Other evidence', hint: 'Anything else relevant' },
] as const;

export const MODALITY_LABELS: Record<string, string> = {
  fingerprint: 'Fingerprint',
  face: 'Face',
  tattoo: 'Tattoos / scars',
  belongings: 'Belongings',
  geo: 'Location',
  demographics: 'Demographics',
};
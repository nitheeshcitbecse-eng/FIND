export const theme = {
  bg: '#0A0E13',
  surface: '#141A22',
  surfaceAlt: '#1C242F',
  surfaceRaised: '#1A212B',
  border: '#242E3A',
  borderSoft: '#1C2530',
  text: '#EDF1F6',
  textDim: '#8D9BAC',
  accent: '#3B82F6',
  accentSoft: 'rgba(59, 130, 246, 0.14)',
  accentBorder: 'rgba(59, 130, 246, 0.35)',
  high: '#22C55E',
  highSoft: 'rgba(34, 197, 94, 0.14)',
  medium: '#F59E0B',
  mediumSoft: 'rgba(245, 158, 11, 0.14)',
  low: '#94A3B8',
  lowSoft: 'rgba(148, 163, 184, 0.14)',
  danger: '#EF4444',
  dangerSoft: 'rgba(239, 68, 68, 0.14)',
  radius: 14,
  radiusSm: 10,
  space: 16,
};

// Reusable elevation for cards — RN needs both the iOS shadow* props and the
// Android `elevation` prop; keeping this in one place avoids repeating both
// everywhere a card wants to look lifted off the background.
export const cardShadow = {
  shadowColor: '#000',
  shadowOffset: { width: 0, height: 8 },
  shadowOpacity: 0.28,
  shadowRadius: 16,
  elevation: 6,
};

export const softShadow = {
  shadowColor: '#000',
  shadowOffset: { width: 0, height: 3 },
  shadowOpacity: 0.2,
  shadowRadius: 6,
  elevation: 3,
};

export function softColor(band: string): string {
  if (band === 'high') return theme.highSoft;
  if (band === 'medium') return theme.mediumSoft;
  return theme.lowSoft;
}

export function confidenceColor(band: string): string {
  if (band === 'high') return theme.high;
  if (band === 'medium') return theme.medium;
  return theme.low;
}
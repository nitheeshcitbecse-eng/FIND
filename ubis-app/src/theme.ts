export const theme = {
  bg: '#0B0F14',
  surface: '#141A22',
  surfaceAlt: '#1C242F',
  border: '#26303C',
  text: '#E8EDF3',
  textDim: '#93A1B1',
  accent: '#3B82F6',
  high: '#22C55E',
  medium: '#F59E0B',
  low: '#94A3B8',
  danger: '#EF4444',
  radius: 12,
  space: 16,
};

export function confidenceColor(band: string): string {
  if (band === 'high') return theme.high;
  if (band === 'medium') return theme.medium;
  return theme.low;
}
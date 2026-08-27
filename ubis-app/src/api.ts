import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE } from './config';

const TOKEN_KEY = 'ubis.token';

export type User = { id: number; username: string; full_name: string; role: string };

export type PersonBrief = {
  id: number;
  record_ref: string;
  name: string;
  sex: string;
  age: number | null;
  last_known_city: string;
  face_photo_path: string | null;
};

export type Person = PersonBrief & {
  tattoo_description: string;
  known_belongings: string;
  notes: string;
  fingerprint_path: string | null;
};

export type Evidence = {
  id: number;
  kind: string;
  label: string;
  file_path: string;
  quality_score: number | null;
  extracted: Record<string, any> | null;
  created_at: string;
};

export type CaseBrief = {
  id: number;
  case_number: string;
  status: string;
  found_location: string;
  created_at: string;
};

export type CaseDetail = CaseBrief & {
  found_lat: number | null;
  found_lng: number | null;
  estimated_sex: string;
  estimated_age_min: number | null;
  estimated_age_max: number | null;
  tattoo_description: string;
  notes: string;
  identified_person_id: number | null;
  decision_note: string;
  evidence: Evidence[];
};

export type Component = {
  modality: string;
  score: number;
  weight: number;
  contribution: number;
  detail: string;
};

export type Candidate = {
  rank: number;
  score: number;
  confidence: string;
  person: PersonBrief;
  explanation: {
    components: Component[];
    coverage: number;
    margin_over_next: number | null;
    notes: string[];
  };
};

export type MatchRun = {
  run_id: number;
  case_id: number;
  created_at: string;
  engine_info: Record<string, any>;
  candidates: Candidate[];
};

export async function setToken(token: string | null) {
  if (token) await AsyncStorage.setItem(TOKEN_KEY, token);
  else await AsyncStorage.removeItem(TOKEN_KEY);
}

export async function getToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_KEY);
}

export function mediaUrl(path: string | null | undefined): string | undefined {
  if (!path) return undefined;
  return `${API_BASE}/media/${path}`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = { ...((init.headers as any) || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new Error(
      `Cannot reach the server at ${API_BASE}. Check API_BASE in src/config.ts and that both devices are on the same Wi-Fi.`
    );
  }

  if (response.status === 204) return undefined as T;

  const raw = await response.text();
  let body: any = null;
  try {
    body = raw ? JSON.parse(raw) : null;
  } catch {
    body = raw;
  }

  if (!response.ok) {
    const detail =
      typeof body?.detail === 'string'
        ? body.detail
        : Array.isArray(body?.detail)
        ? body.detail.map((d: any) => d.msg).join(', ')
        : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return body as T;
}

export async function login(username: string, password: string): Promise<string> {
  const form = new URLSearchParams();
  form.append('username', username);
  form.append('password', password);

  const data = await request<{ access_token: string }>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form.toString(),
  });
  await setToken(data.access_token);
  return data.access_token;
}

export const api = {
  me: () => request<User>('/auth/me'),

  listCases: () => request<CaseBrief[]>('/cases'),

  getCase: (id: number) => request<CaseDetail>(`/cases/${id}`),

  createCase: (payload: Record<string, any>) =>
    request<CaseDetail>('/cases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  updateCase: (id: number, payload: Record<string, any>) =>
    request<CaseDetail>(`/cases/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  uploadEvidence: async (
    caseId: number,
    kind: string,
    uri: string,
    label = ''
  ): Promise<Evidence> => {
    const name = uri.split('/').pop() || `${kind}.jpg`;
    const ext = (name.split('.').pop() || 'jpg').toLowerCase();
    const mime = ext === 'png' ? 'image/png' : ext === 'bmp' ? 'image/bmp' : 'image/jpeg';

    const form = new FormData();
    form.append('kind', kind);
    form.append('label', label);
    form.append('file', { uri, name, type: mime } as any);

    return request<Evidence>(`/cases/${caseId}/evidence`, { method: 'POST', body: form });
  },

  deleteEvidence: (caseId: number, evidenceId: number) =>
    request<void>(`/cases/${caseId}/evidence/${evidenceId}`, { method: 'DELETE' }),

  runMatch: (caseId: number) => request<MatchRun>(`/cases/${caseId}/match`, { method: 'POST' }),

  latestMatch: (caseId: number) => request<MatchRun>(`/cases/${caseId}/matches/latest`),

  getPerson: (id: number) => request<Person>(`/persons/${id}`),

  recordDecision: (caseId: number, payload: Record<string, any>) =>
    request<CaseDetail>(`/cases/${caseId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
};
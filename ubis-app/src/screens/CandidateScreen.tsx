import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';

import type { RootStackParamList } from '../../App';
import { api, Candidate, CaseDetail, mediaUrl, Person } from '../api';
import { useAuth } from '../auth';
import { MODALITY_LABELS } from '../config';
import { confidenceColor, theme } from '../theme';
import { runCache } from './ResultsScreen';

export default function CandidateScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const route = useRoute<RouteProp<RootStackParamList, 'Candidate'>>();
  const { caseId, candidateIndex } = route.params;
  const { user } = useAuth();

  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [person, setPerson] = useState<Person | null>(null);
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const run = runCache[caseId] || (await api.latestMatch(caseId));
      const selected = run.candidates[candidateIndex];
      if (!selected) throw new Error('Candidate not found');
      setCandidate(selected);

      const [personData, caseDetail] = await Promise.all([
        api.getPerson(selected.person.id),
        api.getCase(caseId),
      ]);
      setPerson(personData);
      setCaseData(caseDetail);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [caseId, candidateIndex]);

  useEffect(() => {
    load();
  }, [load]);

  const canDecide = user?.role === 'verifier' || user?.role === 'admin';

  const confirm = () => {
    if (!candidate) return;
    Alert.alert(
      'Confirm identification',
      `Record ${candidate.person.name} as the confirmed identity for this case? This is logged against your account.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Confirm',
          onPress: async () => {
            setBusy(true);
            setError('');
            try {
              await api.recordDecision(caseId, {
                person_id: candidate.person.id,
                decision_note: note,
              });
              navigation.navigate('Cases');
            } catch (e: any) {
              setError(e.message);
            } finally {
              setBusy(false);
            }
          },
        },
      ]
    );
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={theme.accent} size="large" />
      </View>
    );
  }

  if (error && !candidate) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error}</Text>
      </View>
    );
  }

  const caseFace = caseData?.evidence.find((e) => e.kind === 'face');
  const caseFinger = caseData?.evidence.find((e) => e.kind === 'fingerprint');
  const color = confidenceColor(candidate!.confidence);
  const components = [...candidate!.explanation.components].sort(
    (a, b) => b.contribution - a.contribution
  );

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <View style={styles.scoreCard}>
        <Text style={styles.candidateName}>{candidate!.person.name}</Text>
        <Text style={styles.candidateMeta}>
          {candidate!.person.record_ref} · rank #{candidate!.rank}
        </Text>
        <Text style={[styles.bigScore, { color }]}>
          {(candidate!.score * 100).toFixed(1)}%
        </Text>
        <View style={[styles.badge, { borderColor: color }]}>
          <Text style={[styles.badgeText, { color }]}>
            {candidate!.confidence} confidence
          </Text>
        </View>
        <Text style={styles.coverage}>
          Evidence coverage {(candidate!.explanation.coverage * 100).toFixed(0)}%
          {candidate!.explanation.margin_over_next != null
            ? ` · leads next candidate by ${(candidate!.explanation.margin_over_next * 100).toFixed(1)} pts`
            : ''}
        </Text>
      </View>

      <Text style={styles.section}>Side-by-side comparison</Text>
      <View style={styles.compareRow}>
        <View style={styles.compareCol}>
          <Text style={styles.compareLabel}>Case evidence</Text>
          <Image source={{ uri: mediaUrl(caseFace?.file_path) }} style={styles.compareImg} />
          {caseFinger ? (
            <Image
              source={{ uri: mediaUrl(caseFinger.file_path) }}
              style={[styles.compareImg, { marginTop: 8 }]}
            />
          ) : null}
        </View>
        <View style={styles.compareCol}>
          <Text style={styles.compareLabel}>Record</Text>
          <Image
            source={{ uri: mediaUrl(person?.face_photo_path) }}
            style={styles.compareImg}
          />
          {person?.fingerprint_path ? (
            <Image
              source={{ uri: mediaUrl(person.fingerprint_path) }}
              style={[styles.compareImg, { marginTop: 8 }]}
            />
          ) : null}
        </View>
      </View>

      <Text style={styles.section}>Why this candidate ranked here</Text>
      {components.map((component) => (
        <View key={component.modality} style={styles.componentCard}>
          <View style={styles.componentTop}>
            <Text style={styles.componentName}>
              {MODALITY_LABELS[component.modality] || component.modality}
            </Text>
            <Text style={styles.componentScore}>
              {(component.score * 100).toFixed(0)}%
            </Text>
          </View>
          <View style={styles.barTrack}>
            <View
              style={[styles.barFill, { width: `${Math.round(component.score * 100)}%` }]}
            />
          </View>
          <Text style={styles.componentDetail}>{component.detail}</Text>
          <Text style={styles.componentWeight}>
            weight {(component.weight * 100).toFixed(0)}% → contributes{' '}
            {(component.contribution * 100).toFixed(1)} pts of the final score
          </Text>
        </View>
      ))}

      <Text style={styles.section}>Cautions</Text>
      {candidate!.explanation.notes.map((noteText, i) => (
        <Text key={i} style={styles.note}>
          • {noteText}
        </Text>
      ))}

      {person?.tattoo_description || person?.notes ? (
        <>
          <Text style={styles.section}>Record details</Text>
          {person?.tattoo_description ? (
            <Text style={styles.note}>Marks on record: {person.tattoo_description}</Text>
          ) : null}
          {person?.known_belongings ? (
            <Text style={styles.note}>Known belongings: {person.known_belongings}</Text>
          ) : null}
          {person?.notes ? <Text style={styles.note}>{person.notes}</Text> : null}
        </>
      ) : null}

      <Text style={styles.section}>Verification decision</Text>
      {canDecide ? (
        <>
          <TextInput
            style={styles.input}
            value={note}
            onChangeText={setNote}
            multiline
            placeholder="Record the independent checks performed (dental records, family confirmation, DNA, documents…)"
            placeholderTextColor={theme.textDim}
          />
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <TouchableOpacity
            style={[styles.confirmButton, busy && { opacity: 0.6 }]}
            onPress={confirm}
            disabled={busy}
          >
            {busy ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.confirmText}>Record confirmed identification</Text>
            )}
          </TouchableOpacity>
        </>
      ) : (
        <Text style={styles.note}>
          Your role ({user?.role}) can capture and review evidence but cannot confirm an
          identification. Escalate to an authorized verifier.
        </Text>
      )}

      <Text style={styles.disclaimer}>
        This screen presents machine-generated leads. A confirmed identification requires
        independent verification under applicable legal procedure.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  center: { flex: 1, backgroundColor: theme.bg, justifyContent: 'center', padding: 24 },
  content: { padding: 16, paddingBottom: 48 },
  scoreCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 20,
    alignItems: 'center',
    gap: 6,
  },
  candidateName: { color: theme.text, fontSize: 20, fontWeight: '800' },
  candidateMeta: { color: theme.textDim, fontSize: 12 },
  bigScore: { fontSize: 44, fontWeight: '900', marginTop: 4 },
  badge: { borderWidth: 1, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4 },
  badgeText: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase' },
  coverage: { color: theme.textDim, fontSize: 11, textAlign: 'center', marginTop: 4 },
  section: {
    color: theme.text,
    fontSize: 16,
    fontWeight: '700',
    marginTop: 26,
    marginBottom: 10,
  },
  compareRow: { flexDirection: 'row', gap: 12 },
  compareCol: { flex: 1 },
  compareLabel: { color: theme.textDim, fontSize: 11, marginBottom: 6, textTransform: 'uppercase' },
  compareImg: {
    width: '100%',
    height: 160,
    borderRadius: 8,
    backgroundColor: theme.surfaceAlt,
    borderWidth: 1,
    borderColor: theme.border,
  },
  componentCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 14,
    marginBottom: 10,
    gap: 6,
  },
  componentTop: { flexDirection: 'row', justifyContent: 'space-between' },
  componentName: { color: theme.text, fontSize: 14, fontWeight: '700' },
  componentScore: { color: theme.text, fontSize: 14, fontWeight: '800' },
  barTrack: {
    height: 6,
    borderRadius: 3,
    backgroundColor: theme.surfaceAlt,
    overflow: 'hidden',
  },
  barFill: { height: 6, borderRadius: 3, backgroundColor: theme.accent },
  componentDetail: { color: theme.textDim, fontSize: 12, lineHeight: 18 },
  componentWeight: { color: theme.textDim, fontSize: 10 },
  note: { color: theme.textDim, fontSize: 12, lineHeight: 19, marginBottom: 6 },
  input: {
    backgroundColor: theme.surface,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.border,
    color: theme.text,
    padding: 14,
    fontSize: 14,
    minHeight: 100,
    textAlignVertical: 'top',
  },
  confirmButton: {
    backgroundColor: theme.high,
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginTop: 14,
  },
  confirmText: { color: '#052e16', fontWeight: '800', fontSize: 15 },
  error: { color: theme.danger, marginTop: 12, fontSize: 13, lineHeight: 18 },
  disclaimer: {
    color: theme.textDim,
    fontSize: 11,
    lineHeight: 17,
    marginTop: 24,
    textAlign: 'center',
  },
});
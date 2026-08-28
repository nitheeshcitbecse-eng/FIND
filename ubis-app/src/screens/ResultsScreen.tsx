import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useFocusEffect, useNavigation, useRoute } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';

import type { RootStackParamList } from '../../App';
import { api, MatchRun } from '../api';
import { useAuth } from '../auth';
import { confidenceColor, theme } from '../theme';

export default function ResultsScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const route = useRoute<RouteProp<RootStackParamList, 'Results'>>();
  const { caseId } = route.params;
  const { user } = useAuth();

  const [run, setRun] = useState<MatchRun | null>(null);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setError('');
      setRun(await api.latestMatch(caseId));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const canDecide = user?.role === 'verifier' || user?.role === 'admin';

  const decide = (confirmed: boolean) => {
    Alert.alert(
      confirmed ? 'Confirm identification' : 'Reject this match',
      confirmed
        ? `Record ${run?.address} as the confirmed identification for this case? This is logged against your account.`
        : 'Mark this case as closed / unidentified? This is logged against your account.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: confirmed ? 'Confirm' : 'Reject',
          style: confirmed ? 'default' : 'destructive',
          onPress: async () => {
            setBusy(true);
            setError('');
            try {
              await api.recordDecision(caseId, { confirmed, decision_note: note });
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

  if (error || !run) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error || 'No results yet.'}</Text>
      </View>
    );
  }

  const color = confidenceColor(run.confidence);

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <Text style={styles.headerMeta}>
        Generated {new Date(run.created_at).toLocaleString()} · gallery{' '}
        {run.engine_info.gallery_size ?? '?'} records
      </Text>

      {run.matched ? (
        <View style={styles.card}>
          <View style={[styles.badge, { borderColor: color }]}>
            <Text style={[styles.badgeText, { color }]}>{run.confidence} confidence</Text>
          </View>
          <Text style={[styles.score, { color }]}>{(run.score * 100).toFixed(1)}%</Text>
          <Text style={styles.addressLabel}>Registered address</Text>
          <Text style={styles.address}>{run.address}</Text>
        </View>
      ) : (
        <View style={styles.noMatchCard}>
          <Text style={styles.noMatchText}>No person found</Text>
        </View>
      )}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {run.matched ? (
        canDecide ? (
          <>
            <Text style={styles.section}>Verification decision</Text>
            <TextInput
              style={styles.input}
              value={note}
              onChangeText={setNote}
              multiline
              placeholder="Record the independent checks performed (family confirmation, documents…)"
              placeholderTextColor={theme.textDim}
            />
            <TouchableOpacity
              style={[styles.confirmButton, busy && { opacity: 0.6 }]}
              onPress={() => decide(true)}
              disabled={busy}
            >
              {busy ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.confirmText}>Record confirmed identification</Text>
              )}
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.rejectButton, busy && { opacity: 0.6 }]}
              onPress={() => decide(false)}
              disabled={busy}
            >
              <Text style={styles.rejectText}>Reject match / close as unidentified</Text>
            </TouchableOpacity>
          </>
        ) : (
          <Text style={styles.note}>
            Your role ({user?.role}) can capture and review evidence but cannot confirm an
            identification. Escalate to an authorized verifier.
          </Text>
        )
      ) : null}

      <Text style={styles.disclaimer}>
        This is a machine-generated lead, not a legal identification. A confirmed
        identification requires independent verification under applicable legal procedure.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  center: { flex: 1, backgroundColor: theme.bg, justifyContent: 'center', padding: 24 },
  content: { padding: 16, paddingBottom: 48, gap: 14 },
  headerMeta: { color: theme.textDim, fontSize: 11, lineHeight: 16 },
  card: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 20,
    alignItems: 'center',
    gap: 8,
  },
  badge: { borderWidth: 1, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4 },
  badgeText: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase' },
  score: { fontSize: 36, fontWeight: '900' },
  addressLabel: {
    color: theme.textDim,
    fontSize: 11,
    textTransform: 'uppercase',
    marginTop: 6,
  },
  address: { color: theme.text, fontSize: 16, fontWeight: '600', textAlign: 'center' },
  noMatchCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 24,
    alignItems: 'center',
  },
  noMatchText: { color: theme.textDim, fontSize: 16, fontWeight: '700' },
  section: { color: theme.text, fontSize: 16, fontWeight: '700', marginTop: 6 },
  input: {
    backgroundColor: theme.surface,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.border,
    color: theme.text,
    padding: 14,
    fontSize: 14,
    minHeight: 90,
    textAlignVertical: 'top',
  },
  confirmButton: {
    backgroundColor: theme.high,
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
  },
  confirmText: { color: '#052e16', fontWeight: '800', fontSize: 15 },
  rejectButton: {
    borderWidth: 1,
    borderColor: theme.danger,
    borderRadius: 8,
    padding: 14,
    alignItems: 'center',
  },
  rejectText: { color: theme.danger, fontWeight: '700', fontSize: 14 },
  note: { color: theme.textDim, fontSize: 12, lineHeight: 19 },
  error: { color: theme.danger, textAlign: 'center', lineHeight: 20 },
  disclaimer: {
    color: theme.textDim,
    fontSize: 11,
    lineHeight: 17,
    marginTop: 8,
    textAlign: 'center',
  },
});

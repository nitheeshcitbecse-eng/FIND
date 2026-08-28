import React, { useCallback, useState } from 'react';
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
import { useFocusEffect, useNavigation, useRoute } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';

import type { RootStackParamList } from '../../App';
import { api, MatchRun, mediaUrl } from '../api';
import { useAuth } from '../auth';
import { cardShadow, confidenceColor, softColor, softShadow, theme } from '../theme';

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
        ? `Record ${run?.name || 'this person'} (${run?.address}) as the confirmed identification for this case? This is logged against your account.`
        : 'Mark this case as not completed? This is logged against your account.',
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
          {run.photo_url ? (
            <Image source={{ uri: mediaUrl(run.photo_url) }} style={styles.photo} />
          ) : (
            <View style={[styles.photo, styles.photoEmpty]}>
              <Text style={styles.photoEmptyText}>No photo</Text>
            </View>
          )}
          <Text style={styles.name}>{run.name}</Text>
          <View style={[styles.badge, { backgroundColor: softColor(run.confidence) }]}>
            <Text style={[styles.badgeText, { color }]}>{run.confidence} confidence</Text>
          </View>
          <Text style={[styles.score, { color }]}>{(run.score * 100).toFixed(1)}%</Text>
          <View style={styles.addressBox}>
            <Text style={styles.addressLabel}>Registered address</Text>
            <Text style={styles.address}>{run.address}</Text>
          </View>
        </View>
      ) : (
        <View style={styles.noMatchCard}>
          <View style={styles.noMatchIcon}>
            <Text style={styles.noMatchIconText}>?</Text>
          </View>
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
              <Text style={styles.rejectText}>Reject match / mark not completed</Text>
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
    padding: 24,
    alignItems: 'center',
    gap: 10,
    ...cardShadow,
  },
  photo: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: theme.surfaceAlt,
    borderWidth: 2,
    borderColor: theme.border,
  },
  photoEmpty: { alignItems: 'center', justifyContent: 'center' },
  photoEmptyText: { color: theme.textDim, fontSize: 11 },
  name: { color: theme.text, fontSize: 20, fontWeight: '800', textAlign: 'center' },
  badge: { borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5 },
  badgeText: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase' },
  score: { fontSize: 40, fontWeight: '900' },
  addressBox: {
    width: '100%',
    marginTop: 4,
    padding: 14,
    borderRadius: theme.radiusSm,
    backgroundColor: theme.surfaceRaised,
    borderWidth: 1,
    borderColor: theme.borderSoft,
    alignItems: 'center',
  },
  addressLabel: {
    color: theme.textDim,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.4,
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  address: { color: theme.text, fontSize: 16, fontWeight: '600', textAlign: 'center' },
  noMatchCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 28,
    alignItems: 'center',
    gap: 12,
    ...softShadow,
  },
  noMatchIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: theme.lowSoft,
    alignItems: 'center',
    justifyContent: 'center',
  },
  noMatchIconText: { color: theme.low, fontSize: 22, fontWeight: '800' },
  noMatchText: { color: theme.textDim, fontSize: 16, fontWeight: '700' },
  section: {
    color: theme.text,
    fontSize: 15,
    fontWeight: '700',
    marginTop: 6,
    paddingLeft: 10,
    borderLeftWidth: 3,
    borderLeftColor: theme.accent,
  },
  input: {
    backgroundColor: theme.surface,
    borderRadius: theme.radiusSm,
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
    borderRadius: theme.radiusSm,
    padding: 16,
    alignItems: 'center',
    shadowColor: theme.high,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 4,
  },
  confirmText: { color: '#052e16', fontWeight: '800', fontSize: 15 },
  rejectButton: {
    backgroundColor: theme.dangerSoft,
    borderWidth: 1,
    borderColor: theme.danger,
    borderRadius: theme.radiusSm,
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

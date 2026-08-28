import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useFocusEffect, useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';

import type { RootStackParamList } from '../../App';
import { api, Evidence, MatchRun, mediaUrl } from '../api';
import { cardShadow, confidenceColor, softColor, softShadow, theme } from '../theme';

export default function FingerprintCheckScreen() {
  const route = useRoute<RouteProp<RootStackParamList, 'FingerprintCheck'>>();
  const { caseId, evidenceId } = route.params;

  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<MatchRun | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setError('');
      const caseData = await api.getCase(caseId);
      const ev = caseData.evidence.find((e) => e.id === evidenceId) || null;
      setEvidence(ev);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [caseId, evidenceId]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const checkMatch = async () => {
    setChecking(true);
    setError('');
    setResult(null);
    try {
      setResult(await api.matchFingerprint(caseId));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setChecking(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={theme.accent} size="large" />
      </View>
    );
  }

  if (!evidence) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>{error || 'Fingerprint evidence not found.'}</Text>
      </View>
    );
  }

  const template = evidence.extracted?.template;
  const detected = !!template?.descriptors_b64 && (template?.keypoint_count ?? 0) > 0;
  const quality = evidence.quality_score ?? template?.quality ?? null;

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <Image source={{ uri: mediaUrl(evidence.file_path) }} style={styles.preview} />

      <View style={styles.detectCard}>
        <View
          style={[
            styles.detectIcon,
            { backgroundColor: detected ? theme.highSoft : theme.dangerSoft },
          ]}
        >
          <Text style={{ color: detected ? theme.high : theme.danger, fontSize: 20, fontWeight: '800' }}>
            {detected ? '✓' : '✕'}
          </Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.detectTitle}>
            {detected ? 'Valid fingerprint detected' : 'No usable fingerprint detected'}
          </Text>
          <Text style={styles.detectMeta}>
            {template?.keypoint_count ?? 0} ridge features
            {quality != null ? ` · quality ${(quality * 100).toFixed(0)}%` : ''}
          </Text>
        </View>
      </View>

      <TouchableOpacity
        style={[styles.checkButton, (!detected || checking) && { opacity: 0.5 }]}
        onPress={checkMatch}
        disabled={!detected || checking}
      >
        {checking ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.checkButtonText}>Check for match in government database</Text>
        )}
      </TouchableOpacity>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {result ? (
        result.matched ? (
          <View style={styles.resultCard}>
            {result.photo_url ? (
              <Image source={{ uri: mediaUrl(result.photo_url) }} style={styles.photo} />
            ) : (
              <View style={[styles.photo, styles.photoEmpty]}>
                <Text style={styles.photoEmptyText}>No photo</Text>
              </View>
            )}
            <Text style={styles.name}>{result.name}</Text>
            <View style={[styles.badge, { backgroundColor: softColor(result.confidence) }]}>
              <Text style={[styles.badgeText, { color: confidenceColor(result.confidence) }]}>
                {result.confidence} confidence · {(result.score * 100).toFixed(1)}%
              </Text>
            </View>
            <View style={styles.addressBox}>
              <Text style={styles.addressLabel}>Registered address</Text>
              <Text style={styles.address}>{result.address}</Text>
            </View>
          </View>
        ) : (
          <View style={styles.noMatchCard}>
            <Text style={styles.noMatchText}>No person found</Text>
          </View>
        )
      ) : null}

      <Text style={styles.disclaimer}>
        A fingerprint-only quick check. It does not affect the case's main identification
        result — that still comes from "Run identification" on the case screen.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  center: { flex: 1, backgroundColor: theme.bg, justifyContent: 'center', padding: 24 },
  content: { padding: 16, paddingBottom: 48, gap: 14 },
  preview: {
    width: '100%',
    height: 220,
    borderRadius: theme.radius,
    backgroundColor: theme.surfaceAlt,
    borderWidth: 1,
    borderColor: theme.border,
  },
  detectCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 16,
    ...softShadow,
  },
  detectIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  detectTitle: { color: theme.text, fontSize: 15, fontWeight: '700' },
  detectMeta: { color: theme.textDim, fontSize: 12, marginTop: 2 },
  checkButton: {
    backgroundColor: theme.accent,
    borderRadius: theme.radiusSm,
    padding: 16,
    alignItems: 'center',
    shadowColor: theme.accent,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.32,
    shadowRadius: 10,
    elevation: 4,
  },
  checkButtonText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  resultCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 22,
    gap: 10,
    alignItems: 'center',
    ...cardShadow,
  },
  photo: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: theme.surfaceAlt,
    borderWidth: 2,
    borderColor: theme.border,
  },
  photoEmpty: { alignItems: 'center', justifyContent: 'center' },
  photoEmptyText: { color: theme.textDim, fontSize: 11 },
  name: { color: theme.text, fontSize: 18, fontWeight: '800', textAlign: 'center' },
  badge: { alignSelf: 'center', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5 },
  badgeText: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase' },
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
    padding: 24,
    alignItems: 'center',
    ...softShadow,
  },
  noMatchText: { color: theme.textDim, fontSize: 15, fontWeight: '700' },
  error: { color: theme.danger, textAlign: 'center', fontSize: 13, lineHeight: 18 },
  disclaimer: { color: theme.textDim, fontSize: 11, lineHeight: 17, textAlign: 'center' },
});

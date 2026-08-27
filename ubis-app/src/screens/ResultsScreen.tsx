import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useFocusEffect, useNavigation, useRoute } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';

import type { RootStackParamList } from '../../App';
import { api, Candidate, MatchRun, mediaUrl } from '../api';
import { MODALITY_LABELS } from '../config';
import { confidenceColor, theme } from '../theme';

export const runCache: Record<number, MatchRun> = {};

export default function ResultsScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const route = useRoute<RouteProp<RootStackParamList, 'Results'>>();
  const { caseId } = route.params;

  const [run, setRun] = useState<MatchRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setError('');
      const data = await api.latestMatch(caseId);
      runCache[caseId] = data;
      setRun(data);
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

  const topComponent = (candidate: Candidate) =>
    [...candidate.explanation.components].sort(
      (a, b) => b.contribution - a.contribution
    )[0];

  return (
    <FlatList
      style={styles.root}
      contentContainerStyle={{ padding: 16, paddingBottom: 40, gap: 12 }}
      data={run.candidates}
      keyExtractor={(item) => String(item.person.id)}
      ListHeaderComponent={
        <View style={styles.header}>
          <Text style={styles.headerTitle}>
            Top {run.candidates.length} candidates
          </Text>
          <Text style={styles.headerMeta}>
            Face: {run.engine_info.face} · Retrieval: {run.engine_info.retrieval} · Gallery:{' '}
            {run.engine_info.gallery_size} records
          </Text>
          <Text style={styles.headerMeta}>
            Generated {new Date(run.created_at).toLocaleString()}
          </Text>
        </View>
      }
      renderItem={({ item, index }) => {
        const top = topComponent(item);
        const color = confidenceColor(item.confidence);
        return (
          <TouchableOpacity
            style={styles.card}
            onPress={() =>
              navigation.navigate('Candidate', { caseId, candidateIndex: index })
            }
          >
            <Text style={styles.rank}>#{item.rank}</Text>
            <Image
              source={{ uri: mediaUrl(item.person.face_photo_path) }}
              style={styles.avatar}
            />
            <View style={{ flex: 1, gap: 4 }}>
              <Text style={styles.name}>{item.person.name}</Text>
              <Text style={styles.meta}>
                {item.person.record_ref} · {item.person.sex}
                {item.person.age ? `, ${item.person.age}y` : ''}
                {item.person.last_known_city ? ` · ${item.person.last_known_city}` : ''}
              </Text>

              <View style={styles.barTrack}>
                <View
                  style={[
                    styles.barFill,
                    { width: `${Math.round(item.score * 100)}%`, backgroundColor: color },
                  ]}
                />
              </View>

              <View style={styles.scoreRow}>
                <Text style={[styles.score, { color }]}>
                  {(item.score * 100).toFixed(1)}%
                </Text>
                <View style={[styles.badge, { borderColor: color }]}>
                  <Text style={[styles.badgeText, { color }]}>{item.confidence}</Text>
                </View>
              </View>

              {top ? (
                <Text style={styles.driver}>
                  Strongest signal: {MODALITY_LABELS[top.modality] || top.modality} (
                  {(top.score * 100).toFixed(0)}%)
                </Text>
              ) : null}
            </View>
          </TouchableOpacity>
        );
      }}
      ListFooterComponent={
        <Text style={styles.footer}>
          Tap a candidate for the full evidence breakdown. A confirmed identification must be
          recorded by an authorized verifier after independent checks.
        </Text>
      }
    />
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  center: { flex: 1, backgroundColor: theme.bg, justifyContent: 'center', padding: 24 },
  header: { gap: 4, marginBottom: 4 },
  headerTitle: { color: theme.text, fontSize: 18, fontWeight: '700' },
  headerMeta: { color: theme.textDim, fontSize: 11, lineHeight: 16 },
  card: {
    flexDirection: 'row',
    gap: 12,
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 14,
    alignItems: 'center',
  },
  rank: { color: theme.textDim, fontSize: 13, fontWeight: '700', width: 26 },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: theme.surfaceAlt,
    borderWidth: 1,
    borderColor: theme.border,
  },
  name: { color: theme.text, fontSize: 15, fontWeight: '700' },
  meta: { color: theme.textDim, fontSize: 11 },
  barTrack: {
    height: 6,
    borderRadius: 3,
    backgroundColor: theme.surfaceAlt,
    overflow: 'hidden',
    marginTop: 4,
  },
  barFill: { height: 6, borderRadius: 3 },
  scoreRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 2 },
  score: { fontSize: 14, fontWeight: '800' },
  badge: { borderWidth: 1, borderRadius: 20, paddingHorizontal: 8, paddingVertical: 2 },
  badgeText: { fontSize: 10, fontWeight: '700', textTransform: 'uppercase' },
  driver: { color: theme.textDim, fontSize: 11 },
  error: { color: theme.danger, textAlign: 'center', lineHeight: 20 },
  footer: {
    color: theme.textDim,
    fontSize: 11,
    lineHeight: 17,
    marginTop: 16,
    textAlign: 'center',
  },
});
import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useFocusEffect, useNavigation, useRoute } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';

import type { RootStackParamList } from '../../App';
import { api, CaseDetail, Evidence, mediaUrl } from '../api';
import { EVIDENCE_KINDS } from '../config';
import { theme } from '../theme';

export default function CaseDetailScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const route = useRoute<RouteProp<RootStackParamList, 'CaseDetail'>>();
  const { caseId } = route.params;

  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState<string | null>(null);
  const [matching, setMatching] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setError('');
      const data = await api.getCase(caseId);
      setCaseData(data);
      navigation.setOptions({ title: data.case_number });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [caseId, navigation]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const pickAndUpload = async (kind: string, fromCamera: boolean) => {
    setError('');
    try {
      if (fromCamera) {
        const permission = await ImagePicker.requestCameraPermissionsAsync();
        if (!permission.granted) {
          setError('Camera permission denied.');
          return;
        }
      }

      const result = fromCamera
        ? await ImagePicker.launchCameraAsync({ quality: 0.85, exif: false })
        : await ImagePicker.launchImageLibraryAsync({
            quality: 0.85,
            mediaTypes: ImagePicker.MediaTypeOptions.Images,
          });

      if (result.canceled || !result.assets?.length) return;

      setUploading(kind);
      const evidence = await api.uploadEvidence(caseId, kind, result.assets[0].uri);

      if (kind === 'face' && evidence.extracted?.faces_found === 0) {
        Alert.alert(
          'No face detected',
          'The system could not find a face in this photo. Try better lighting or a more frontal angle.'
        );
      }
      if (evidence.quality_score != null && evidence.quality_score < 0.35) {
        Alert.alert(
          'Low quality capture',
          `Quality score ${evidence.quality_score.toFixed(2)}. A better capture will improve matching accuracy.`
        );
      }
      await load();
    } catch (e: any) {
      setError(e.message || 'Upload failed');
    } finally {
      setUploading(null);
    }
  };

  const chooseSource = (kind: string, label: string) => {
    Alert.alert(label, 'Choose a source', [
      { text: 'Camera', onPress: () => pickAndUpload(kind, true) },
      { text: 'Gallery / files', onPress: () => pickAndUpload(kind, false) },
      { text: 'Cancel', style: 'cancel' },
    ]);
  };

  const removeEvidence = (evidence: Evidence) => {
    Alert.alert('Remove evidence', `Delete this ${evidence.kind} capture?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.deleteEvidence(caseId, evidence.id);
            await load();
          } catch (e: any) {
            setError(e.message);
          }
        },
      },
    ]);
  };

  const runMatch = async () => {
    setMatching(true);
    setError('');
    try {
      await api.runMatch(caseId);
      navigation.navigate('Results', { caseId });
    } catch (e: any) {
      setError(e.message || 'Matching failed');
    } finally {
      setMatching(false);
    }
  };

  if (loading || !caseData) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={theme.accent} size="large" />
      </View>
    );
  }

  const grouped = EVIDENCE_KINDS.map((kind) => ({
    ...kind,
    items: caseData.evidence.filter((e) => e.kind === kind.key),
  }));

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <View style={styles.summary}>
        <Text style={styles.summaryTitle}>{caseData.found_location || 'Location not recorded'}</Text>
        <Text style={styles.summaryLine}>
          Status: {caseData.status.replace('_', ' ')} · Sex estimate: {caseData.estimated_sex}
          {caseData.estimated_age_min != null || caseData.estimated_age_max != null
            ? ` · Age ${caseData.estimated_age_min ?? '?'}–${caseData.estimated_age_max ?? '?'}`
            : ''}
        </Text>
        {caseData.tattoo_description ? (
          <Text style={styles.summaryLine}>Marks: {caseData.tattoo_description}</Text>
        ) : null}
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {grouped.map((group) => (
        <View key={group.key} style={styles.group}>
          <View style={styles.groupHeader}>
            <View style={{ flex: 1 }}>
              <Text style={styles.groupTitle}>
                {group.label} {group.items.length > 0 ? `(${group.items.length})` : ''}
              </Text>
              <Text style={styles.groupHint}>{group.hint}</Text>
            </View>
            <TouchableOpacity
              style={styles.addButton}
              onPress={() => chooseSource(group.key, group.label)}
              disabled={uploading !== null}
            >
              {uploading === group.key ? (
                <ActivityIndicator color={theme.accent} size="small" />
              ) : (
                <Text style={styles.addButtonText}>+ Add</Text>
              )}
            </TouchableOpacity>
          </View>

          {group.items.length > 0 ? (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.strip}>
              {group.items.map((evidence) => (
                <TouchableOpacity
                  key={evidence.id}
                  style={styles.thumbWrap}
                  onLongPress={() => removeEvidence(evidence)}
                >
                  <Image source={{ uri: mediaUrl(evidence.file_path) }} style={styles.thumb} />
                  {evidence.quality_score != null ? (
                    <Text style={styles.thumbMeta}>
                      Q {evidence.quality_score.toFixed(2)}
                    </Text>
                  ) : null}
                  {evidence.extracted?.labels?.length ? (
                    <Text style={styles.thumbMeta} numberOfLines={1}>
                      {evidence.extracted.labels.slice(0, 2).join(', ')}
                    </Text>
                  ) : null}
                </TouchableOpacity>
              ))}
            </ScrollView>
          ) : null}
        </View>
      ))}

      <Text style={styles.hintSmall}>Long-press a thumbnail to remove it.</Text>

      <TouchableOpacity
        style={[
          styles.primaryButton,
          (matching || caseData.evidence.length === 0) && { opacity: 0.5 },
        ]}
        onPress={runMatch}
        disabled={matching || caseData.evidence.length === 0}
      >
        {matching ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.primaryButtonText}>Run identification</Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.secondaryButton}
        onPress={() => navigation.navigate('Results', { caseId })}
      >
        <Text style={styles.secondaryButtonText}>View last candidate list</Text>
      </TouchableOpacity>

      <Text style={styles.disclaimer}>
        Results are ranked leads for authorized human verification. They are not a legal
        identification.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  center: { flex: 1, backgroundColor: theme.bg, justifyContent: 'center' },
  content: { padding: 16, paddingBottom: 48 },
  summary: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 16,
    gap: 6,
    marginBottom: 20,
  },
  summaryTitle: { color: theme.text, fontSize: 16, fontWeight: '700' },
  summaryLine: { color: theme.textDim, fontSize: 13, lineHeight: 19 },
  group: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 14,
    marginBottom: 12,
  },
  groupHeader: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  groupTitle: { color: theme.text, fontSize: 15, fontWeight: '600' },
  groupHint: { color: theme.textDim, fontSize: 11, marginTop: 2 },
  addButton: {
    borderWidth: 1,
    borderColor: theme.accent,
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 8,
    minWidth: 64,
    alignItems: 'center',
  },
  addButtonText: { color: theme.accent, fontWeight: '700', fontSize: 13 },
  strip: { marginTop: 12 },
  thumbWrap: { marginRight: 10, width: 84 },
  thumb: {
    width: 84,
    height: 84,
    borderRadius: 8,
    backgroundColor: theme.surfaceAlt,
    borderWidth: 1,
    borderColor: theme.border,
  },
  thumbMeta: { color: theme.textDim, fontSize: 10, marginTop: 3 },
  hintSmall: { color: theme.textDim, fontSize: 11, marginBottom: 20 },
  primaryButton: {
    backgroundColor: theme.accent,
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
  },
  primaryButtonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  secondaryButton: { padding: 14, alignItems: 'center' },
  secondaryButtonText: { color: theme.accent, fontWeight: '600' },
  disclaimer: {
    color: theme.textDim,
    fontSize: 11,
    lineHeight: 17,
    marginTop: 12,
    textAlign: 'center',
  },
  error: { color: theme.danger, marginBottom: 14, fontSize: 13, lineHeight: 18 },
});
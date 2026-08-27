import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useShareIntentContext } from 'expo-share-intent';

import { api, FingerprintIdentifyResult } from '../api';
import { confidenceColor, theme } from '../theme';

const MODALITY_LABELS: Record<string, string> = {
  fingerprint: 'Fingerprint',
  face: 'Face photo',
};

export default function IdentifyScreen() {
  const { hasShareIntent, shareIntent, resetShareIntent } = useShareIntentContext();

  const [imageUri, setImageUri] = useState<string | null>(null);
  const [facePhotoUri, setFacePhotoUri] = useState<string | null>(null);
  const [result, setResult] = useState<FingerprintIdentifyResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [source, setSource] = useState<'shared' | 'manual' | null>(null);

  const identify = async (fpUri: string, faceUri?: string | null) => {
    setBusy(true);
    setError('');
    setResult(null);
    try {
      setResult(await api.identifyFingerprint(fpUri, faceUri));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  // A fingerprint capture app hands its scan to us via the Android share
  // sheet ("Share" -> UBIS Identification). As soon as that arrives, run the
  // 1:N lookup automatically — no manual step for the officer. A face photo
  // can still be added afterward to strengthen the check.
  useEffect(() => {
    if (!hasShareIntent) return;
    const file = shareIntent?.files?.[0];
    if (file?.path) {
      setImageUri(file.path);
      setFacePhotoUri(null);
      setSource('shared');
      identify(file.path);
    }
    resetShareIntent();
  }, [hasShareIntent, shareIntent]);

  const pickManually = async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      setError('Photo library permission is required to pick a fingerprint image.');
      return;
    }
    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 1,
    });
    if (picked.canceled || !picked.assets?.[0]) return;
    const uri = picked.assets[0].uri;
    setImageUri(uri);
    setFacePhotoUri(null);
    setSource('manual');
    identify(uri);
  };

  const addFacePhoto = async () => {
    if (!imageUri) return;
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      setError('Photo library permission is required to pick a face photo.');
      return;
    }
    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 1,
    });
    if (picked.canceled || !picked.assets?.[0]) return;
    const uri = picked.assets[0].uri;
    setFacePhotoUri(uri);
    identify(imageUri, uri);
  };

  const person = result?.person;

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <Text style={styles.hint}>
        Waiting for a fingerprint scan shared from the capture app — or pick an
        image to test manually.
      </Text>

      <View style={styles.previewRow}>
        <View style={{ flex: 1 }}>
          <Text style={styles.previewLabel}>Fingerprint</Text>
          {imageUri ? (
            <Image source={{ uri: imageUri }} style={styles.preview} />
          ) : (
            <View style={[styles.preview, styles.previewEmpty]}>
              <Text style={styles.previewEmptyText}>Waiting…</Text>
            </View>
          )}
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.previewLabel}>Face photo (optional)</Text>
          {facePhotoUri ? (
            <Image source={{ uri: facePhotoUri }} style={styles.preview} />
          ) : (
            <View style={[styles.preview, styles.previewEmpty]}>
              <Text style={styles.previewEmptyText}>Not added</Text>
            </View>
          )}
        </View>
      </View>

      <TouchableOpacity style={styles.pickButton} onPress={pickManually} disabled={busy}>
        <Text style={styles.pickButtonText}>Pick fingerprint image manually</Text>
      </TouchableOpacity>

      {imageUri ? (
        <TouchableOpacity style={styles.pickButton} onPress={addFacePhoto} disabled={busy}>
          <Text style={styles.pickButtonText}>
            {facePhotoUri ? 'Replace face photo' : 'Add face photo for a stronger check'}
          </Text>
        </TouchableOpacity>
      ) : null}

      {source === 'shared' ? (
        <Text style={styles.sourceTag}>Fingerprint received from the capture app</Text>
      ) : null}

      {busy ? (
        <View style={styles.center}>
          <ActivityIndicator color={theme.accent} size="large" />
          <Text style={styles.hint}>Matching against the reference database…</Text>
        </View>
      ) : null}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {result && !busy ? (
        result.matched && person ? (
          <View style={styles.resultCard}>
            <View style={[styles.badge, { borderColor: confidenceColor(result.confidence) }]}>
              <Text style={[styles.badgeText, { color: confidenceColor(result.confidence) }]}>
                {result.confidence} confidence · {(result.score * 100).toFixed(1)}%
              </Text>
            </View>
            <Text style={styles.name}>{person.name}</Text>
            <Text style={styles.meta}>{person.record_ref}</Text>

            <View style={styles.row}>
              <Text style={styles.label}>Address</Text>
              <Text style={styles.value}>{person.address || 'Not on record'}</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.label}>Last known city</Text>
              <Text style={styles.value}>{person.last_known_city || 'Unknown'}</Text>
            </View>
            <View style={styles.row}>
              <Text style={styles.label}>Sex / Age</Text>
              <Text style={styles.value}>
                {person.sex} · {person.age ?? 'unknown'}
              </Text>
            </View>
            {person.notes ? (
              <View style={styles.row}>
                <Text style={styles.label}>Notes</Text>
                <Text style={styles.value}>{person.notes}</Text>
              </View>
            ) : null}

            <Text style={styles.breakdownTitle}>Match breakdown</Text>
            {result.components.map((c) => (
              <View key={c.modality} style={styles.componentRow}>
                <Text style={styles.componentName}>
                  {MODALITY_LABELS[c.modality] || c.modality}
                </Text>
                <Text style={styles.componentScore}>{(c.score * 100).toFixed(0)}%</Text>
              </View>
            ))}
          </View>
        ) : (
          <View style={styles.noMatchCard}>
            <Text style={styles.noMatchText}>{result.message}</Text>
          </View>
        )
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  content: { padding: 16, paddingBottom: 48, gap: 14 },
  center: { alignItems: 'center', gap: 8, marginTop: 4 },
  hint: { color: theme.textDim, fontSize: 13, lineHeight: 19, textAlign: 'center' },
  preview: {
    width: '100%',
    height: 150,
    borderRadius: theme.radius,
    backgroundColor: theme.surfaceAlt,
    borderWidth: 1,
    borderColor: theme.border,
  },
  previewEmpty: { alignItems: 'center', justifyContent: 'center' },
  previewEmptyText: { color: theme.textDim, fontSize: 13 },
  previewRow: { flexDirection: 'row', gap: 12 },
  previewLabel: { color: theme.textDim, fontSize: 11, marginBottom: 6, textTransform: 'uppercase' },
  pickButton: {
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: 8,
    padding: 14,
    alignItems: 'center',
  },
  pickButtonText: { color: theme.accent, fontWeight: '700' },
  sourceTag: { color: theme.textDim, fontSize: 11, textAlign: 'center' },
  error: { color: theme.danger, fontSize: 13, textAlign: 'center' },
  resultCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 20,
    gap: 10,
  },
  badge: {
    alignSelf: 'center',
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 4,
  },
  badgeText: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase' },
  name: { color: theme.text, fontSize: 20, fontWeight: '800', textAlign: 'center' },
  meta: { color: theme.textDim, fontSize: 12, textAlign: 'center', marginBottom: 4 },
  row: { gap: 2 },
  label: { color: theme.textDim, fontSize: 11, textTransform: 'uppercase' },
  value: { color: theme.text, fontSize: 15, lineHeight: 20 },
  breakdownTitle: {
    color: theme.textDim,
    fontSize: 11,
    textTransform: 'uppercase',
    marginTop: 6,
  },
  componentRow: { flexDirection: 'row', justifyContent: 'space-between' },
  componentName: { color: theme.text, fontSize: 13 },
  componentScore: { color: theme.text, fontSize: 13, fontWeight: '700' },
  noMatchCard: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 20,
    alignItems: 'center',
  },
  noMatchText: { color: theme.textDim, fontSize: 14, textAlign: 'center' },
});

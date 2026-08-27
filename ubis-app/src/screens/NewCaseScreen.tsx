import React, { useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import * as Location from 'expo-location';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../App';
import { api } from '../api';
import { theme } from '../theme';

const SEXES = ['unknown', 'male', 'female'];

export default function NewCaseScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();

  const [location, setLocation] = useState('');
  const [lat, setLat] = useState<number | null>(null);
  const [lng, setLng] = useState<number | null>(null);
  const [sex, setSex] = useState('unknown');
  const [ageMin, setAgeMin] = useState('');
  const [ageMax, setAgeMax] = useState('');
  const [tattoo, setTattoo] = useState('');
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [gpsBusy, setGpsBusy] = useState(false);
  const [error, setError] = useState('');

  const useGps = async () => {
    setGpsBusy(true);
    setError('');
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setError('Location permission denied. You can type the location instead.');
        return;
      }
      const position = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      setLat(position.coords.latitude);
      setLng(position.coords.longitude);
    } catch (e: any) {
      setError(e.message || 'Could not read GPS');
    } finally {
      setGpsBusy(false);
    }
  };

  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      const created = await api.createCase({
        found_location: location,
        found_lat: lat,
        found_lng: lng,
        estimated_sex: sex,
        estimated_age_min: ageMin ? parseInt(ageMin, 10) : null,
        estimated_age_max: ageMax ? parseInt(ageMax, 10) : null,
        tattoo_description: tattoo,
        notes,
      });
      navigation.replace('CaseDetail', { caseId: created.id });
    } catch (e: any) {
      setError(e.message || 'Could not create case');
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScrollView style={styles.root} contentContainerStyle={styles.content}>
      <Text style={styles.section}>Recovery details</Text>

      <Text style={styles.label}>Location description</Text>
      <TextInput
        style={styles.input}
        value={location}
        onChangeText={setLocation}
        placeholder="e.g. Near Perungudi bus depot, Chennai"
        placeholderTextColor={theme.textDim}
      />

      <TouchableOpacity style={styles.ghostButton} onPress={useGps} disabled={gpsBusy}>
        <Text style={styles.ghostButtonText}>
          {gpsBusy
            ? 'Reading GPS…'
            : lat != null
            ? `GPS: ${lat.toFixed(5)}, ${lng?.toFixed(5)}`
            : 'Attach current GPS coordinates'}
        </Text>
      </TouchableOpacity>

      <Text style={styles.section}>Physical estimate</Text>

      <Text style={styles.label}>Apparent sex</Text>
      <View style={styles.row}>
        {SEXES.map((value) => (
          <TouchableOpacity
            key={value}
            style={[styles.chip, sex === value && styles.chipActive]}
            onPress={() => setSex(value)}
          >
            <Text style={[styles.chipText, sex === value && styles.chipTextActive]}>
              {value}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>Estimated age range</Text>
      <View style={styles.row}>
        <TextInput
          style={[styles.input, { flex: 1 }]}
          value={ageMin}
          onChangeText={setAgeMin}
          keyboardType="number-pad"
          placeholder="Min"
          placeholderTextColor={theme.textDim}
        />
        <TextInput
          style={[styles.input, { flex: 1 }]}
          value={ageMax}
          onChangeText={setAgeMax}
          keyboardType="number-pad"
          placeholder="Max"
          placeholderTextColor={theme.textDim}
        />
      </View>

      <Text style={styles.label}>Tattoos, scars, marks (text description)</Text>
      <TextInput
        style={[styles.input, styles.multiline]}
        value={tattoo}
        onChangeText={setTattoo}
        multiline
        placeholder="e.g. Om symbol tattoo on left forearm; surgical scar on right knee"
        placeholderTextColor={theme.textDim}
      />

      <Text style={styles.label}>Case notes</Text>
      <TextInput
        style={[styles.input, styles.multiline]}
        value={notes}
        onChangeText={setNotes}
        multiline
        placeholder="Condition, clothing, circumstances of recovery"
        placeholderTextColor={theme.textDim}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TouchableOpacity
        style={[styles.button, busy && { opacity: 0.6 }]}
        onPress={submit}
        disabled={busy}
      >
        {busy ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Create case &amp; add evidence</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  content: { padding: 16, paddingBottom: 48, gap: 8 },
  section: {
    color: theme.text,
    fontSize: 16,
    fontWeight: '700',
    marginTop: 20,
    marginBottom: 4,
  },
  label: { color: theme.textDim, fontSize: 12, marginTop: 12, textTransform: 'uppercase' },
  input: {
    backgroundColor: theme.surface,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.border,
    color: theme.text,
    padding: 14,
    fontSize: 15,
  },
  multiline: { minHeight: 90, textAlignVertical: 'top' },
  row: { flexDirection: 'row', gap: 10, marginTop: 4 },
  chip: {
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 9,
    backgroundColor: theme.surface,
  },
  chipActive: { backgroundColor: theme.accent, borderColor: theme.accent },
  chipText: { color: theme.textDim, fontSize: 13 },
  chipTextActive: { color: '#fff', fontWeight: '700' },
  ghostButton: {
    borderWidth: 1,
    borderColor: theme.accent,
    borderRadius: 8,
    padding: 14,
    alignItems: 'center',
    marginTop: 12,
  },
  ghostButtonText: { color: theme.accent, fontWeight: '600' },
  button: {
    backgroundColor: theme.accent,
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginTop: 28,
  },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  error: { color: theme.danger, marginTop: 14, fontSize: 13, lineHeight: 18 },
});
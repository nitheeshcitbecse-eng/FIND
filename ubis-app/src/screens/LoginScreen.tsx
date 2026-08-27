import React, { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import { useAuth } from '../auth';
import { API_BASE } from '../config';
import { theme } from '../theme';

export default function LoginScreen() {
  const { signIn } = useAuth();
  const [username, setUsername] = useState('officer1');
  const [password, setPassword] = useState('officer123');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      await signIn(username.trim(), password);
    } catch (e: any) {
      setError(e.message || 'Login failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.brand}>UBIS</Text>
        <Text style={styles.subtitle}>
          Unidentified Body Identification System — authorized personnel only
        </Text>

        <View style={styles.card}>
          <Text style={styles.label}>Username</Text>
          <TextInput
            style={styles.input}
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="officer1"
            placeholderTextColor={theme.textDim}
          />

          <Text style={styles.label}>Password</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholder="••••••••"
            placeholderTextColor={theme.textDim}
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <TouchableOpacity
            style={[styles.button, busy && styles.buttonDisabled]}
            onPress={submit}
            disabled={busy}
          >
            {busy ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Sign in</Text>
            )}
          </TouchableOpacity>
        </View>

        <Text style={styles.footer}>Server: {API_BASE}</Text>
        <Text style={styles.footer}>
          Demo accounts — officer1/officer123 (capture), verifier1/verify123 (can confirm
          identifications), admin/admin123
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  scroll: { padding: 24, paddingTop: 80, gap: 8 },
  brand: { color: theme.text, fontSize: 40, fontWeight: '800', letterSpacing: 4 },
  subtitle: { color: theme.textDim, fontSize: 14, marginBottom: 28, lineHeight: 20 },
  card: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 20,
    gap: 6,
  },
  label: { color: theme.textDim, fontSize: 12, marginTop: 10, textTransform: 'uppercase' },
  input: {
    backgroundColor: theme.surfaceAlt,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.border,
    color: theme.text,
    padding: 14,
    fontSize: 16,
  },
  button: {
    backgroundColor: theme.accent,
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginTop: 24,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  error: { color: theme.danger, marginTop: 12, fontSize: 13, lineHeight: 18 },
  footer: { color: theme.textDim, fontSize: 11, marginTop: 16, lineHeight: 16 },
});
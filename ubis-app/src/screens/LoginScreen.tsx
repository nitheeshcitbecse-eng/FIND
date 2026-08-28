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
import { cardShadow, theme } from '../theme';

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
        <View style={styles.badge}>
          <Text style={styles.badgeText}>U</Text>
        </View>
        <Text style={styles.brand}>UBIS</Text>
        <Text style={styles.subtitle}>
          Unidentified Body Identification System{'\n'}Authorized personnel only
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

        <View style={styles.footerCard}>
          <Text style={styles.footerLabel}>Server</Text>
          <Text style={styles.footerValue}>{API_BASE}</Text>
          <View style={styles.footerDivider} />
          <Text style={styles.footerLabel}>Demo accounts</Text>
          <Text style={styles.footerValue}>
            officer1 / officer123 (capture) · verifier1 / verify123 (confirm) · admin / admin123
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  scroll: { padding: 24, paddingTop: 72, gap: 8, alignItems: 'center' },
  badge: {
    width: 64,
    height: 64,
    borderRadius: 20,
    backgroundColor: theme.accentSoft,
    borderWidth: 1,
    borderColor: theme.accentBorder,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 18,
  },
  badgeText: { color: theme.accent, fontSize: 28, fontWeight: '800' },
  brand: { color: theme.text, fontSize: 34, fontWeight: '800', letterSpacing: 6 },
  subtitle: {
    color: theme.textDim,
    fontSize: 13,
    marginTop: 8,
    marginBottom: 32,
    lineHeight: 19,
    textAlign: 'center',
  },
  card: {
    width: '100%',
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 22,
    gap: 6,
    ...cardShadow,
  },
  label: {
    color: theme.textDim,
    fontSize: 11,
    marginTop: 14,
    marginBottom: 2,
    fontWeight: '700',
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
  input: {
    backgroundColor: theme.surfaceAlt,
    borderRadius: theme.radiusSm,
    borderWidth: 1,
    borderColor: theme.border,
    color: theme.text,
    padding: 14,
    fontSize: 16,
  },
  button: {
    backgroundColor: theme.accent,
    borderRadius: theme.radiusSm,
    padding: 16,
    alignItems: 'center',
    marginTop: 26,
    shadowColor: theme.accent,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 4,
  },
  buttonDisabled: { opacity: 0.6, shadowOpacity: 0 },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16, letterSpacing: 0.3 },
  error: { color: theme.danger, marginTop: 12, fontSize: 13, lineHeight: 18 },
  footerCard: {
    width: '100%',
    marginTop: 22,
    padding: 16,
    borderRadius: theme.radiusSm,
    backgroundColor: theme.surfaceRaised,
    borderWidth: 1,
    borderColor: theme.borderSoft,
    gap: 2,
  },
  footerLabel: {
    color: theme.textDim,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  footerValue: { color: theme.text, fontSize: 12, lineHeight: 17 },
  footerDivider: { height: 1, backgroundColor: theme.borderSoft, marginVertical: 10 },
  footer: { color: theme.textDim, fontSize: 11, marginTop: 16, lineHeight: 16 },
});
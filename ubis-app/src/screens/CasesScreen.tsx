import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

import type { RootStackParamList } from '../../App';
import { api, CaseBrief } from '../api';
import { useAuth } from '../auth';
import { theme } from '../theme';

const STATUS_COLORS: Record<string, string> = {
  open: theme.textDim,
  matched: theme.medium,
  identified: theme.high,
  closed_unidentified: theme.low,
};

export default function CasesScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const { user, signOut } = useAuth();
  const [cases, setCases] = useState<CaseBrief[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setError('');
      setCases(await api.listCases());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  React.useEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <TouchableOpacity onPress={signOut}>
          <Text style={{ color: theme.accent, fontSize: 15 }}>Sign out</Text>
        </TouchableOpacity>
      ),
    });
  }, [navigation, signOut]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={theme.accent} size="large" />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Text style={styles.hello}>
          {user?.full_name || user?.username} · {user?.role}
        </Text>
        <TouchableOpacity
          style={styles.newButton}
          onPress={() => navigation.navigate('NewCase')}
        >
          <Text style={styles.newButtonText}>+ New case</Text>
        </TouchableOpacity>
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <FlatList
        data={cases}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={{ padding: 16, gap: 12 }}
        refreshControl={
          <RefreshControl refreshing={false} onRefresh={load} tintColor={theme.accent} />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>
            No cases yet. Tap “New case” to register an unidentified body.
          </Text>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() => navigation.navigate('CaseDetail', { caseId: item.id })}
          >
            <View style={styles.cardTop}>
              <Text style={styles.caseNumber}>{item.case_number}</Text>
              <View
                style={[
                  styles.badge,
                  { borderColor: STATUS_COLORS[item.status] || theme.textDim },
                ]}
              >
                <Text
                  style={[
                    styles.badgeText,
                    { color: STATUS_COLORS[item.status] || theme.textDim },
                  ]}
                >
                  {item.status.replace('_', ' ')}
                </Text>
              </View>
            </View>
            <Text style={styles.location}>
              {item.found_location || 'Location not recorded'}
            </Text>
            <Text style={styles.date}>
              Registered {new Date(item.created_at).toLocaleString()}
            </Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.bg },
  center: { flex: 1, backgroundColor: theme.bg, justifyContent: 'center' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    paddingBottom: 0,
  },
  hello: { color: theme.textDim, fontSize: 13, flex: 1 },
  newButton: {
    backgroundColor: theme.accent,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
  },
  newButtonText: { color: '#fff', fontWeight: '700' },
  card: {
    backgroundColor: theme.surface,
    borderRadius: theme.radius,
    borderWidth: 1,
    borderColor: theme.border,
    padding: 16,
    gap: 6,
  },
  cardTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  caseNumber: { color: theme.text, fontSize: 16, fontWeight: '700' },
  badge: { borderWidth: 1, borderRadius: 20, paddingHorizontal: 10, paddingVertical: 3 },
  badgeText: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase' },
  location: { color: theme.text, fontSize: 14 },
  date: { color: theme.textDim, fontSize: 12 },
  empty: { color: theme.textDim, textAlign: 'center', marginTop: 60, lineHeight: 20 },
  error: { color: theme.danger, padding: 16, fontSize: 13 },
});
import 'react-native-gesture-handler';
import React from 'react';
import { ActivityIndicator, StatusBar, View } from 'react-native';
import {
  NavigationContainer,
  DarkTheme,
  useNavigationContainerRef,
} from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { ShareIntentProvider, useShareIntentContext } from 'expo-share-intent';

import { AuthProvider, useAuth } from './src/auth';
import { theme } from './src/theme';
import LoginScreen from './src/screens/LoginScreen';
import CasesScreen from './src/screens/CasesScreen';
import NewCaseScreen from './src/screens/NewCaseScreen';
import CaseDetailScreen from './src/screens/CaseDetailScreen';
import ResultsScreen from './src/screens/ResultsScreen';
import IdentifyScreen from './src/screens/IdentifyScreen';
import FingerprintCheckScreen from './src/screens/FingerprintCheckScreen';

export type RootStackParamList = {
  Login: undefined;
  Cases: undefined;
  NewCase: undefined;
  CaseDetail: { caseId: number };
  Results: { caseId: number; runFresh?: boolean };
  Identify: undefined;
  FingerprintCheck: { caseId: number; evidenceId: number };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

const navTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: theme.bg,
    card: theme.surface,
    text: theme.text,
    border: theme.border,
    primary: theme.accent,
  },
};

function Router() {
  const { user, loading } = useAuth();
  const { hasShareIntent } = useShareIntentContext();
  const navigationRef = useNavigationContainerRef<RootStackParamList>();

  // When a fingerprint capture app shares a scan in via Android's share
  // sheet, jump straight to the Identify screen so the officer doesn't have
  // to go hunting for it. If nobody is signed in yet, IdentifyScreen picks up
  // the same pending intent once it mounts after login.
  React.useEffect(() => {
    if (hasShareIntent && user && navigationRef.isReady()) {
      navigationRef.navigate('Identify');
    }
  }, [hasShareIntent, user, navigationRef]);

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.bg, justifyContent: 'center' }}>
        <ActivityIndicator color={theme.accent} size="large" />
      </View>
    );
  }

  return (
    <NavigationContainer ref={navigationRef} theme={navTheme}>
      <Stack.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: theme.surface },
          headerTitleStyle: { color: theme.text, fontSize: 17 },
          headerTintColor: theme.accent,
          contentStyle: { backgroundColor: theme.bg },
        }}
      >
        {!user ? (
          <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
        ) : (
          <>
            <Stack.Screen name="Cases" component={CasesScreen} options={{ title: 'Cases' }} />
            <Stack.Screen name="NewCase" component={NewCaseScreen} options={{ title: 'New Case' }} />
            <Stack.Screen name="CaseDetail" component={CaseDetailScreen} options={{ title: 'Case' }} />
            <Stack.Screen name="Results" component={ResultsScreen} options={{ title: 'Identification' }} />
            <Stack.Screen
              name="Identify"
              component={IdentifyScreen}
              options={{ title: 'Identify by Fingerprint' }}
            />
            <Stack.Screen
              name="FingerprintCheck"
              component={FingerprintCheckScreen}
              options={{ title: 'Fingerprint Analysis' }}
            />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <ShareIntentProvider>
      <AuthProvider>
        <StatusBar barStyle="light-content" backgroundColor={theme.surface} />
        <Router />
      </AuthProvider>
    </ShareIntentProvider>
  );
}
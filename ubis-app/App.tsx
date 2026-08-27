import 'react-native-gesture-handler';
import React from 'react';
import { ActivityIndicator, StatusBar, View } from 'react-native';
import { NavigationContainer, DarkTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { AuthProvider, useAuth } from './src/auth';
import { theme } from './src/theme';
import LoginScreen from './src/screens/LoginScreen';
import CasesScreen from './src/screens/CasesScreen';
import NewCaseScreen from './src/screens/NewCaseScreen';
import CaseDetailScreen from './src/screens/CaseDetailScreen';
import ResultsScreen from './src/screens/ResultsScreen';
import CandidateScreen from './src/screens/CandidateScreen';

export type RootStackParamList = {
  Login: undefined;
  Cases: undefined;
  NewCase: undefined;
  CaseDetail: { caseId: number };
  Results: { caseId: number; runFresh?: boolean };
  Candidate: { caseId: number; candidateIndex: number };
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

  if (loading) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.bg, justifyContent: 'center' }}>
        <ActivityIndicator color={theme.accent} size="large" />
      </View>
    );
  }

  return (
    <NavigationContainer theme={navTheme}>
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
            <Stack.Screen name="Results" component={ResultsScreen} options={{ title: 'Candidates' }} />
            <Stack.Screen name="Candidate" component={CandidateScreen} options={{ title: 'Comparison' }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <StatusBar barStyle="light-content" backgroundColor={theme.surface} />
      <Router />
    </AuthProvider>
  );
}
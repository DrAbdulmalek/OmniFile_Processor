/**
 * App.js
 * ======
 *
 * التطبيق الرئيسي للمراجعة المتنقلة.
 */

import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, SafeAreaView,
  StatusBar, Platform
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Provider as PaperProvider, DefaultTheme } from 'react-native-paper';
import AsyncStorage from '@react-native-async-storage/async-storage';

// الشاشات
import LoginScreen from './screens/LoginScreen';
import ReviewScreen from './screens/ReviewScreen';
import BatchScreen from './screens/BatchScreen';
import SettingsScreen from './screens/SettingsScreen';
import StatsScreen from './screens/StatsScreen';

// السياقات
import { AuthProvider } from './contexts/AuthContext';
import { ReviewProvider } from './contexts/ReviewContext';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';

const Stack = createNativeStackNavigator();

// الثيم العربي
const ArabicTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: '#1976D2',
    accent: '#FF4081',
    background: '#F5F5F5',
    surface: '#FFFFFF',
    text: '#212121',
    error: '#D32F2F',
  },
  fonts: {
    ...DefaultTheme.fonts,
    regular: { fontFamily: 'Cairo-Regular' },
    medium: { fontFamily: 'Cairo-Medium' },
    bold: { fontFamily: 'Cairo-Bold' },
  }
};

function AppContent() {
  const { isDark } = useTheme();

  return (
    <PaperProvider theme={ArabicTheme}>
      <NavigationContainer>
        <StatusBar
          barStyle={isDark ? 'light-content' : 'dark-content'}
          backgroundColor={isDark ? '#121212' : '#F5F5F5'}
        />
        <Stack.Navigator
          screenOptions={{
            headerStyle: {
              backgroundColor: ArabicTheme.colors.primary,
            },
            headerTintColor: '#fff',
            headerTitleStyle: {
              fontFamily: 'Cairo-Bold',
            },
          }}
        >
          <Stack.Screen
            name="Login"
            component={LoginScreen}
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="Batch"
            component={BatchScreen}
            options={{ title: 'دفعات المراجعة' }}
          />
          <Stack.Screen
            name="Review"
            component={ReviewScreen}
            options={{ title: 'المراجعة' }}
          />
          <Stack.Screen
            name="Settings"
            component={SettingsScreen}
            options={{ title: 'الإعدادات' }}
          />
          <Stack.Screen
            name="Stats"
            component={StatsScreen}
            options={{ title: 'إحصائياتي' }}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </PaperProvider>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ReviewProvider>
          <AppContent />
        </ReviewProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

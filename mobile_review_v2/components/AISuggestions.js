/**
 * AISuggestions.js
 * ===============
 *
 * عرض اقتراحات AI للتصحيح.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { Chip, Surface } from 'react-native-paper';

export default function AISuggestions({ suggestions, onSelect, style }) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <Surface style={[styles.container, style]}>
      <Text style={styles.title}>💡 اقتراحات ذكية</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {suggestions.map((suggestion, index) => (
          <TouchableOpacity
            key={index}
            onPress={() => onSelect(suggestion)}
            activeOpacity={0.7}
          >
            <Chip
              style={styles.chip}
              textStyle={styles.chipText}
            >
              {suggestion}
            </Chip>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </Surface>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 12,
    borderRadius: 8,
    elevation: 2,
  },
  title: {
    fontSize: 12,
    color: '#666',
    marginBottom: 8,
    fontFamily: 'Cairo-Medium',
  },
  scrollContent: {
    gap: 8,
  },
  chip: {
    backgroundColor: '#E3F2FD',
    marginRight: 8,
  },
  chipText: {
    fontFamily: 'Cairo-Regular',
    color: '#1976D2',
  },
});

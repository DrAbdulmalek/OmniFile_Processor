/**
 * ReviewScreen.js
 * ===============
 *
 * شاشة المراجعة الرئيسية مع:
 * - عرض الصورة والتنبؤ
 * - تصحيح سريع
 * - اقتراحات AI
 * - تنقل سريع
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, StyleSheet, Image, TextInput,
  TouchableOpacity, ScrollView, KeyboardAvoidingView,
  Platform, Animated, Vibration, Alert
} from 'react-native';
import { Button, IconButton, Surface, Chip, ProgressBar } from 'react-native-paper';
import { GestureHandlerRootView, Swipeable } from 'react-native-gesture-handler';
import AsyncStorage from '@react-native-async-storage/async-storage';

// المكونات
import AISuggestions from '../components/AISuggestions';
import QuickActions from '../components/QuickActions';
import ImageViewer from '../components/ImageViewer';
import ReviewStats from '../components/ReviewStats';

// الخدمات
import { fetchBatch, submitCorrection, fetchSuggestions } from '../services/api';
import { saveOffline, syncWhenOnline } from '../services/offline';
import { playSound } from '../services/audio';

export default function ReviewScreen({ route, navigation }) {
  const { batchId } = route.params;

  // الحالة
  const [items, setItems] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [correction, setCorrection] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [progress, setProgress] = useState(0);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(true);

  // Refs للتنقل
  const inputRef = useRef(null);
  const swipeableRef = useRef(null);

  // تحميل الدفعة
  useEffect(() => {
    loadBatch();
  }, []);

  const loadBatch = async () => {
    try {
      setIsLoading(true);
      const data = await fetchBatch(batchId);
      setItems(data.items);
      setProgress(0);

      // تحميل الاقتراحات للأولى
      if (data.items.length > 0) {
        loadSuggestions(data.items[0]);
      }
    } catch (error) {
      // محاولة من التخزين المحلي
      const offline = await AsyncStorage.getItem(`batch_${batchId}`);
      if (offline) {
        setItems(JSON.parse(offline));
        setIsOffline(true);
      } else {
        Alert.alert('خطأ', 'فشل في تحميل الدفعة');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // تحميل اقتراحات AI
  const loadSuggestions = async (item) => {
    if (!showSuggestions) return;

    try {
      const data = await fetchSuggestions(item.imageUrl, item.prediction);
      setSuggestions(data.suggestions || []);
    } catch (error) {
      // الاقتراحات المحلية
      setSuggestions(generateLocalSuggestions(item.prediction));
    }
  };

  // اقتراحات محلية
  const generateLocalSuggestions = (prediction) => {
    // قواعد بسيطة للعربي
    const suggestions = [];

    // إضافة تشكيل شائع
    if (prediction.includes('الله')) {
      suggestions.push(prediction.replace('الله', 'اللَّهِ'));
    }
    if (prediction.includes('بسم')) {
      suggestions.push(prediction.replace('بسم', 'بِسْمِ'));
    }

    return suggestions;
  };

  // تقديم تصحيح
  const submit = useCallback(async () => {
    const current = items[currentIndex];
    if (!current) return;

    const correctionData = {
      id: current.id,
      original: current.prediction,
      corrected: correction || current.prediction,
      confidence: calculateConfidence(current.prediction, correction),
      timestamp: new Date().toISOString(),
      reviewer: await AsyncStorage.getItem('user_id'),
      batchId: batchId
    };

    try {
      if (isOffline) {
        // حفظ محلي
        await saveOffline(correctionData);
        playSound('saved');
      } else {
        // إرسال فوري
        await submitCorrection(correctionData);
        playSound('success');
      }

      // تحديث التقدم
      const newProgress = (currentIndex + 1) / items.length;
      setProgress(newProgress);

      // الانتقال للتالي
      if (currentIndex < items.length - 1) {
        goNext();
      } else {
        // انتهت الدفعة
        Alert.alert(
          '✅ اكتملت الدفعة!',
          `تمت مراجعة ${items.length} عنصر`,
          [
            { text: 'عرض الإحصائيات', onPress: () => navigation.navigate('Stats') },
            { text: 'دفعة جديدة', onPress: () => navigation.navigate('Batch') }
          ]
        );
      }
    } catch (error) {
      // حفظ محلي كاحتياطي
      await saveOffline(correctionData);
      Alert.alert('⚠️', 'حُفظ محلياً - سيتم المزامنة لاحقاً');
    }
  }, [items, currentIndex, correction, isOffline]);

  // الانتقال للتالي
  const goNext = useCallback(() => {
    setCorrection('');
    setSuggestions([]);

    const nextIndex = currentIndex + 1;
    setCurrentIndex(nextIndex);

    if (items[nextIndex]) {
      loadSuggestions(items[nextIndex]);
    }

    // تركيز على الحقل
    setTimeout(() => inputRef.current?.focus(), 100);
  }, [currentIndex, items]);

  // الانتقال للسابق
  const goPrevious = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setCorrection('');
    }
  }, [currentIndex]);

  // تخطي العنصر
  const skip = useCallback(() => {
    Vibration.vibrate(50);
    goNext();
  }, [goNext]);

  // نسخ التنبؤ
  const copyPrediction = useCallback(() => {
    const current = items[currentIndex];
    if (current) {
      setCorrection(current.prediction);
    }
  }, [items, currentIndex]);

  // تطبيق اقتراح
  const applySuggestion = useCallback((suggestion) => {
    setCorrection(suggestion);
    inputRef.current?.focus();
  }, []);

  // حساب الثقة
  const calculateConfidence = (original, corrected) => {
    if (!corrected || original === corrected) return 1.0;

    // Levenshtein distance
    const distance = levenshteinDistance(original, corrected);
    const maxLen = Math.max(original.length, corrected.length);

    return Math.max(0, 1 - (distance / maxLen));
  };

  // المسافة بين السلاسل
  const levenshteinDistance = (a, b) => {
    const matrix = [];
    for (let i = 0; i <= b.length; i++) matrix[i] = [i];
    for (let j = 0; j <= a.length; j++) matrix[0][j] = j;

    for (let i = 1; i <= b.length; i++) {
      for (let j = 1; j <= a.length; j++) {
        if (b.charAt(i-1) === a.charAt(j-1)) {
          matrix[i][j] = matrix[i-1][j-1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i-1][j-1] + 1,
            matrix[i][j-1] + 1,
            matrix[i-1][j] + 1
          );
        }
      }
    }

    return matrix[b.length][a.length];
  };

  // العنصر الحالي
  const current = items[currentIndex];

  if (!current) {
    return (
      <View style={styles.container}>
        <Text>جاري التحميل...</Text>
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.container}
      >
        {/* شريط التقدم */}
        <ProgressBar
          progress={progress}
          color="#1976D2"
          style={styles.progressBar}
        />

        {/* معلومات الدفعة */}
        <View style={styles.header}>
          <Text style={styles.counter}>
            {currentIndex + 1} / {items.length}
          </Text>
          {isOffline && (
            <Chip icon="cloud-off-outline" style={styles.offlineChip}>
              offline
            </Chip>
          )}
        </View>

        <ScrollView style={styles.scrollView}>
          {/* عرض الصورة */}
          <ImageViewer
            imageUrl={current.imageUrl}
            style={styles.image}
            onZoom={() => {}}
          />

          {/* التنبؤ الأصلي */}
          <Surface style={styles.predictionSurface}>
            <Text style={styles.predictionLabel}>التنبؤ الأصلي:</Text>
            <Text style={styles.predictionText}>{current.prediction}</Text>
            <IconButton
              icon="content-copy"
              size={20}
              onPress={copyPrediction}
              style={styles.copyButton}
            />
          </Surface>

          {/* حقل التصحيح */}
          <View style={styles.inputContainer}>
            <TextInput
              ref={inputRef}
              style={styles.input}
              value={correction}
              onChangeText={setCorrection}
              placeholder="اكتب التصحيح هنا..."
              placeholderTextColor="#999"
              multiline
              textAlign="right"
              autoFocus
              onSubmitEditing={submit}
            />

            {/* أزرار سريعة */}
            <QuickActions
              onClear={() => setCorrection('')}
              onCopy={copyPrediction}
              onUndo={() => setCorrection(correction.slice(0, -1))}
            />
          </View>

          {/* اقتراحات AI */}
          {showSuggestions && suggestions.length > 0 && (
            <AISuggestions
              suggestions={suggestions}
              onSelect={applySuggestion}
              style={styles.suggestions}
            />
          )}

          {/* إحصائيات سريعة */}
          <ReviewStats
            total={items.length}
            completed={currentIndex}
            accuracy={calculateConfidence(current.prediction, correction)}
          />
        </ScrollView>

        {/* أزرار التنقل */}
        <View style={styles.footer}>
          <Button
            mode="outlined"
            onPress={goPrevious}
            disabled={currentIndex === 0}
            style={styles.navButton}
          >
            السابق
          </Button>

          <Button
            mode="contained"
            onPress={submit}
            style={[styles.submitButton, styles.navButton]}
          >
            ✓ تصحيح
          </Button>

          <Button
            mode="outlined"
            onPress={skip}
            style={styles.navButton}
          >
            تخطي →
          </Button>
        </View>
      </KeyboardAvoidingView>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  progressBar: {
    height: 4,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 12,
  },
  counter: {
    fontSize: 16,
    fontFamily: 'Cairo-Bold',
    color: '#666',
  },
  offlineChip: {
    backgroundColor: '#FFF3E0',
  },
  scrollView: {
    flex: 1,
  },
  image: {
    width: '100%',
    height: 200,
    resizeMode: 'contain',
    marginVertical: 8,
  },
  predictionSurface: {
    margin: 12,
    padding: 16,
    borderRadius: 8,
    elevation: 2,
  },
  predictionLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  predictionText: {
    fontSize: 18,
    fontFamily: 'Cairo-Regular',
    color: '#333',
    textAlign: 'right',
  },
  copyButton: {
    position: 'absolute',
    top: 8,
    left: 8,
  },
  inputContainer: {
    margin: 12,
  },
  input: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    fontSize: 18,
    fontFamily: 'Cairo-Regular',
    minHeight: 80,
    textAlignVertical: 'top',
    borderWidth: 1,
    borderColor: '#ddd',
  },
  suggestions: {
    marginHorizontal: 12,
    marginBottom: 12,
  },
  footer: {
    flexDirection: 'row',
    padding: 12,
    gap: 8,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  navButton: {
    flex: 1,
  },
  submitButton: {
    backgroundColor: '#1976D2',
  },
});

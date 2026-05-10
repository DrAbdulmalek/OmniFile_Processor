/**
 * offline.js
 * ==========
 *
 * إدارة العمل offline + المزامنة.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { Queue } from '../utils/queue';

const SYNC_QUEUE_KEY = '@review_sync_queue';
const BATCHES_KEY = '@offline_batches';

// طابور المزامنة
let syncQueue = new Queue();

// مراقبة الاتصال
export function initOfflineSync() {
  NetInfo.addEventListener(state => {
    if (state.isConnected && syncQueue.size() > 0) {
      syncPendingCorrections();
    }
  });
}

// حفظ تصحيح محلي
export async function saveOffline(correction) {
  try {
    // إضافة للطابور
    syncQueue.enqueue(correction);

    // حفظ في التخزين
    const queue = await AsyncStorage.getItem(SYNC_QUEUE_KEY);
    const corrections = queue ? JSON.parse(queue) : [];
    corrections.push(correction);

    await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(corrections));

    return true;
  } catch (error) {
    console.error('Error saving offline:', error);
    return false;
  }
}

// مزامنة التصحيحات المعلقة
export async function syncPendingCorrections() {
  try {
    const queue = await AsyncStorage.getItem(SYNC_QUEUE_KEY);
    if (!queue) return;

    const corrections = JSON.parse(queue);
    if (corrections.length === 0) return;

    console.log(`Syncing ${corrections.length} corrections...`);

    // إرسال دفعة
    const response = await fetch('/api/review/batch-submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ corrections })
    });

    if (response.ok) {
      // مسح الطابور
      await AsyncStorage.removeItem(SYNC_QUEUE_KEY);
      syncQueue.clear();

      console.log('Sync completed!');
      return { success: true, count: corrections.length };
    } else {
      throw new Error('Sync failed');
    }
  } catch (error) {
    console.error('Sync error:', error);
    return { success: false, error: error.message };
  }
}

// حفظ دفعة للعمل offline
export async function cacheBatch(batchId, items) {
  try {
    await AsyncStorage.setItem(
      `${BATCHES_KEY}_${batchId}`,
      JSON.stringify({
        items,
        cachedAt: new Date().toISOString()
      })
    );
    return true;
  } catch (error) {
    console.error('Error caching batch:', error);
    return false;
  }
}

// جلب دفعة من التخزين المحلي
export async function getCachedBatch(batchId) {
  try {
    const data = await AsyncStorage.getItem(`${BATCHES_KEY}_${batchId}`);
    return data ? JSON.parse(data) : null;
  } catch (error) {
    console.error('Error getting cached batch:', error);
    return null;
  }
}

// حالة المزامنة
export async function getSyncStatus() {
  const queue = await AsyncStorage.getItem(SYNC_QUEUE_KEY);
  const corrections = queue ? JSON.parse(queue) : [];

  return {
    pendingCount: corrections.length,
    isOnline: (await NetInfo.fetch()).isConnected
  };
}

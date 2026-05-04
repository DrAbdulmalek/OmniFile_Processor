// API service for communicating with the Flask backend

const API_BASE_URL = 'http://localhost:5002/api';

class APIService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    // Remove Content-Type for FormData
    if (options.body instanceof FormData) {
      delete config.headers['Content-Type'];
    }

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Get available OCR engines and system status
  async getEngines() {
    return this.request('/ocr/engines');
  }

  // Process file with OCR and AI correction
  async processFile(file, options = {}) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Add processing options
    if (options.engines && options.engines.length > 0) {
      options.engines.forEach(engine => {
        formData.append('engines', engine);
      });
    }
    
    if (options.language) {
      formData.append('language', options.language);
    }
    
    if (options.aiCorrection !== undefined) {
      formData.append('ai_correction', options.aiCorrection.toString());
    }
    
    if (options.combinationMethod) {
      formData.append('combination_method', options.combinationMethod);
    }
    
    if (options.context) {
      formData.append('context', options.context);
    }
    
    if (options.externalEngine) {
      formData.append('external_engine', options.externalEngine);
    }
    
    if (options.confidence !== undefined) {
      formData.append('confidence', options.confidence.toString());
    }

    return this.request('/ocr/process', {
      method: 'POST',
      body: formData,
    });
  }

  // Correct text using AI without OCR processing
  async correctText(text, language = 'mixed', context = '') {
    return this.request('/ocr/correct-text', {
      method: 'POST',
      body: JSON.stringify({
        text,
        language,
        context,
      }),
    });
  }

  // Get AI suggestions for text improvement
  async getSuggestions(text, language = 'mixed') {
    return this.request('/ocr/suggest-improvements', {
      method: 'POST',
      body: JSON.stringify({
        text,
        language,
      }),
    });
  }

  // Health check
  async healthCheck() {
    return this.request('/ocr/health');
  }
}

// Create and export a singleton instance
const apiService = new APIService();
export default apiService;

// Export individual methods for convenience
export const {
  getEngines,
  processFile,
  correctText,
  getSuggestions,
  healthCheck,
} = apiService;


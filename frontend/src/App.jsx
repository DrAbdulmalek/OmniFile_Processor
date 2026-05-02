import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Loader2, AlertCircle, CheckCircle, Zap, FileText, Brain } from 'lucide-react';
import FileUpload from './components/FileUpload';
import ProcessingOptions from './components/ProcessingOptions';
import ResultsDisplay from './components/ResultsDisplay';
import apiService from './services/api';
import './App.css';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [availableEngines, setAvailableEngines] = useState([]);
  const [aiAvailable, setAiAvailable] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [systemStatus, setSystemStatus] = useState('loading');
  
  const [processingOptions, setProcessingOptions] = useState({
    engines: ['tesseract'],
    language: 'eng+ara',
    aiCorrection: true,
    combinationMethod: 'best_confidence',
    context: '',
    externalEngine: 'ABBYY FineReader',
    confidence: 85,
    fileType: null
  });

  // Initialize system and check available engines
  useEffect(() => {
    initializeSystem();
  }, []);

  // Update file type when file is selected
  useEffect(() => {
    if (selectedFile) {
      const fileExtension = selectedFile.name.split('.').pop().toLowerCase();
      setProcessingOptions(prev => ({
        ...prev,
        fileType: fileExtension
      }));
    }
  }, [selectedFile]);

  const initializeSystem = async () => {
    try {
      setSystemStatus('loading');
      const response = await apiService.getEngines();
      
      if (response.success) {
        setAvailableEngines(response.engines);
        setAiAvailable(response.ai_correction_available);
        setSystemStatus('ready');
        
        // Update default options based on available engines
        setProcessingOptions(prev => ({
          ...prev,
          engines: response.engines.length > 0 ? [response.engines[0]] : [],
          aiCorrection: response.ai_correction_available
        }));
      } else {
        throw new Error('Failed to initialize system');
      }
    } catch (err) {
      console.error('System initialization failed:', err);
      setError(`System initialization failed: ${err.message}`);
      setSystemStatus('error');
    }
  };

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setResults(null);
    setError('');
  };

  const handleOptionsChange = (newOptions) => {
    setProcessingOptions(newOptions);
  };

  const handleProcess = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    if (processingOptions.engines.length === 0) {
      setError('Please select at least one OCR engine');
      return;
    }

    try {
      setProcessing(true);
      setError('');
      setResults(null);

      const response = await apiService.processFile(selectedFile, processingOptions);
      
      if (response.success) {
        setResults(response);
      } else {
        throw new Error(response.error || 'Processing failed');
      }
    } catch (err) {
      console.error('Processing failed:', err);
      setError(`Processing failed: ${err.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const handleTextEdit = (newText) => {
    if (results) {
      setResults(prev => ({
        ...prev,
        final_text: newText
      }));
    }
  };

  const handleSaveResults = (text, resultsData) => {
    // Create a comprehensive results file
    const saveData = {
      timestamp: new Date().toISOString(),
      filename: selectedFile?.name,
      final_text: text,
      processing_settings: resultsData.settings,
      ocr_results: resultsData.ocr_results,
      ai_correction: resultsData.ai_correction,
      combined_result: resultsData.combined_result
    };

    const blob = new Blob([JSON.stringify(saveData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ocr_results_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const renderSystemStatus = () => {
    switch (systemStatus) {
      case 'loading':
        return (
          <Alert>
            <Loader2 className="h-4 w-4 animate-spin" />
            <AlertDescription>Initializing OCR system...</AlertDescription>
          </Alert>
        );
      case 'error':
        return (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              System initialization failed. Please refresh the page or check your connection.
              <Button 
                variant="outline" 
                size="sm" 
                className="ml-2" 
                onClick={initializeSystem}
              >
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        );
      case 'ready':
        return (
          <Alert>
            <CheckCircle className="h-4 w-4" />
            <AlertDescription>
              System ready. {availableEngines.length} OCR engine(s) available.
              {aiAvailable ? ' AI correction enabled.' : ' AI correction not available.'}
            </AlertDescription>
          </Alert>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            OCR Enhancer
          </h1>
          <p className="text-lg text-gray-600">
            AI-Powered Text Recognition and Correction
          </p>
        </div>

        {/* System Status */}
        <div className="mb-6">
          {renderSystemStatus()}
        </div>

        {/* Error Display */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {systemStatus === 'ready' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column - File Upload and Options */}
            <div className="lg:col-span-1 space-y-6">
              {/* File Upload */}
              <div>
                <h2 className="text-xl font-semibold mb-4 flex items-center">
                  <FileText className="h-5 w-5 mr-2" />
                  Upload Document
                </h2>
                <FileUpload onFileSelect={handleFileSelect} />
              </div>

              {/* Processing Options */}
              {selectedFile && (
                <div>
                  <h2 className="text-xl font-semibold mb-4 flex items-center">
                    <Brain className="h-5 w-5 mr-2" />
                    Processing Options
                  </h2>
                  <ProcessingOptions
                    options={processingOptions}
                    onOptionsChange={handleOptionsChange}
                    availableEngines={availableEngines}
                    aiAvailable={aiAvailable}
                    onProcess={handleProcess}
                    processing={processing}
                  />
                </div>
              )}
            </div>

            {/* Right Column - Results */}
            <div className="lg:col-span-2">
              {processing && (
                <Card>
                  <CardContent className="flex items-center justify-center py-12">
                    <div className="text-center">
                      <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
                      <h3 className="text-lg font-medium mb-2">Processing Document</h3>
                      <p className="text-gray-600">
                        Running OCR engines and AI correction...
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}

              {results && !processing && (
                <div>
                  <h2 className="text-xl font-semibold mb-4 flex items-center">
                    <Zap className="h-5 w-5 mr-2" />
                    Results
                  </h2>
                  <ResultsDisplay
                    results={results}
                    onTextEdit={handleTextEdit}
                    onSaveResults={handleSaveResults}
                  />
                </div>
              )}

              {!selectedFile && !processing && !results && (
                <Card>
                  <CardContent className="flex items-center justify-center py-12">
                    <div className="text-center text-gray-500">
                      <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <h3 className="text-lg font-medium mb-2">No Document Selected</h3>
                      <p>Upload a document to get started with OCR processing</p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

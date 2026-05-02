import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Download, 
  Copy, 
  Eye, 
  EyeOff, 
  CheckCircle, 
  AlertCircle, 
  Zap,
  FileText,
  Brain,
  Settings
} from 'lucide-react';

const ResultsDisplay = ({ results, onTextEdit, onSaveResults }) => {
  const [editableText, setEditableText] = useState(results?.final_text || '');
  const [showDetails, setShowDetails] = useState(false);

  if (!results) {
    return null;
  }

  const handleTextChange = (value) => {
    setEditableText(value);
    onTextEdit(value);
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(editableText);
      // You could add a toast notification here
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const downloadText = () => {
    const blob = new Blob([editableText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ocr_result_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 90) return 'bg-green-100 text-green-800';
    if (confidence >= 70) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getConfidenceIcon = (confidence) => {
    if (confidence >= 70) return <CheckCircle className="h-4 w-4" />;
    return <AlertCircle className="h-4 w-4" />;
  };

  return (
    <div className="space-y-6">
      {/* Main Results */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>Extracted Text</span>
            </CardTitle>
            <div className="flex items-center space-x-2">
              <Button variant="outline" size="sm" onClick={copyToClipboard}>
                <Copy className="h-4 w-4 mr-2" />
                Copy
              </Button>
              <Button variant="outline" size="sm" onClick={downloadText}>
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => setShowDetails(!showDetails)}
              >
                {showDetails ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                {showDetails ? 'Hide' : 'Show'} Details
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Textarea
            value={editableText}
            onChange={(e) => handleTextChange(e.target.value)}
            rows={12}
            className="w-full font-mono text-sm"
            placeholder="Extracted text will appear here..."
          />
          
          {/* Quick Stats */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t">
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span>Words: {editableText.split(/\s+/).filter(w => w.length > 0).length}</span>
              <span>Characters: {editableText.length}</span>
            </div>
            {results.combined_result && (
              <Badge className={getConfidenceColor(results.combined_result.confidence)}>
                {getConfidenceIcon(results.combined_result.confidence)}
                <span className="ml-1">{Math.round(results.combined_result.confidence)}% Confidence</span>
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Detailed Results */}
      {showDetails && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Settings className="h-5 w-5" />
              <span>Processing Details</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="ocr" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="ocr">OCR Results</TabsTrigger>
                <TabsTrigger value="ai">AI Correction</TabsTrigger>
                <TabsTrigger value="settings">Settings</TabsTrigger>
              </TabsList>
              
              <TabsContent value="ocr" className="space-y-4">
                {results.ocr_results && Object.entries(results.ocr_results).map(([engine, result]) => (
                  <Card key={engine}>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg capitalize">{engine}</CardTitle>
                        <Badge variant={result.success ? 'default' : 'destructive'}>
                          {result.success ? 'Success' : 'Failed'}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {result.success ? (
                        <div className="space-y-3">
                          <div className="flex items-center space-x-4 text-sm">
                            <span>Confidence: {Math.round(result.confidence)}%</span>
                            <span>Words: {result.word_count}</span>
                            <span>Language: {result.language}</span>
                          </div>
                          <div className="bg-gray-50 p-3 rounded text-sm font-mono max-h-32 overflow-y-auto">
                            {result.text || 'No text extracted'}
                          </div>
                        </div>
                      ) : (
                        <div className="text-red-600 text-sm">
                          Error: {result.error}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </TabsContent>
              
              <TabsContent value="ai" className="space-y-4">
                {results.ai_correction ? (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <Brain className="h-5 w-5" />
                        <span>AI Enhancement Results</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {results.ai_correction.success ? (
                        <div className="space-y-4">
                          <div className="flex items-center space-x-4 text-sm">
                            <Badge className={getConfidenceColor(results.ai_correction.confidence)}>
                              {Math.round(results.ai_correction.confidence)}% Confidence
                            </Badge>
                            <span>Changes: {results.ai_correction.changes_made?.length || 0}</span>
                            <span>Model: {results.ai_correction.model_used}</span>
                          </div>
                          
                          {results.ai_correction.changes_made?.length > 0 && (
                            <div className="space-y-2">
                              <h4 className="font-medium">Changes Made:</h4>
                              <div className="bg-gray-50 p-3 rounded text-sm max-h-32 overflow-y-auto">
                                {results.ai_correction.changes_made.map((change, index) => (
                                  <div key={index} className="mb-2">
                                    <span className="text-red-600">"{change.original}"</span>
                                    {' → '}
                                    <span className="text-green-600">"{change.corrected}"</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-red-600">
                          AI correction failed: {results.ai_correction.error}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    AI correction was not applied
                  </div>
                )}
              </TabsContent>
              
              <TabsContent value="settings" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Processing Settings</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium">Engines Used:</span>
                        <div className="mt-1">
                          {results.settings?.engines?.map(engine => (
                            <Badge key={engine} variant="outline" className="mr-1">
                              {engine}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <span className="font-medium">Language:</span>
                        <div className="mt-1">{results.settings?.language}</div>
                      </div>
                      <div>
                        <span className="font-medium">AI Correction:</span>
                        <div className="mt-1">
                          {results.settings?.ai_correction ? 'Enabled' : 'Disabled'}
                        </div>
                      </div>
                      <div>
                        <span className="font-medium">Combination Method:</span>
                        <div className="mt-1">{results.settings?.combination_method}</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Save Results */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Save Results</h3>
              <p className="text-sm text-gray-600">Save the processed text and corrections for future reference</p>
            </div>
            <Button onClick={() => onSaveResults(editableText, results)}>
              <Download className="h-4 w-4 mr-2" />
              Save Results
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ResultsDisplay;


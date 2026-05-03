import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Settings, Zap, Globe, Brain } from 'lucide-react';

const ProcessingOptions = ({ 
  options, 
  onOptionsChange, 
  availableEngines = ['tesseract'], 
  aiAvailable = false,
  onProcess,
  processing = false 
}) => {
  const handleEngineChange = (engine, checked) => {
    const newEngines = checked 
      ? [...options.engines, engine]
      : options.engines.filter(e => e !== engine);
    
    onOptionsChange({ ...options, engines: newEngines });
  };

  const handleOptionChange = (key, value) => {
    onOptionsChange({ ...options, [key]: value });
  };

  return (
    <div className="space-y-6">
      {/* OCR Engines */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Settings className="h-5 w-5" />
            <span>OCR Engines</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            {availableEngines.map((engine) => (
              <div key={engine} className="flex items-center space-x-2">
                <Checkbox
                  id={engine}
                  checked={options.engines.includes(engine)}
                  onCheckedChange={(checked) => handleEngineChange(engine, checked)}
                />
                <Label htmlFor={engine} className="capitalize">
                  {engine === 'tesseract' ? 'Tesseract OCR' : engine}
                </Label>
              </div>
            ))}
          </div>
          
          {options.engines.length > 1 && (
            <div className="space-y-2">
              <Label>Combination Method</Label>
              <Select 
                value={options.combinationMethod} 
                onValueChange={(value) => handleOptionChange('combinationMethod', value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="best_confidence">Best Confidence</SelectItem>
                  <SelectItem value="longest_text">Longest Text</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Language Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Globe className="h-5 w-5" />
            <span>Language Settings</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>OCR Language</Label>
            <Select 
              value={options.language} 
              onValueChange={(value) => handleOptionChange('language', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="eng+ara">Arabic + English</SelectItem>
                <SelectItem value="eng">English Only</SelectItem>
                <SelectItem value="ara">Arabic Only</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* AI Correction */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Brain className="h-5 w-5" />
            <span>AI Enhancement</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="aiCorrection"
              checked={options.aiCorrection}
              onCheckedChange={(checked) => handleOptionChange('aiCorrection', checked)}
              disabled={!aiAvailable}
            />
            <Label htmlFor="aiCorrection">
              Enable AI Text Correction
              {!aiAvailable && <span className="text-red-500 ml-2">(Not Available)</span>}
            </Label>
          </div>
          
          {options.aiCorrection && aiAvailable && (
            <div className="space-y-3">
              <div className="space-y-2">
                <Label>Context (Optional)</Label>
                <Textarea
                  placeholder="Provide context about the document to improve AI correction..."
                  value={options.context}
                  onChange={(e) => handleOptionChange('context', e.target.value)}
                  rows={3}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* External OCR Settings */}
      {options.fileType === 'txt' && (
        <Card>
          <CardHeader>
            <CardTitle>External OCR Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>OCR Engine Name</Label>
              <Input
                placeholder="e.g., ABBYY FineReader, Readiris"
                value={options.externalEngine}
                onChange={(e) => handleOptionChange('externalEngine', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Confidence Score (%)</Label>
              <Input
                type="number"
                min="0"
                max="100"
                value={options.confidence}
                onChange={(e) => handleOptionChange('confidence', parseFloat(e.target.value) || 85)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Process Button */}
      <Button 
        onClick={onProcess} 
        disabled={processing || options.engines.length === 0}
        className="w-full"
        size="lg"
      >
        <Zap className="h-4 w-4 mr-2" />
        {processing ? 'Processing...' : 'Process Document'}
      </Button>
    </div>
  );
};

export default ProcessingOptions;


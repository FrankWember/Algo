'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Play, Pause, SkipBack, SkipForward, RotateCcw } from 'lucide-react';
import type { AlgorithmStep } from '@/types';

interface StepVisualizerProps {
  steps: AlgorithmStep[];
  onStepChange: (step: AlgorithmStep | null) => void;
  algorithmName: string;
}

export default function StepVisualizer({
  steps: stepsProp,
  onStepChange,
  algorithmName,
}: StepVisualizerProps) {
  const steps = Array.isArray(stepsProp) ? stepsProp : [];
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(500); // ms per step

  const currentStep = steps[currentStepIndex] || null;

  // Notify parent of step changes
  useEffect(() => {
    onStepChange(currentStep);
  }, [currentStep, onStepChange]);

  // Auto-play functionality
  useEffect(() => {
    if (!isPlaying) return;

    const timer = setInterval(() => {
      setCurrentStepIndex(prev => {
        if (prev >= steps.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, playSpeed);

    return () => clearInterval(timer);
  }, [isPlaying, playSpeed, steps.length]);

  const goToStep = useCallback((index: number) => {
    setCurrentStepIndex(Math.max(0, Math.min(index, steps.length - 1)));
  }, [steps.length]);

  const reset = useCallback(() => {
    setCurrentStepIndex(0);
    setIsPlaying(false);
  }, []);

  if (steps.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-semibold text-gray-900">
          Step-by-Step Visualization
        </h4>
        <span className="text-sm text-gray-500">
          {algorithmName}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Step {currentStepIndex + 1}</span>
          <span>{steps.length} total</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-siue-red transition-all duration-200"
            style={{ width: `${((currentStepIndex + 1) / steps.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-2 mb-4">
        <button
          onClick={reset}
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          title="Reset"
        >
          <RotateCcw size={18} />
        </button>
        <button
          onClick={() => goToStep(currentStepIndex - 1)}
          disabled={currentStepIndex === 0}
          className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Previous step"
        >
          <SkipBack size={18} />
        </button>
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className={`p-3 rounded-full transition-colors ${
            isPlaying ? 'bg-red-100 text-red-600' : 'bg-siue-red text-white'
          }`}
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? <Pause size={20} /> : <Play size={20} />}
        </button>
        <button
          onClick={() => goToStep(currentStepIndex + 1)}
          disabled={currentStepIndex === steps.length - 1}
          className="p-2 rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Next step"
        >
          <SkipForward size={18} />
        </button>

        {/* Speed Control */}
        <select
          value={playSpeed}
          onChange={(e) => setPlaySpeed(Number(e.target.value))}
          className="ml-2 text-sm border border-gray-300 rounded-lg px-2 py-1"
        >
          <option value={1000}>0.5x</option>
          <option value={500}>1x</option>
          <option value={250}>2x</option>
          <option value={100}>5x</option>
        </select>
      </div>

      {/* Current Step Details */}
      {currentStep && (
        <div className={`p-3 rounded-lg ${getStepBackground(currentStep.action)}`}>
          <div className="flex items-center gap-2 mb-2">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${getActionBadge(currentStep.action)}`}>
              {currentStep.action.toUpperCase()}
            </span>
            {currentStep.current && (
              <span className="text-sm font-medium">
                Node: {currentStep.current}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-700">{currentStep.message}</p>

          {/* Additional step info */}
          {currentStep.newDistance !== undefined && (
            <div className="mt-2 text-xs text-gray-500">
              New distance: {currentStep.newDistance.toFixed(1)}m
            </div>
          )}
          {currentStep.heuristic !== undefined && (
            <div className="mt-1 text-xs text-gray-500">
              Heuristic: {currentStep.heuristic.toFixed(1)}
            </div>
          )}
          {currentStep.iteration !== undefined && (
            <div className="mt-1 text-xs text-gray-500">
              Iteration: {currentStep.iteration}
            </div>
          )}
        </div>
      )}

      {/* Step List (collapsed) */}
      <details className="mt-4">
        <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">
          View all steps
        </summary>
        <div className="mt-2 max-h-48 overflow-y-auto space-y-1">
          {steps.map((step, index) => (
            <button
              key={index}
              onClick={() => goToStep(index)}
              className={`w-full text-left px-2 py-1 rounded text-xs transition-colors ${
                index === currentStepIndex
                  ? 'bg-siue-red text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              <span className="font-mono">{index + 1}.</span> {step.message.slice(0, 50)}
              {step.message.length > 50 && '...'}
            </button>
          ))}
        </div>
      </details>
    </div>
  );
}

function getStepBackground(action: string): string {
  switch (action) {
    case 'visit':
      return 'bg-amber-50 border border-amber-200';
    case 'update':
      return 'bg-blue-50 border border-blue-200';
    case 'found':
      return 'bg-green-50 border border-green-200';
    case 'skip':
      return 'bg-gray-50 border border-gray-200';
    case 'iteration':
      return 'bg-purple-50 border border-purple-200';
    default:
      return 'bg-gray-50 border border-gray-200';
  }
}

function getActionBadge(action: string): string {
  switch (action) {
    case 'visit':
      return 'bg-amber-100 text-amber-800';
    case 'update':
      return 'bg-blue-100 text-blue-800';
    case 'found':
      return 'bg-green-100 text-green-800';
    case 'skip':
      return 'bg-gray-100 text-gray-800';
    case 'iteration':
      return 'bg-purple-100 text-purple-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

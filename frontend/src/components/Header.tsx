'use client';

import React from 'react';
import { Github, Info } from 'lucide-react';

export default function Header() {
  return (
    <header className="bg-siue-red text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              {/* SIUE-style logo */}
              <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
                <span className="text-siue-red font-bold text-xl">e</span>
              </div>
              <div>
                <h1 className="text-xl font-bold">SIUE Campus Router</h1>
                <p className="text-red-200 text-sm">Algorithm Visualizer</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                const modal = document.getElementById('info-modal');
                if (modal) modal.classList.toggle('hidden');
              }}
              className="p-2 hover:bg-red-700 rounded-lg transition-colors"
              title="About this project"
            >
              <Info size={20} />
            </button>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 hover:bg-red-700 rounded-lg transition-colors"
              title="View on GitHub"
            >
              <Github size={20} />
            </a>
          </div>
        </div>
      </div>

      {/* Info Modal */}
      <div
        id="info-modal"
        className="hidden fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            e.currentTarget.classList.add('hidden');
          }
        }}
      >
        <div className="bg-white text-gray-900 rounded-xl max-w-lg w-full p-6 shadow-2xl">
          <h2 className="text-xl font-bold mb-4">About This Project</h2>
          <div className="space-y-3 text-sm text-gray-600">
            <p>
              <strong>Smart Multi-Modal Campus Routing & Scheduling Optimizer</strong>
            </p>
            <p>
              This project demonstrates three different shortest path algorithms
              for finding optimal routes across the SIUE campus:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li><strong>Dijkstra's Algorithm</strong> - Classic greedy approach</li>
              <li><strong>A* Search</strong> - Heuristic-guided optimization</li>
              <li><strong>Bellman-Ford</strong> - Dynamic programming method</li>
            </ul>
            <p>
              The campus is modeled as a weighted graph where buildings are nodes
              and walkways are edges with distance weights.
            </p>
            <div className="pt-3 border-t border-gray-200">
              <p className="text-xs text-gray-500">
                Created by Odedairo Oluwaferanmi | Southern Illinois University Edwardsville
              </p>
            </div>
          </div>
          <button
            onClick={() => document.getElementById('info-modal')?.classList.add('hidden')}
            className="mt-4 w-full bg-siue-red text-white py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </header>
  );
}

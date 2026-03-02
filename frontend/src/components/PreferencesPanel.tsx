'use client';

import React, { useState, useEffect } from 'react';
import type { RoutePreferences, RushHour, ScheduleStatus } from '@/types';
import { api } from '@/lib/api';

interface PreferencesPanelProps {
  preferences: RoutePreferences;
  onChange: (prefs: RoutePreferences) => void;
}

const INTENSITY_COLORS: Record<string, string> = {
  low: 'text-green-600',
  medium: 'text-yellow-600',
  high: 'text-orange-500',
  very_high: 'text-red-600',
};

const INTENSITY_LABELS: Record<string, string> = {
  low: 'Low',
  medium: 'Moderate',
  high: 'High',
  very_high: 'Very High',
};

export default function PreferencesPanel({ preferences, onChange }: PreferencesPanelProps) {
  const [scheduleStatus, setScheduleStatus] = useState<ScheduleStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);

  // Fetch schedule status whenever departure_time changes
  useEffect(() => {
    const time = preferences.departure_time;
    if (!time) {
      setScheduleStatus(null);
      return;
    }
    setLoadingStatus(true);
    api.getScheduleStatus(time)
      .then(setScheduleStatus)
      .catch(() => setScheduleStatus(null))
      .finally(() => setLoadingStatus(false));
  }, [preferences.departure_time]);

  const update = (patch: Partial<RoutePreferences>) => {
    onChange({ ...preferences, ...patch });
  };

  const anyActive = preferences.wheelchair_only || preferences.avoid_stairs || !!preferences.departure_time;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-700 text-sm">Route Preferences</h3>
        {anyActive && (
          <button
            onClick={() => onChange({ wheelchair_only: false, avoid_stairs: false, max_stairs: 999, departure_time: '' })}
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Accessibility section */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Accessibility</p>

        <label className="flex items-start gap-2 cursor-pointer group">
          <input
            type="checkbox"
            checked={preferences.wheelchair_only}
            onChange={e => update({ wheelchair_only: e.target.checked })}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-siue-red focus:ring-siue-red"
          />
          <div>
            <span className="text-sm text-gray-700 group-hover:text-gray-900">
              Wheelchair accessible only
            </span>
            <p className="text-xs text-gray-400">Avoid routes through buildings rated inaccessible</p>
          </div>
        </label>

        <label className="flex items-start gap-2 cursor-pointer group">
          <input
            type="checkbox"
            checked={preferences.avoid_stairs}
            onChange={e => update({ avoid_stairs: e.target.checked })}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-siue-red focus:ring-siue-red"
          />
          <div>
            <span className="text-sm text-gray-700 group-hover:text-gray-900">
              Minimize stairs
            </span>
            <p className="text-xs text-gray-400">Prefer routes with fewer steps</p>
          </div>
        </label>

        {preferences.avoid_stairs && (
          <div className="ml-6 flex items-center gap-2">
            <label className="text-xs text-gray-500 whitespace-nowrap">Max stairs:</label>
            <input
              type="number"
              min={0}
              max={50}
              value={preferences.max_stairs === 999 ? '' : preferences.max_stairs}
              placeholder="any"
              onChange={e => {
                const v = parseInt(e.target.value);
                update({ max_stairs: isNaN(v) ? 999 : Math.max(0, v) });
              }}
              className="w-16 px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-siue-red focus:outline-none"
            />
            <span className="text-xs text-gray-400">steps</span>
          </div>
        )}
      </div>

      {/* Schedule section */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Schedule</p>

        <div>
          <label className="block text-sm text-gray-700 mb-1">Departure time</label>
          <input
            type="time"
            value={preferences.departure_time}
            onChange={e => update({ departure_time: e.target.value })}
            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-siue-red focus:border-transparent"
          />
          {!preferences.departure_time && (
            <p className="text-xs text-gray-400 mt-1">Set a time to see crowd delays</p>
          )}
        </div>

        {/* Schedule status feedback */}
        {preferences.departure_time && (
          <div className="rounded-lg border p-3 text-xs space-y-1.5">
            {loadingStatus ? (
              <div className="text-gray-400">Checking schedule…</div>
            ) : scheduleStatus ? (
              <>
                {scheduleStatus.is_rush_hour && scheduleStatus.active_rush_hour ? (
                  <div className="flex items-start gap-1.5">
                    <span>⚠️</span>
                    <div>
                      <span className={`font-medium ${INTENSITY_COLORS[scheduleStatus.active_rush_hour.intensity]}`}>
                        {INTENSITY_LABELS[scheduleStatus.active_rush_hour.intensity]} traffic
                      </span>
                      <span className="text-gray-500">
                        {' '}({scheduleStatus.active_rush_hour.start_time}–{scheduleStatus.active_rush_hour.end_time})
                      </span>
                      <p className="text-gray-500">
                        Travel time ×{scheduleStatus.crowd_multiplier.toFixed(1)} vs. off-peak
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 text-green-600">
                    <span>✓</span>
                    <span className="font-medium">Off-peak</span>
                    <span className="text-gray-500">— no crowd delays</span>
                  </div>
                )}
              </>
            ) : null}
          </div>
        )}
      </div>

      {/* Active preferences summary */}
      {anyActive && (
        <div className="bg-siue-red/5 border border-siue-red/20 rounded-lg p-2.5">
          <p className="text-xs font-medium text-siue-red mb-1">Active preferences</p>
          <ul className="text-xs text-gray-600 space-y-0.5">
            {preferences.wheelchair_only && <li>• Wheelchair accessible routes only</li>}
            {preferences.avoid_stairs && (
              <li>• Minimize stairs{preferences.max_stairs < 999 ? ` (max ${preferences.max_stairs})` : ''}</li>
            )}
            {preferences.departure_time && (
              <li>• Departure at {preferences.departure_time}
                {scheduleStatus && ` (×${scheduleStatus.crowd_multiplier.toFixed(1)} crowd)`}
              </li>
            )}
          </ul>
          <p className="text-xs text-gray-400 mt-1.5">Edge weights adjusted accordingly</p>
        </div>
      )}
    </div>
  );
}

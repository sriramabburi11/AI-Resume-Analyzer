import React from 'react';

export default function ScoreGauge({ score, title, subtitle, icon: Icon, color = 'blue' }) {
  const getScoreColor = (val) => {
    if (val >= 85) return { text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', bar: 'bg-emerald-500' };
    if (val >= 70) return { text: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', bar: 'bg-blue-500' };
    if (val >= 55) return { text: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', bar: 'bg-amber-500' };
    return { text: 'text-rose-600', bg: 'bg-rose-50', border: 'border-rose-200', bar: 'bg-rose-500' };
  };

  const colors = getScoreColor(score);

  return (
    <div className={`p-5 rounded-2xl bg-white border border-slate-200/80 shadow-xs hover:shadow-md transition duration-200 flex flex-col justify-between`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            {Icon && <Icon className="w-4 h-4 text-slate-500" />}
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>
        </div>
        <div className={`px-2.5 py-1 rounded-full text-xs font-bold ${colors.bg} ${colors.text} border ${colors.border}`}>
          {score}/100
        </div>
      </div>

      <div className="mt-4">
        <div className="flex items-baseline gap-1">
          <span className={`text-3xl font-extrabold tracking-tight ${colors.text}`}>{score}</span>
          <span className="text-sm font-medium text-slate-400">/ 100</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-2 mt-2 overflow-hidden">
          <div
            className={`h-2 rounded-full transition-all duration-700 ease-out ${colors.bar}`}
            style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
          />
        </div>
      </div>
    </div>
  );
}

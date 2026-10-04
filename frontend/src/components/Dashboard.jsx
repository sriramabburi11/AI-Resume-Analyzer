import React, { useState } from 'react';
import {
  FileText,
  Award,
  Zap,
  Briefcase,
  ShieldCheck,
  LayoutGrid,
  Target,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  RotateCcw,
  Sparkles
} from 'lucide-react';

import ScoreGauge from './ScoreGauge';
import ExactImprovements from './ExactImprovements';
import RoleRecommendations from './RoleRecommendations';
import AtsAnalysis from './AtsAnalysis';
import StructureAnalysis from './StructureAnalysis';
import JobMatchAnalysis from './JobMatchAnalysis';

export default function Dashboard({ data, onReset }) {
  const [activeTab, setActiveTab] = useState('improvements');

  if (!data) return null;

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8 fade-in">
      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/90 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200">
              Analysis Complete
            </span>
            {data.filename && (
              <span className="text-xs font-semibold text-slate-500 truncate max-w-xs">
                📄 {data.filename}
              </span>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Resume Performance Dashboard
          </h1>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="px-4 py-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-sm font-semibold flex items-center gap-2 shadow-xs transition cursor-pointer"
        >
          <RotateCcw className="w-4 h-4 text-slate-500" />
          <span>Upload Another Resume</span>
        </button>
      </div>

      {/* Feature 9 & 10: Overall Score & Sub-scores Overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <ScoreGauge
          score={data.overall_score}
          title="Overall Resume Score"
          subtitle="Weighted quality index"
          icon={Award}
          color="blue"
        />
        <ScoreGauge
          score={data.structure_score}
          title="Structure Score"
          subtitle="Section completeness"
          icon={LayoutGrid}
          color="emerald"
        />
        <ScoreGauge
          score={data.ats_score}
          title="Estimated ATS"
          subtitle="Parser readability"
          icon={ShieldCheck}
          color="amber"
        />
        <ScoreGauge
          score={data.content_score}
          title="Content Quality"
          subtitle="Bullet & keyword strength"
          icon={Zap}
          color="purple"
        />
      </div>

      {/* Executive Summary Cards: Strengths & Problems */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Strengths Card */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-3">
          <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            Resume Strengths
          </h3>
          <ul className="space-y-2">
            {data.strengths && data.strengths.length > 0 ? (
              data.strengths.map((st, idx) => (
                <li key={idx} className="text-xs sm:text-sm text-slate-700 flex items-start gap-2">
                  <span className="text-emerald-500 font-bold mt-0.5">✓</span>
                  <span>{st}</span>
                </li>
              ))
            ) : (
              <li className="text-xs text-slate-400">No strengths identified.</li>
            )}
          </ul>
        </div>

        {/* Problems Card */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-3">
          <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            Areas Requiring Attention
          </h3>
          <ul className="space-y-2">
            {data.problems && data.problems.length > 0 ? (
              data.problems.map((pr, idx) => (
                <li key={idx} className="text-xs sm:text-sm text-slate-700 flex items-start gap-2">
                  <span className="text-amber-500 font-bold mt-0.5">⚠</span>
                  <span>{pr}</span>
                </li>
              ))
            ) : (
              <li className="text-xs text-slate-400">No key problems detected.</li>
            )}
          </ul>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-2 sm:space-x-8 overflow-x-auto pb-1">
          <button
            onClick={() => setActiveTab('improvements')}
            className={`py-3 px-1 border-b-2 font-bold text-sm flex items-center gap-2 whitespace-nowrap transition cursor-pointer ${
              activeTab === 'improvements'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Zap className="w-4 h-4" />
            Exact Improvements ({data.improvements?.length || 0})
          </button>

          <button
            onClick={() => setActiveTab('roles')}
            className={`py-3 px-1 border-b-2 font-bold text-sm flex items-center gap-2 whitespace-nowrap transition cursor-pointer ${
              activeTab === 'roles'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Briefcase className="w-4 h-4" />
            Suitable Roles ({data.roles?.length || 0})
          </button>

          <button
            onClick={() => setActiveTab('ats')}
            className={`py-3 px-1 border-b-2 font-bold text-sm flex items-center gap-2 whitespace-nowrap transition cursor-pointer ${
              activeTab === 'ats'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            Estimated ATS ({data.ats_score}/100)
          </button>

          <button
            onClick={() => setActiveTab('structure')}
            className={`py-3 px-1 border-b-2 font-bold text-sm flex items-center gap-2 whitespace-nowrap transition cursor-pointer ${
              activeTab === 'structure'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <LayoutGrid className="w-4 h-4" />
            Structure Audit ({data.structure_score}/100)
          </button>

          <button
            onClick={() => setActiveTab('jobmatch')}
            className={`py-3 px-1 border-b-2 font-bold text-sm flex items-center gap-2 whitespace-nowrap transition cursor-pointer ${
              activeTab === 'jobmatch'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Target className="w-4 h-4" />
            Job Description & Keywords
            {data.job_match_score !== null && (
              <span className="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full font-bold">
                {data.job_match_score}% Match
              </span>
            )}
          </button>
        </nav>
      </div>

      {/* Tab Panels */}
      <div className="pt-2">
        {activeTab === 'improvements' && (
          <ExactImprovements improvements={data.improvements} />
        )}

        {activeTab === 'roles' && (
          <RoleRecommendations roles={data.roles} />
        )}

        {activeTab === 'ats' && (
          <AtsAnalysis score={data.ats_score} issues={data.ats_issues} />
        )}

        {activeTab === 'structure' && (
          <StructureAnalysis
            score={data.structure_score}
            sectionDetails={data.section_details}
            sectionsMap={data.sections}
          />
        )}

        {activeTab === 'jobmatch' && (
          <JobMatchAnalysis
            jobMatchScore={data.job_match_score}
            jobMatchDetails={data.job_match_details}
            keywords={data.keywords}
          />
        )}
      </div>
    </div>
  );
}

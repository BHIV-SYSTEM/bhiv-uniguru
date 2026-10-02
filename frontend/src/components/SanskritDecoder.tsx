import React, { useState, useCallback, useRef, useEffect } from "react";
import {
  Search,
  ChevronDown,
  ChevronRight,
  GitBranch,
  BookOpen,
  Layers,
  Shield,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Circle,
  Network,
  Sparkles,
  FlaskConical,
  BookMarked,
  Zap,
  Info,
} from "lucide-react";
import {
  decodeSanskritConcept,
  checkDecoderHealth,
  RUNTIME_API_BASE,
} from "../services/sanskritDecoderApi";
import type {
  SanskritDecoderApiResponse,
  KnowledgeLayer,
  PipelineStage,
} from "../types/sanskrit";
import SanskritDecoderGraph from "./SanskritDecoderGraph";

// ── Constants ─────────────────────────────────────────────────────────────────
const PIPELINE_STAGES = [
  { key: "śabda",            label: "Śabda",           desc: "Sound-form / phonetic identity" },
  { key: "dhātu",           label: "Dhātu",            desc: "Root verb / primary semantic seed" },
  { key: "vyākaraṇa",      label: "Vyākaraṇa",        desc: "Grammar & derivation (Pāṇini)" },
  { key: "nirukta",         label: "Nirukta",          desc: "Etymological interpretation (Yāska)" },
  { key: "bīja",            label: "Bīja",             desc: "Seed-syllable / acoustic form" },
  { key: "tattva",          label: "Tattva",           desc: "Cosmic principle / elemental reality" },
  { key: "śakti",           label: "Śakti",            desc: "Dynamic power / transformative force" },
  { key: "functional_meaning", label: "Functional Meaning", desc: "Civilizational operational definition" },
];

const KNOWLEDGE_LAYER_GROUPS = [
  {
    group: "Core Linguistic",
    icon: BookOpen,
    layers: ["literal_meaning", "functional_meaning"],
  },
  {
    group: "Philosophical Domains",
    icon: Sparkles,
    layers: ["ontology", "cosmology", "psychology", "governance"],
  },
  {
    group: "Scientific Applications",
    icon: FlaskConical,
    layers: ["medicine", "engineering", "mathematics", "astronomy", "metallurgy"],
  },
  {
    group: "Ritual & Symbolism",
    icon: Zap,
    layers: ["ritual", "symbolism"],
  },
  {
    group: "Relational Network",
    icon: Network,
    layers: [
      "related_deities", "related_lokas", "related_koshas",
      "related_chakras", "related_yantras", "related_mantras",
      "related_vidyas", "related_shastras",
    ],
  },
  {
    group: "Hermeneutics & History",
    icon: BookMarked,
    layers: ["traditional_interpretations", "historical_evolution", "comparative_hermeneutics"],
  },
  {
    group: "Research Classification",
    icon: FlaskConical,
    layers: ["open_research_questions", "experimental_hypotheses"],
  },
];

const SUGGESTED_CONCEPTS = [
  "dharma", "karma", "prana", "atman", "brahman", "shakti",
  "yajna", "moksha", "yoga", "vidya", "guru", "maya",
  "akasha", "agni", "rta", "om", "purusha", "prakrti",
];

// ── Helper components ─────────────────────────────────────────────────────────

const EvidenceBadge: React.FC<{ status: string }> = ({ status }) => {
  const map: Record<string, { label: string; className: string }> = {
    EVIDENCE_BACKED:                  { label: "Evidence Backed",   className: "bg-emerald-900/50 text-emerald-300 border-emerald-700/60" },
    NO_RETRIEVED_EVIDENCE:            { label: "No Evidence",       className: "bg-gray-800/50 text-gray-400 border-gray-700/40" },
    NOT_ASSERTED:                     { label: "Not Asserted",      className: "bg-gray-800/30 text-gray-500 border-gray-800/40" },
    EXPLICITLY_MARKED_EXPERIMENTAL:   { label: "Experimental",      className: "bg-amber-900/40 text-amber-300 border-amber-700/40" },
    SOURCE_SCOPED:                    { label: "Source Scoped",     className: "bg-blue-900/50 text-blue-300 border-blue-700/40" },
    UNVERIFIED:                       { label: "Unverified",        className: "bg-red-900/30 text-red-400 border-red-800/40" },
    DERIVED:                          { label: "Derived",           className: "bg-purple-900/30 text-purple-400 border-purple-800/40" },
  };
  const config = map[status] ?? { label: status, className: "bg-gray-800/30 text-gray-500 border-gray-700/30" };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border ${config.className}`}>
      {config.label}
    </span>
  );
};

const LayerRow: React.FC<{ layerKey: string; layer: KnowledgeLayer }> = ({ layerKey, layer }) => {
  const [open, setOpen] = useState(false);
  if (layer.status === "NOT_ASSERTED" || layer.status === "NO_RETRIEVED_EVIDENCE") {
    return (
      <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-900/20 border border-gray-800/30">
        <span className="text-gray-600 text-xs capitalize">{layerKey.replace(/_/g, " ")}</span>
        <EvidenceBadge status={layer.status} />
      </div>
    );
  }
  const firstClaim = layer.claims[0];
  return (
    <div className="rounded-lg border border-gray-700/40 overflow-hidden">
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center justify-between px-3 py-2.5 bg-gray-900/40 hover:bg-gray-800/60 transition-colors"
        id={`layer-${layerKey}`}
      >
        <div className="flex items-center gap-2">
          {open ? (
            <ChevronDown size={12} className="text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronRight size={12} className="text-gray-400 flex-shrink-0" />
          )}
          <span className="text-gray-200 text-xs font-medium capitalize">
            {layerKey.replace(/_/g, " ")}
          </span>
        </div>
        <EvidenceBadge status={layer.status} />
      </button>

      {open && (
        <div className="px-4 py-3 bg-gray-950/60 space-y-2 border-t border-gray-800/40">
          {/* Panini grammar enrichment */}
          {layer.panini_grammar?.panini_sutras?.length ? (
            <div className="mb-2 p-2 rounded bg-purple-950/40 border border-purple-800/30">
              <div className="text-purple-300 text-[10px] font-semibold mb-1">
                Pāṇini Sūtras ({layer.panini_grammar.panini_sutras.length})
              </div>
              {layer.panini_grammar.panini_sutras.map((s, i) => (
                <div key={i} className="text-gray-300 text-xs mb-1">
                  <span className="text-purple-400 font-mono">{s.sutra_number}</span>{" "}
                  <span>{s.sutra_text}</span>{" "}
                  {s.gloss && <span className="text-gray-500">— {s.gloss}</span>}
                </div>
              ))}
            </div>
          ) : null}

          {/* Acoustic phonetics enrichment */}
          {layer.acoustic_phonetics?.claims?.length ? (
            <div className="mb-2 p-2 rounded bg-teal-950/40 border border-teal-800/30">
              <div className="text-teal-300 text-[10px] font-semibold mb-1">Śikṣā Acoustic Phonetics</div>
              {layer.acoustic_phonetics.claims.map((c, i) => {
                const v = c.value as Record<string, string | undefined>;
                return (
                  <div key={i} className="text-gray-300 text-xs grid grid-cols-2 gap-1">
                    {v.iast && <span>IAST: <span className="font-mono text-teal-300">{v.iast}</span></span>}
                    {v.ipa && <span>IPA: <span className="font-mono text-teal-300">{v.ipa}</span></span>}
                    {v.varna_class && <span>Class: <span className="text-gray-400">{v.varna_class}</span></span>}
                    {v.sthana && <span>Sthāna: <span className="text-gray-400">{v.sthana}</span></span>}
                  </div>
                );
              })}
            </div>
          ) : null}

          {/* Darshana matrix */}
          {layer.darshana_matrix && Object.keys(layer.darshana_matrix).length > 0 && (
            <div className="mb-2 space-y-1">
              {Object.entries(layer.darshana_matrix).map(([trad, entry]) => (
                <div key={trad} className="p-2 rounded bg-indigo-950/30 border border-indigo-800/20">
                  <div className="text-indigo-300 text-[10px] font-semibold capitalize mb-0.5">{trad}</div>
                  <div className="text-gray-300 text-xs">{entry.position}</div>
                </div>
              ))}
            </div>
          )}

          {/* Regular claims */}
          {layer.claims.map((claim, i) => (
            <div key={i} className="text-gray-300 text-xs leading-relaxed">
              {typeof claim.value === "string"
                ? claim.value
                : Array.isArray(claim.value)
                ? (claim.value as string[]).join(", ")
                : JSON.stringify(claim.value)}
            </div>
          ))}

          {/* Provenance */}
          {firstClaim?.provenance?.[0] && (
            <div className="mt-2 flex items-start gap-1.5 text-[10px] text-gray-500">
              <Shield size={10} className="mt-0.5 flex-shrink-0 text-gray-600" />
              <span className="font-mono break-all">
                {firstClaim.provenance[0].source_path}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ── Main component ─────────────────────────────────────────────────────────────

const SanskritDecoder: React.FC = () => {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SanskritDecoderApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"pipeline" | "layers" | "graph" | "provenance">("pipeline");
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(["Core Linguistic"]));
  const [healthStatus, setHealthStatus] = useState<"unknown" | "online" | "offline">("unknown");
  const inputRef = useRef<HTMLInputElement>(null);

  // Health check on mount
  useEffect(() => {
    checkDecoderHealth().then(({ online }) => {
      setHealthStatus(online ? "online" : "offline");
    });
  }, []);

  const handleDecode = useCallback(async (q?: string) => {
    const finalQuery = (q ?? query).trim();
    if (!finalQuery) return;
    setQuery(finalQuery);
    setLoading(true);
    setError(null);
    setResult(null);
    setActiveTab("pipeline");
    try {
      const res = await decodeSanskritConcept(finalQuery);
      setResult(res);
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to reach the Sanskrit decoder runtime. Ensure the backend is running on port 8001.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleDecode();
  };

  const toggleGroup = (group: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      next.has(group) ? next.delete(group) : next.add(group);
      return next;
    });
  };

  const concept = result?.decoder_result?.canonical_concept;
  const civilizational = result?.decoder_result?.civilizational_knowledge;
  const pipeline = result?.decoder_result?.pipeline ?? [];
  const graph = result?.decoder_result?.knowledge_graph;
  const govResponse = result?.decoder_result?.governed_response;
  const provenance = result?.decoder_result?.provenance;
  const isNotFound = result && !concept;

  return (
    <div className="min-h-screen bg-black text-white font-sans">
      {/* Header */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-purple-950/30 via-black to-black pointer-events-none" />
        <div className="relative max-w-5xl mx-auto px-4 pt-10 pb-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-violet-800 flex items-center justify-center text-lg font-bold shadow-lg shadow-purple-900/50">
                ॐ
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-300 via-violet-200 to-white bg-clip-text text-transparent">
                  Sanskrit Knowledge Decoder
                </h1>
                <p className="text-gray-500 text-xs mt-0.5">
                  UniGuru Native Civilizational Intelligence Engine · Isha Singh · Sprint 2026
                </p>
              </div>
            </div>
            {/* Health badge */}
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs ${
              healthStatus === "online"
                ? "bg-emerald-950/50 border-emerald-700/50 text-emerald-400"
                : healthStatus === "offline"
                ? "bg-red-950/50 border-red-800/50 text-red-400"
                : "bg-gray-900/50 border-gray-700/50 text-gray-500"
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full ${
                healthStatus === "online" ? "bg-emerald-400 animate-pulse" :
                healthStatus === "offline" ? "bg-red-400" : "bg-gray-500"
              }`} />
              {healthStatus === "online" ? "Runtime Online" : healthStatus === "offline" ? "Runtime Offline" : "Checking…"}
            </div>
          </div>

          {/* Description */}
          <p className="text-gray-400 text-sm max-w-2xl mt-4 leading-relaxed">
            Decodes Sanskrit concepts through their own epistemology — Śabda → Dhātu → Vyākaraṇa →
            Nirukta → Bīja → Tattva → Śakti → Functional Meaning. Every claim is source-scoped,
            every statement is evidence-classified, every execution is replay-safe.
          </p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 pb-16 space-y-6">
        {/* Search box */}
        <div className="relative">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search
                size={16}
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500"
              />
              <input
                ref={inputRef}
                id="sanskrit-decoder-query"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Enter a Sanskrit concept — dharma, karma, prana, ॐ, धर्म …"
                className="w-full pl-10 pr-4 py-3.5 rounded-xl bg-gray-900 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-600/60 focus:border-purple-600 transition-all text-sm"
                autoComplete="off"
                spellCheck={false}
              />
            </div>
            <button
              id="sanskrit-decode-btn"
              onClick={() => handleDecode()}
              disabled={loading || !query.trim()}
              className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-purple-700 to-violet-700 hover:from-purple-600 hover:to-violet-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-all flex items-center gap-2 shadow-lg shadow-purple-900/30"
            >
              {loading ? (
                <RefreshCw size={15} className="animate-spin" />
              ) : (
                <Layers size={15} />
              )}
              {loading ? "Decoding…" : "Decode"}
            </button>
          </div>

          {/* Suggestions */}
          <div className="flex flex-wrap gap-2 mt-3">
            {SUGGESTED_CONCEPTS.map((c) => (
              <button
                key={c}
                id={`suggest-${c}`}
                onClick={() => handleDecode(c)}
                className="px-2.5 py-1 rounded-lg bg-gray-900/60 border border-gray-800 text-gray-400 text-xs hover:border-purple-700/60 hover:text-purple-300 hover:bg-purple-950/30 transition-all"
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-3 p-4 rounded-xl bg-red-950/30 border border-red-800/50">
            <AlertCircle size={16} className="text-red-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-red-300">
              <div className="font-semibold mb-0.5">Decoder Error</div>
              <div className="text-red-400 text-xs">{error}</div>
              <div className="text-gray-500 text-xs mt-1">Runtime URL: {RUNTIME_API_BASE}</div>
            </div>
          </div>
        )}

        {/* Not Found */}
        {isNotFound && (
          <div className="flex items-start gap-3 p-4 rounded-xl bg-gray-900/50 border border-gray-700">
            <Info size={16} className="text-gray-400 flex-shrink-0 mt-0.5" />
            <div>
              <div className="text-gray-300 font-semibold text-sm mb-0.5">No Canonical Record Found</div>
              <div className="text-gray-500 text-xs">
                "{query}" did not match any canonical Sanskrit lexical record in the
                UniGuru registry. Try the Devanagari script form or a transliteration
                variant. Evidence classification: UNVERIFIED.
              </div>
            </div>
          </div>
        )}

        {/* ── Results ──────────────────────────────────────────────────────── */}
        {concept && (
          <>
            {/* Concept header card */}
            <div className="rounded-2xl bg-gradient-to-br from-gray-900 via-purple-950/20 to-gray-900 border border-purple-800/40 p-5 shadow-xl">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="text-4xl font-bold text-purple-200 mb-1">
                    {concept.sanskrit}
                  </div>
                  <div className="text-gray-300 text-lg font-semibold">
                    {concept.transliteration}
                  </div>
                  <div className="text-gray-500 text-sm mt-0.5 font-mono">
                    {concept.concept_id}
                  </div>
                </div>
                <div className="flex flex-col gap-2 items-end">
                  <EvidenceBadge
                    status={govResponse?.evidence_classification?.classification ?? "SOURCE_SCOPED"}
                  />
                  {result?.replay?.replay_safe && (
                    <div className="flex items-center gap-1 text-xs text-emerald-400">
                      <CheckCircle2 size={11} />
                      Replay Safe
                    </div>
                  )}
                  {civilizational?.coverage && (
                    <div className="text-xs text-gray-500">
                      Coverage:{" "}
                      <span className="text-purple-400 font-semibold">
                        {civilizational.coverage.coverage_pct}%
                      </span>{" "}
                      ({civilizational.coverage.evidence_backed_layers}/
                      {civilizational.coverage.total_layers} layers)
                    </div>
                  )}
                </div>
              </div>

              {/* Functional meaning */}
              {concept.functional_meaning && (
                <div className="mt-4 p-3 rounded-xl bg-black/40 border border-gray-800/60">
                  <div className="text-gray-500 text-xs mb-1 uppercase tracking-wider">
                    Functional Meaning
                  </div>
                  <div className="text-gray-200 text-sm leading-relaxed">
                    {concept.functional_meaning}
                  </div>
                </div>
              )}

              {/* Related concepts */}
              {concept.related_concepts?.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {concept.related_concepts.map((rc) => (
                    <button
                      key={rc}
                      onClick={() => handleDecode(rc)}
                      className="px-2.5 py-0.5 rounded-full bg-purple-950/40 border border-purple-800/40 text-purple-300 text-xs hover:bg-purple-900/50 transition-all"
                    >
                      {rc}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Tab navigation */}
            <div className="flex gap-1 bg-gray-900/60 rounded-xl p-1 border border-gray-800/60">
              {[
                { id: "pipeline", label: "Pipeline", icon: GitBranch },
                { id: "layers",   label: "Knowledge Layers", icon: Layers },
                { id: "graph",    label: "Knowledge Graph", icon: Network },
                { id: "provenance", label: "Provenance", icon: Shield },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  id={`tab-${id}`}
                  onClick={() => setActiveTab(id as typeof activeTab)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-all ${
                    activeTab === id
                      ? "bg-purple-700 text-white shadow-md"
                      : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
                  }`}
                >
                  <Icon size={13} />
                  <span className="hidden sm:inline">{label}</span>
                </button>
              ))}
            </div>

            {/* ── Pipeline Tab ─────────────────────────────────────────── */}
            {activeTab === "pipeline" && (
              <div className="space-y-2">
                <div className="text-gray-500 text-xs mb-3">
                  Canonical decoder pipeline — every stage traceable to source
                </div>
                {PIPELINE_STAGES.map((def, idx) => {
                  const stage = pipeline.find((p: PipelineStage) => p.stage === def.key);
                  const value = stage?.value ?? concept[def.key.replace(/[āīū]/g, (c) =>
                    c === "ā" ? "a" : c === "ī" ? "i" : "u"
                  ) as keyof typeof concept] as string | null;
                  return (
                    <div
                      key={def.key}
                      className="flex items-start gap-3 p-4 rounded-xl bg-gray-900/40 border border-gray-800/40 hover:border-purple-800/40 transition-all"
                    >
                      {/* Step indicator */}
                      <div className="flex flex-col items-center">
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 ${
                          value
                            ? "bg-purple-900 border-purple-600 text-purple-200"
                            : "bg-gray-900 border-gray-700 text-gray-600"
                        }`}>
                          {idx + 1}
                        </div>
                        {idx < PIPELINE_STAGES.length - 1 && (
                          <div className="w-px h-4 bg-gray-800 mt-1" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-purple-300 font-semibold text-sm">{def.label}</span>
                          {value ? (
                            <CheckCircle2 size={11} className="text-emerald-400" />
                          ) : (
                            <Circle size={11} className="text-gray-600" />
                          )}
                        </div>
                        <div className="text-gray-600 text-xs mb-1.5">{def.desc}</div>
                        {value ? (
                          <div className="text-gray-200 text-sm leading-relaxed">{value}</div>
                        ) : (
                          <div className="text-gray-600 text-xs italic">Not asserted in source record</div>
                        )}
                        {stage?.lineage && (
                          <div className="mt-1.5 text-[10px] text-gray-600 font-mono">
                            ↳ {stage.lineage.source_path}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* ── Knowledge Layers Tab ─────────────────────────────────── */}
            {activeTab === "layers" && civilizational && (
              <div className="space-y-3">
                {KNOWLEDGE_LAYER_GROUPS.map(({ group, icon: Icon, layers }) => {
                  const hasEvidence = layers.some(
                    (k) => civilizational.layers[k]?.status === "EVIDENCE_BACKED"
                  );
                  return (
                    <div key={group} className="rounded-xl border border-gray-800/50 overflow-hidden">
                      <button
                        id={`group-${group.toLowerCase().replace(/\s+/g, "-")}`}
                        onClick={() => toggleGroup(group)}
                        className="w-full flex items-center justify-between px-4 py-3 bg-gray-900/60 hover:bg-gray-800/60 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Icon size={14} className="text-purple-400" />
                          <span className="text-sm font-semibold text-gray-200">{group}</span>
                          {hasEvidence && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-950/50 text-emerald-400 border border-emerald-800/40">
                              Evidence Available
                            </span>
                          )}
                        </div>
                        {expandedGroups.has(group) ? (
                          <ChevronDown size={14} className="text-gray-500" />
                        ) : (
                          <ChevronRight size={14} className="text-gray-500" />
                        )}
                      </button>
                      {expandedGroups.has(group) && (
                        <div className="p-3 space-y-1.5 bg-black/20">
                          {layers.map((layerKey) => {
                            const layer = civilizational.layers[layerKey];
                            if (!layer) return (
                              <div key={layerKey} className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-gray-900/20 border border-gray-800/20">
                                <span className="text-gray-700 text-xs capitalize">{layerKey.replace(/_/g, " ")}</span>
                                <span className="text-gray-700 text-[10px]">—</span>
                              </div>
                            );
                            return <LayerRow key={layerKey} layerKey={layerKey} layer={layer} />;
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Cross-references */}
                {result?.decoder_result?.cross_references?.length > 0 && (
                  <div className="rounded-xl border border-gray-800/50 overflow-hidden">
                    <div className="px-4 py-3 bg-gray-900/60">
                      <div className="flex items-center gap-2">
                        <GitBranch size={14} className="text-purple-400" />
                        <span className="text-sm font-semibold text-gray-200">Cross-Text Synthesis</span>
                      </div>
                    </div>
                    <div className="p-3 space-y-1.5 bg-black/20">
                      {result.decoder_result.cross_references.map((xr, i) => (
                        <div key={i} className="flex items-start gap-2 px-3 py-2 rounded-lg bg-gray-900/30 border border-gray-800/30">
                          <ChevronRight size={12} className="text-purple-500 mt-0.5 flex-shrink-0" />
                          <div>
                            <button
                              onClick={() => handleDecode(xr.target)}
                              className="text-purple-300 text-xs font-medium hover:text-purple-200 transition-colors"
                            >
                              {xr.target}
                            </button>
                            <div className="text-gray-500 text-xs mt-0.5">{xr.claim}</div>
                          </div>
                          <EvidenceBadge status={xr.classification} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── Graph Tab ────────────────────────────────────────────── */}
            {activeTab === "graph" && graph && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-gray-500 text-xs">
                    {graph.metadata.node_count} nodes · {graph.metadata.edge_count} edges ·{" "}
                    <span className="text-purple-400">Civilizational Knowledge Graph V3</span>
                  </div>
                  <div className={`flex items-center gap-1 text-xs ${
                    graph.metadata.consistency_valid ? "text-emerald-400" : "text-red-400"
                  }`}>
                    {graph.metadata.consistency_valid ? (
                      <CheckCircle2 size={11} />
                    ) : (
                      <AlertCircle size={11} />
                    )}
                    Graph {graph.metadata.consistency_valid ? "Consistent" : "Invalid"}
                  </div>
                </div>
                <SanskritDecoderGraph
                  nodes={graph.nodes}
                  edges={graph.edges}
                  width={700}
                  height={440}
                />
                <div className="text-[10px] text-gray-600 font-mono">
                  graph_id: {graph.graph_id} · snapshot_hash:{" "}
                  {graph.metadata.source_snapshot_hash?.slice(0, 16)}
                </div>
              </div>
            )}

            {/* ── Provenance Tab ───────────────────────────────────────── */}
            {activeTab === "provenance" && provenance && (
              <div className="space-y-4">
                {/* Replay banner */}
                <div className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm ${
                  provenance.replay_safe
                    ? "bg-emerald-950/30 border-emerald-800/40 text-emerald-300"
                    : "bg-red-950/30 border-red-800/40 text-red-300"
                }`}>
                  {provenance.replay_safe ? (
                    <CheckCircle2 size={14} />
                  ) : (
                    <AlertCircle size={14} />
                  )}
                  <span>
                    {provenance.replay_safe
                      ? "Execution is replay-safe — deterministic output guaranteed"
                      : "Replay safety flag NOT set"}
                  </span>
                </div>

                {/* Metadata */}
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: "Registry Version", value: provenance.registry_version },
                    { label: "Schema Version", value: provenance.schema_version },
                    { label: "Concept ID", value: provenance.lineage?.concept_id },
                    { label: "Trace ID", value: result?.trace_id },
                    { label: "Response Hash", value: result?.response_hash?.slice(0, 20) + "…" },
                    { label: "Replay Key", value: result?.replay?.replay_key?.slice(0, 20) + "…" },
                  ].map(({ label, value }) => (
                    <div key={label} className="p-3 rounded-lg bg-gray-900/40 border border-gray-800/40">
                      <div className="text-gray-600 text-[10px] uppercase tracking-wider mb-0.5">{label}</div>
                      <div className="text-gray-300 text-xs font-mono break-all">{value ?? "—"}</div>
                    </div>
                  ))}
                </div>

                {/* Source documents */}
                <div>
                  <div className="text-gray-500 text-xs mb-2 uppercase tracking-wider">Source Documents</div>
                  <div className="space-y-2">
                    {provenance.source_documents?.map((doc, i) => (
                      <div key={i} className="p-3 rounded-lg bg-gray-900/40 border border-gray-800/40">
                        <div className="flex items-center gap-2 mb-1">
                          <Shield size={11} className="text-purple-400" />
                          <span className="text-purple-300 text-xs font-mono">{doc.source_path}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-x-4 text-[10px] text-gray-500">
                          <span>Source: <span className="text-gray-400">{doc.source}</span></span>
                          <span>Evidence: <span className="text-gray-400">{doc.evidence_type}</span></span>
                          <span className="col-span-2 font-mono">
                            hash: {doc.content_hash?.slice(0, 24)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Lineage path */}
                {provenance.lineage?.source_path && (
                  <div className="p-3 rounded-lg bg-purple-950/20 border border-purple-800/30">
                    <div className="text-gray-500 text-[10px] uppercase tracking-wider mb-1">
                      Knowledge Lineage
                    </div>
                    <div className="font-mono text-purple-300 text-xs">
                      {provenance.lineage.source_path}
                    </div>
                    <div className="font-mono text-gray-600 text-[10px] mt-0.5">
                      hash: {provenance.lineage.content_hash?.slice(0, 24)}
                    </div>
                  </div>
                )}

                {/* Governance */}
                {govResponse && (
                  <div className="p-4 rounded-xl bg-gray-900/40 border border-gray-800/40">
                    <div className="text-gray-500 text-xs uppercase tracking-wider mb-2">
                      Governance State
                    </div>
                    <div className="space-y-1.5 text-xs">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Governance</span>
                        <span className="text-gray-300 font-mono">{govResponse.governance_state}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Research Class</span>
                        <span className="text-gray-300 font-mono">{govResponse.research_classification}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Evidence Types</span>
                        <div className="flex gap-1 flex-wrap justify-end">
                          {govResponse.evidence_classification?.evidence_types?.map((et) => (
                            <span key={et} className="text-[10px] px-1.5 py-0.5 rounded bg-purple-950/50 text-purple-400 border border-purple-800/30">
                              {et}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="text-gray-600 text-[10px] mt-2 leading-relaxed">
                        {govResponse.evidence_classification?.notes}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* Empty state */}
        {!loading && !result && !error && (
          <div className="text-center py-16 space-y-4">
            <div className="text-6xl opacity-20 select-none">ॐ</div>
            <div className="text-gray-600 text-sm">
              Enter any Sanskrit concept above to decode its civilizational meaning
            </div>
            <div className="text-gray-700 text-xs max-w-md mx-auto">
              The decoder exposes Śabda, Dhātu, Vyākaraṇa, Nirukta, Bīja, Tattva, Śakti,
              35 knowledge layers, and the full civilizational knowledge graph —
              all source-backed and provenance-tagged.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SanskritDecoder;

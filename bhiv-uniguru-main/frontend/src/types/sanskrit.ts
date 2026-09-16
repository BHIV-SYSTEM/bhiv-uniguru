/**
 * Sanskrit Knowledge Decoder — TypeScript Types
 *
 * Mirrors the canonical schemas defined in:
 *   backend/ontology/sanskrit/schema.py
 *   backend/ontology/sanskrit_decoder.py  (UNIGURU_CIVILIZATIONAL_KNOWLEDGE_OBJECT_V3)
 *   backend/service/uniguru_runtime_api.py (UNIGURU_SANSKRIT_DECODER_RESPONSE_V1)
 */

// ── Evidence & Provenance ──────────────────────────────────────────────────────

export type EvidenceType =
  | "BHAGAVAD_GITA"
  | "UPANISHAD"
  | "VEDA"
  | "PRIMARY_CANON"
  | "PANINI"
  | "NIRUKTA"
  | "COMMENTARY"
  | "TRADITION"
  | "DERIVED";

export interface Provenance {
  source_id: string;
  source: string;
  document: string;
  section: string;
  retrieval_path: string;
  evidence_type: EvidenceType;
  source_path: string;
  content_hash: string;
  retrieval_system: string;
  confidence?: number;
  source_type?: string;
}

export interface EvidenceClaim {
  value: unknown;
  classification: "SOURCE_SCOPED" | "DERIVED" | "EXPERIMENTAL" | string;
  provenance: Provenance[];
}

// ── Sanskrit Concept Object ────────────────────────────────────────────────────

export interface SanskritConcept {
  concept_id: string;
  canonical_name: string;
  sanskrit: string;
  transliteration: string;
  shabda: string;
  dhatu: string;
  vyakarana: string;
  nirukta: string;
  beeja: string | null;
  tattva: string | null;
  shakti: string | null;
  functional_meaning: string;
  related_concepts: string[];
  ontology_version: string;
  semantic_version: string;
}

// ── Pipeline ──────────────────────────────────────────────────────────────────

export interface PipelineStage {
  stage: string;          // e.g. "śabda", "dhātu", "vyākaraṇa" …
  schema_field: string;   // internal field name
  value: string | null;
  evidence: Provenance[];
  classification: EvidenceType[];
  lineage: {
    concept_id: string;
    source_path: string;
    content_hash: string;
  };
}

// ── Knowledge Layer ───────────────────────────────────────────────────────────

export interface PaniniGrammar {
  status: "EVIDENCE_BACKED" | "NO_RETRIEVED_EVIDENCE";
  dhatu_root_key: string;
  panini_sutras: Array<{
    sutra_number: string;
    sutra_text: string;
    rule_class: string;
    gloss: string;
    pada: string;
    derived_word: string;
    provenance: Provenance;
  }>;
  provenance: Provenance[];
  source: string;
}

export interface AcousticPhonetics {
  status: "EVIDENCE_BACKED" | "NO_RETRIEVED_EVIDENCE";
  claims: EvidenceClaim[];
  provenance: Provenance[];
  source?: string;
}

export interface DarshanaMatrix {
  [tradition: string]: {
    position: string;
    key_terms: string;
    source_text: string;
    evidence_type: EvidenceType;
    provenance: Provenance[];
  };
}

export interface KnowledgeLayer {
  status: "EVIDENCE_BACKED" | "NO_RETRIEVED_EVIDENCE" | "NOT_ASSERTED" | "EXPLICITLY_MARKED_EXPERIMENTAL";
  claims: EvidenceClaim[];
  // Enrichments (only on specific layers)
  panini_grammar?: PaniniGrammar;
  acoustic_phonetics?: AcousticPhonetics;
  // Comparative hermeneutics layer
  darshana_matrix?: DarshanaMatrix;
  traditions_represented?: string[];
  // Experimental
  policy?: string;
}

// ── Knowledge Object ──────────────────────────────────────────────────────────

export interface CivilizationalKnowledge {
  schema_version: string;
  concept_id: string;
  canonical_name: string;
  lexical_record: SanskritConcept;
  layers: {
    sanskrit?: KnowledgeLayer;
    shabda?: KnowledgeLayer;
    dhatu?: KnowledgeLayer;
    vyakarana?: KnowledgeLayer;
    nirukta?: KnowledgeLayer;
    beeja?: KnowledgeLayer;
    tattva?: KnowledgeLayer;
    shakti?: KnowledgeLayer;
    literal_meaning?: KnowledgeLayer;
    functional_meaning?: KnowledgeLayer;
    ontology?: KnowledgeLayer;
    cosmology?: KnowledgeLayer;
    psychology?: KnowledgeLayer;
    governance?: KnowledgeLayer;
    medicine?: KnowledgeLayer;
    engineering?: KnowledgeLayer;
    mathematics?: KnowledgeLayer;
    astronomy?: KnowledgeLayer;
    metallurgy?: KnowledgeLayer;
    ritual?: KnowledgeLayer;
    symbolism?: KnowledgeLayer;
    related_deities?: KnowledgeLayer;
    related_lokas?: KnowledgeLayer;
    related_koshas?: KnowledgeLayer;
    related_chakras?: KnowledgeLayer;
    related_yantras?: KnowledgeLayer;
    related_mantras?: KnowledgeLayer;
    related_vidyas?: KnowledgeLayer;
    related_shastras?: KnowledgeLayer;
    traditional_interpretations?: KnowledgeLayer;
    historical_evolution?: KnowledgeLayer;
    cross_references?: KnowledgeLayer;
    open_research_questions?: KnowledgeLayer;
    experimental_hypotheses?: KnowledgeLayer;
    comparative_hermeneutics?: KnowledgeLayer;
    [key: string]: KnowledgeLayer | undefined;
  };
  retrieved_evidence: Array<{
    knowledge_id: string;
    content: string;
    source: string;
    source_type: string;
    domain: string | null;
    tags: string[];
    match_terms: string[];
    provenance: Provenance;
  }>;
  retrieval: {
    system: string;
    strategy: string;
    records_found: number;
  };
  coverage: {
    total_layers: number;
    evidence_backed_layers: number;
    coverage_pct: number;
  };
}

// ── Graph ─────────────────────────────────────────────────────────────────────

export interface GraphNode {
  id: string;
  type: "sanskrit_concept" | "kosha" | "chakra" | "bija" | "loka" | "deity" | "shastra" | "yantra" | "vidya" | "knowledge_record" | string;
  label: string;
  address?: string;
  provenance: string | Provenance;
}

export interface GraphEdge {
  from: string;
  to: string;
  type: string;
  evidence_type: EvidenceType;
  provenance: string | Provenance;
  match_terms?: string[];
  hop?: number;
  from_type?: string;
  to_type?: string;
}

export interface KnowledgeGraph {
  graph_id: string;
  schema_version: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata: {
    adapter: string;
    consistency_valid: boolean;
    orphaned_nodes: string[];
    source_snapshot_hash: string;
    node_count: number;
    edge_count: number;
  };
}

// ── Full Decoder Result ───────────────────────────────────────────────────────

export interface CrossReference {
  target: string;
  claim: string;
  classification: string;
  source_path: string;
  status: string;
}

export interface GovernedResponse {
  evidence_classification: {
    classification: "SOURCE_SCOPED" | "UNVERIFIED" | string;
    evidence_types: EvidenceType[];
    notes: string;
  };
  research_classification: string;
  governance_state: string;
}

export interface DecoderResult {
  canonical_concept: SanskritConcept | null;
  civilizational_knowledge: CivilizationalKnowledge | null;
  pipeline: PipelineStage[];
  cross_references: CrossReference[];
  cross_text_synthesis: {
    status: string;
    canonical_claims?: EvidenceClaim[];
    retrieved_records?: unknown[];
    conflicts: unknown[];
    uncertainty?: string;
  };
  knowledge_graph: KnowledgeGraph;
  functional_meaning?: {
    summary: string;
    classification: string;
  };
  provenance: {
    registry_version: string;
    schema_version: string;
    source_documents: Provenance[];
    retrieved_records: Array<{ knowledge_id: string; provenance: Provenance }>;
    lineage: { concept_id: string; source_path: string; content_hash: string };
    replay_safe: boolean;
  };
  governed_response: GovernedResponse;
  result_hash: string;
}

export interface ChantMeterInfo {
  meter_name: string;
  sanskrit_name?: string;
  syllable_count?: number;
  laghu_guru_pattern?: string;
  description?: string;
  confidence?: number;
}

export interface ChantAudioMetadata {
  duration_seconds?: number;
  sample_rate?: number;
  channels?: number;
  format?: string;
}

export interface ChantAudioInfo {
  audio_id: string;
  available: boolean;
  audio_url?: string;
  engine?: string;
  source?: string;
  meter?: ChantMeterInfo;
  metadata?: ChantAudioMetadata;
  text?: string;
  normalized_text?: string;
  reason?: string;
}

// ── API Response Wrappers ─────────────────────────────────────────────────────

export interface SanskritDecoderApiResponse {
  trace_id: string;
  decoder_result: DecoderResult;
  governed_response: GovernedResponse;
  replay: {
    replay_key: string;
    replay_safe: boolean;
    input_trace_id_accepted: boolean;
  };
  audio?: ChantAudioInfo;
  schema_version: string;
  response_hash: string;
}

// ── Graph Traversal ───────────────────────────────────────────────────────────

export interface GraphTraversalApiResponse {
  trace_id: string;
  traversal_result: {
    start: string;
    max_depth: number;
    edge_type_filter: string[] | "all";
    path: Array<{
      hop: number;
      node_id: string;
      node_label: string;
      node_type: string;
      incoming_edge_type: string | null;
      provenance: string;
    }>;
    sub_graph: {
      nodes: GraphNode[];
      edges: GraphEdge[];
      node_count: number;
      edge_count: number;
    };
    traversal_metadata: {
      graph_id: string;
      schema_version: string;
      traversal_hash: string;
      replay_safe: boolean;
    };
  };
  schema_version: string;
  replay_safe: boolean;
  response_hash: string;
}

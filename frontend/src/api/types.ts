export type RiskCategory = "Low" | "Moderate" | "Elevated" | "High";

export type MatchedIndicator = { id: string; label: string; weight: number };

export type AnalysisPayload = {
  score: number;
  risk_category: RiskCategory;
  matched_indicators: MatchedIndicator[];
  explanations: string[];
  engine_version: string;
  analyzed_at: string | null;
};

export type RecordItem = {
  id: number;
  record_type: string;
  content_text: string;
  created_at: string | null;
  review_status: string;
  is_synthetic: boolean;
  account: { id: number; username: string; display_name: string; platform: string };
  analysis: AnalysisPayload | null;
};

export type RecordsResponse = {
  items: RecordItem[];
  total: number;
  page: number;
  page_size: number;
  filters: Record<string, string | null>;
};

export type RiskSlice = { category: string; count: number };
export type PlatformSlice = { platform: string; count: number };

export type Summary = {
  records: number;
  accounts: number;
  cases: number;
  pending_review: number;
  risk_distribution: RiskSlice[];
  platform_distribution: PlatformSlice[];
  account_distribution: PlatformSlice[];
  risk_basis: string;
  platform_basis: string;
  data_mode: string;
};

export type ActivityBucket = { bucket: string; count: number };

export type ActivityResponse = {
  interval: string;
  buckets: ActivityBucket[];
  total: number;
  distinct_buckets: number;
};

export type CaseItem = {
  id: number;
  title: string;
  description: string;
  status: string;
  record_count: number;
  created_at: string;
};

export type CaseDetail = CaseItem & {
  records: RecordItem[];
  notes: { id: number; record_id: number | null; note_text: string; disposition: string; created_at: string }[];
};

export type GraphNode = {
  id: string;
  account_id: number;
  label: string;
  display_name: string;
  platform: string;
  account_type: string;
  synthetic: boolean;
  created_at: string | null;
  record_count: number;
  record_ids: number[];
  risk_score: number;
  risk_category: RiskCategory;
  connection_count: number;
};

export type GraphEdge = {
  id: number;
  source: string;
  target: string;
  relationship_type: string;
  shared_feature: string;
  evidence_description: string;
  synthetic: boolean;
};

export type GraphData = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  risk_categories: string[];
  engine_version: string;
};

export type GraphNodeDetail = {
  id: string;
  account_id: number;
  label: string;
  display_name: string;
  platform: string;
  account_type: string;
  synthetic: boolean;
  created_at: string | null;
  record_count: number;
  risk_score: number;
  risk_category: RiskCategory;
  records: (RecordItem & { content_preview: string })[];
  relationships: {
    id: number;
    direction: string;
    counterpart_account_id: number;
    counterpart_label: string | null;
    counterpart_platform: string | null;
    relationship_type: string;
    shared_feature: string;
    evidence_description: string;
    synthetic: boolean;
  }[];
};

export type GraphEdgeDetail = {
  id: number;
  source: string;
  target: string;
  source_label: string | null;
  source_platform: string | null;
  target_label: string | null;
  target_platform: string | null;
  relationship_type: string;
  shared_feature: string;
  evidence_description: string;
  synthetic: boolean;
};

export type MetaResponse = {
  app: string;
  version: string;
  data_mode: string;
  engine_version: string;
  risk_categories: string[];
  risk_thresholds: Record<string, number>;
  methodology_principle: string;
  synthetic_data_notice: string;
  demo_auth: { enabled: boolean; mode: string; email: string; note: string };
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  expires_in_minutes: number;
  user: { email: string; role: string };
};

export type SessionResponse = {
  user: { email: string; role: string };
  expires_at: string;
  engine_version: string;
};

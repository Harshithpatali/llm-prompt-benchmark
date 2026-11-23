-- Consolidated LLM Quality Intelligence Platform schema.
-- PostgreSQL 15+ / Neon. Apply only after reviewing the target project and backup policy.

CREATE TABLE IF NOT EXISTS public.dataset_versions (
  dataset_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_name TEXT NOT NULL,
  version_label TEXT NOT NULL,
  sha256 CHAR(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  row_count INTEGER NOT NULL CHECK (row_count >= 0),
  source TEXT,
  license_note TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (dataset_name, sha256)
);

CREATE TABLE IF NOT EXISTS public.model_registry (
  model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  model_name TEXT NOT NULL,
  display_name TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider, model_name)
);

CREATE TABLE IF NOT EXISTS public.prompt_templates (
  prompt_template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_name TEXT NOT NULL,
  version_label TEXT NOT NULL,
  strategy TEXT NOT NULL,
  template_text TEXT NOT NULL,
  output_schema JSONB,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (template_name, version_label)
);

CREATE TABLE IF NOT EXISTS public.rubrics (
  rubric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rubric_name TEXT NOT NULL,
  version_label TEXT NOT NULL,
  objective TEXT NOT NULL,
  dimensions JSONB NOT NULL,
  decision_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'retired')),
  generator_provider TEXT,
  generator_model TEXT,
  approved_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (rubric_name, version_label)
);

CREATE TABLE IF NOT EXISTS public.evaluation_runs (
  run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_type TEXT NOT NULL CHECK (run_type IN ('prompt_benchmark', 'general_quality', 'seller_support')),
  dataset_version_id UUID REFERENCES public.dataset_versions(dataset_version_id),
  provider TEXT NOT NULL,
  model_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'partial', 'failed')),
  configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS public.evaluation_results (
  result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES public.evaluation_runs(run_id) ON DELETE CASCADE,
  case_id TEXT NOT NULL,
  strategy TEXT NOT NULL DEFAULT 'default',
  category TEXT NOT NULL,
  difficulty TEXT,
  prompt TEXT NOT NULL,
  context TEXT,
  reference_answer TEXT,
  response TEXT,
  status TEXT NOT NULL CHECK (status IN ('success', 'error')),
  metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_type TEXT,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (run_id, case_id, strategy)
);

CREATE TABLE IF NOT EXISTS public.evaluation_traces (
  trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  result_id UUID NOT NULL UNIQUE REFERENCES public.evaluation_results(result_id) ON DELETE CASCADE,
  provider_request_id TEXT,
  latency_ms NUMERIC(12,2) CHECK (latency_ms IS NULL OR latency_ms >= 0),
  prompt_tokens INTEGER CHECK (prompt_tokens IS NULL OR prompt_tokens >= 0),
  completion_tokens INTEGER CHECK (completion_tokens IS NULL OR completion_tokens >= 0),
  retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
  raw_response JSONB,
  trace_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.run_metrics (
  run_metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES public.evaluation_runs(run_id) ON DELETE CASCADE,
  metric_name TEXT NOT NULL,
  metric_value NUMERIC(16,6),
  dimension TEXT,
  metric_definition TEXT,
  evaluator_version TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (run_id, metric_name, dimension)
);

CREATE TABLE IF NOT EXISTS public.annotation_tasks (
  annotation_task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_key TEXT NOT NULL UNIQUE,
  source_dataset TEXT NOT NULL,
  source_task_id TEXT,
  result_id UUID REFERENCES public.evaluation_results(result_id) ON DELETE SET NULL,
  category TEXT NOT NULL,
  difficulty TEXT,
  query TEXT NOT NULL,
  context TEXT,
  candidate_response TEXT NOT NULL,
  review_guidance TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'claimed', 'submitted', 'adjudicated', 'cancelled')),
  assigned_to TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.annotations (
  annotation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  annotation_task_id UUID NOT NULL REFERENCES public.annotation_tasks(annotation_task_id) ON DELETE CASCADE,
  annotator_id TEXT NOT NULL,
  relevance TEXT NOT NULL CHECK (relevance IN ('pass', 'minor_issue', 'major_issue', 'not_applicable')),
  correctness TEXT NOT NULL CHECK (correctness IN ('pass', 'minor_issue', 'major_issue', 'not_applicable')),
  completeness TEXT NOT NULL CHECK (completeness IN ('pass', 'minor_issue', 'major_issue', 'not_applicable')),
  overall_label TEXT NOT NULL CHECK (overall_label IN ('accept', 'revise', 'reject', 'escalate')),
  evidence TEXT NOT NULL CHECK (length(trim(evidence)) >= 8),
  confidence SMALLINT NOT NULL CHECK (confidence BETWEEN 1 AND 5),
  handling_seconds INTEGER NOT NULL DEFAULT 0 CHECK (handling_seconds >= 0),
  escalated BOOLEAN NOT NULL DEFAULT FALSE,
  defect_category TEXT NOT NULL DEFAULT 'none',
  is_audit BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (annotation_task_id, annotator_id)
);

CREATE TABLE IF NOT EXISTS public.adjudications (
  adjudication_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  annotation_task_id UUID NOT NULL UNIQUE REFERENCES public.annotation_tasks(annotation_task_id) ON DELETE CASCADE,
  adjudicator_id TEXT NOT NULL,
  final_label TEXT NOT NULL CHECK (final_label IN ('accept', 'revise', 'reject', 'escalate')),
  evidence TEXT NOT NULL CHECK (length(trim(evidence)) >= 8),
  notes TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.judge_calibration_runs (
  calibration_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_version_id UUID REFERENCES public.dataset_versions(dataset_version_id),
  evaluator_version TEXT NOT NULL,
  thresholds JSONB NOT NULL,
  validation_metrics JSONB NOT NULL,
  holdout_metrics JSONB NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.quality_review_queue (
  review_queue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  result_id UUID NOT NULL UNIQUE REFERENCES public.evaluation_results(result_id) ON DELETE CASCADE,
  priority SMALLINT NOT NULL DEFAULT 0 CHECK (priority BETWEEN 0 AND 100),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'claimed', 'resolved', 'dismissed')),
  assigned_to TEXT,
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  claimed_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS public.audit_events (
  audit_event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor_id TEXT,
  event_type TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evaluation_runs_created_at ON public.evaluation_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_evaluation_runs_model ON public.evaluation_runs (provider, model_name);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_run ON public.evaluation_results (run_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_category ON public.evaluation_results (category, status);
CREATE INDEX IF NOT EXISTS idx_annotation_tasks_status ON public.annotation_tasks (status, category);
CREATE INDEX IF NOT EXISTS idx_annotations_task ON public.annotations (annotation_task_id);
CREATE INDEX IF NOT EXISTS idx_annotations_annotator ON public.annotations (annotator_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_review_queue_status ON public.quality_review_queue (status, priority DESC, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON public.audit_events (entity_type, entity_id, created_at DESC);

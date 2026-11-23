-- Rubric lifecycle and criterion-level judge evaluation.
ALTER TABLE public.rubrics ADD COLUMN IF NOT EXISTS source_csv TEXT;
ALTER TABLE public.rubrics ADD COLUMN IF NOT EXISTS sha256 CHAR(64);
ALTER TABLE public.rubrics ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE public.rubrics ADD COLUMN IF NOT EXISTS created_by TEXT;

CREATE TABLE IF NOT EXISTS public.rubric_evaluations (
  rubric_evaluation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rubric_id UUID NOT NULL REFERENCES public.rubrics(rubric_id),
  provider TEXT NOT NULL,
  judge_model TEXT NOT NULL,
  prompt_text TEXT NOT NULL,
  response_text TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('completed','failed')),
  summary JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS public.rubric_criterion_scores (
  criterion_score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rubric_evaluation_id UUID NOT NULL REFERENCES public.rubric_evaluations(rubric_evaluation_id) ON DELETE CASCADE,
  component_id TEXT NOT NULL,
  parent_category TEXT NOT NULL,
  criterion_name TEXT NOT NULL,
  evaluation_question TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK (verdict IN ('pass','fail','not_applicable')),
  evidence TEXT NOT NULL,
  rationale TEXT NOT NULL,
  confidence NUMERIC(4,3) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
  UNIQUE (rubric_evaluation_id, component_id)
);
CREATE INDEX IF NOT EXISTS idx_rubric_evaluations_rubric ON public.rubric_evaluations(rubric_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rubric_scores_eval ON public.rubric_criterion_scores(rubric_evaluation_id);

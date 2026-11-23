-- Human adjudication and judge calibration for rubric evaluations.
ALTER TABLE public.annotation_tasks
  ADD COLUMN IF NOT EXISTS rubric_evaluation_id UUID REFERENCES public.rubric_evaluations(rubric_evaluation_id) ON DELETE CASCADE;
CREATE UNIQUE INDEX IF NOT EXISTS uq_annotation_task_rubric_eval
  ON public.annotation_tasks(rubric_evaluation_id) WHERE rubric_evaluation_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.rubric_human_annotations (
  human_annotation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rubric_evaluation_id UUID NOT NULL REFERENCES public.rubric_evaluations(rubric_evaluation_id) ON DELETE CASCADE,
  component_id TEXT NOT NULL,
  annotator_id TEXT NOT NULL,
  verdict TEXT NOT NULL CHECK (verdict IN ('pass','fail','not_applicable')),
  evidence TEXT NOT NULL,
  rationale TEXT NOT NULL DEFAULT '',
  confidence SMALLINT NOT NULL CHECK (confidence BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (rubric_evaluation_id, component_id, annotator_id)
);

CREATE TABLE IF NOT EXISTS public.rubric_adjudications (
  rubric_adjudication_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rubric_evaluation_id UUID NOT NULL REFERENCES public.rubric_evaluations(rubric_evaluation_id) ON DELETE CASCADE,
  component_id TEXT NOT NULL,
  adjudicator_id TEXT NOT NULL,
  final_verdict TEXT NOT NULL CHECK (final_verdict IN ('pass','fail','not_applicable')),
  evidence TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (rubric_evaluation_id, component_id)
);

CREATE INDEX IF NOT EXISTS idx_rubric_human_annotations_eval
  ON public.rubric_human_annotations(rubric_evaluation_id, component_id);
CREATE INDEX IF NOT EXISTS idx_rubric_adjudications_eval
  ON public.rubric_adjudications(rubric_evaluation_id);

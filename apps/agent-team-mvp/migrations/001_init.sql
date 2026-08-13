-- AIエージェントチームMVP 初期スキーマ(要件定義 §7 データ要件)
--
-- 監査要件(FR-042)より、すべてのテーブルは case_id で連結する。
-- 実行の冪等性(FR-041)は execution_jobs.idempotency_key の一意制約で担保する。

CREATE TABLE IF NOT EXISTS cases (
  case_id                 TEXT PRIMARY KEY,
  objective               TEXT,
  due_date                TEXT,
  desired_artifacts       JSONB NOT NULL DEFAULT '[]'::jsonb,
  target_workflow         TEXT,
  business_owner          TEXT,
  approver                TEXT,
  permitted_operations    JSONB NOT NULL DEFAULT '[]'::jsonb,
  permitted_personal_data JSONB NOT NULL DEFAULT '[]'::jsonb,
  actor_roles             JSONB NOT NULL DEFAULT '[]'::jsonb,
  state                   TEXT NOT NULL,
  stage                   TEXT NOT NULL,
  risk                    TEXT NOT NULL,
  created_at              TIMESTAMPTZ NOT NULL,
  updated_at              TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS source_documents (
  source_id             TEXT PRIMARY KEY,
  case_id               TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  title                 TEXT NOT NULL,
  content               TEXT NOT NULL,
  classification        TEXT NOT NULL,
  updated_at            TIMESTAMPTZ NOT NULL,
  allowed_roles         JSONB NOT NULL DEFAULT '[]'::jsonb,
  retention_policy      TEXT NOT NULL,
  retention_expires_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_source_documents_case ON source_documents(case_id);

CREATE TABLE IF NOT EXISTS agent_runs (
  run_id                 TEXT PRIMARY KEY,
  case_id                TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  role                   TEXT NOT NULL,
  input_hash             TEXT NOT NULL,
  output_schema_version  TEXT NOT NULL,
  state                  TEXT NOT NULL,
  error                  TEXT,
  started_at             TIMESTAMPTZ NOT NULL,
  finished_at            TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_case ON agent_runs(case_id);

-- 成果物。claims は evidence_bundle の payload 内に保持し、
-- 併せて claims テーブルへ展開して claim_id 単位の追跡を可能にする。
CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id  TEXT PRIMARY KEY,
  case_id      TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  kind         TEXT NOT NULL,
  version      INTEGER NOT NULL,
  payload      JSONB NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL,
  UNIQUE (case_id, kind, version)
);
CREATE INDEX IF NOT EXISTS idx_artifacts_case ON artifacts(case_id);

CREATE TABLE IF NOT EXISTS claims (
  claim_id          TEXT PRIMARY KEY,
  case_id           TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  artifact_id       TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE CASCADE,
  statement         TEXT NOT NULL,
  source_id         TEXT NOT NULL,
  locator_start     INTEGER NOT NULL,
  locator_end       INTEGER NOT NULL,
  locator_quote     TEXT NOT NULL,
  source_updated_at TIMESTAMPTZ NOT NULL,
  confidence        REAL NOT NULL,
  kind              TEXT NOT NULL,
  subject_key       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_claims_case ON claims(case_id);

CREATE TABLE IF NOT EXISTS approval_requests (
  request_id       TEXT PRIMARY KEY,
  case_id          TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  packet           JSONB NOT NULL,
  status           TEXT NOT NULL,
  chat_message_id  TEXT,
  nonce_consumed   BOOLEAN NOT NULL DEFAULT FALSE,
  created_at       TIMESTAMPTZ NOT NULL,
  updated_at       TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_approval_requests_case ON approval_requests(case_id);

CREATE TABLE IF NOT EXISTS approval_decisions (
  decision_id     TEXT PRIMARY KEY,
  request_id      TEXT NOT NULL REFERENCES approval_requests(request_id) ON DELETE CASCADE,
  case_id         TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  decision        TEXT NOT NULL,
  reason          TEXT NOT NULL,
  conditions      JSONB NOT NULL DEFAULT '[]'::jsonb,
  decided_by      TEXT NOT NULL,
  decided_by_role TEXT NOT NULL,
  decided_at      TIMESTAMPTZ NOT NULL,
  granted_scope   JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_approval_decisions_case ON approval_decisions(case_id);

CREATE TABLE IF NOT EXISTS execution_jobs (
  execution_id        TEXT PRIMARY KEY,
  case_id             TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  operation           TEXT NOT NULL,
  target              TEXT NOT NULL,
  idempotency_key     TEXT NOT NULL,
  status              TEXT NOT NULL,
  result              TEXT NOT NULL,
  rollback_ref        TEXT,
  approval_request_id TEXT REFERENCES approval_requests(request_id),
  attempt             INTEGER NOT NULL DEFAULT 1,
  error               TEXT,
  executed_at         TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_execution_jobs_case ON execution_jobs(case_id);

-- FR-041: 成功・人間引き渡し・重複スキップは同じ冪等性キーで一度きり。
-- 失敗ジョブは再試行できるよう一意制約の対象から外す。
CREATE UNIQUE INDEX IF NOT EXISTS uq_execution_jobs_idempotency
  ON execution_jobs(idempotency_key)
  WHERE status <> 'failed';

CREATE TABLE IF NOT EXISTS audit_events (
  event_id            TEXT PRIMARY KEY,
  case_id             TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  event_type          TEXT NOT NULL,
  actor               TEXT NOT NULL,
  actor_role          TEXT NOT NULL,
  occurred_at         TIMESTAMPTZ NOT NULL,
  input_refs          JSONB NOT NULL DEFAULT '[]'::jsonb,
  output_refs         JSONB NOT NULL DEFAULT '[]'::jsonb,
  decision            TEXT,
  approval_request_id TEXT,
  execution_id        TEXT,
  detail              JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_audit_events_case_time ON audit_events(case_id, occurred_at);

-- FR-022: 同一カテゴリ・同一根本原因の自動差戻し回数。
CREATE TABLE IF NOT EXISTS retry_counters (
  case_id        TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  category       TEXT NOT NULL,
  root_cause     TEXT NOT NULL,
  auto_revisions INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (case_id, category, root_cause)
);

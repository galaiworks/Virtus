/**
 * 品質/承認エージェントの状態機械(FR-020 / FR-021 / FR-022、手順書 C-3)。
 *
 * 各状態には「システムの動作」「介入者」「停止範囲」「再開地点」が対応する。
 * 複数の例外が同時に立つ場合は PRIORITY に従って最も強い状態を採用する。
 */

export const CASE_STATES = [
  'pass',
  'needs_revision',
  'needs_clarification',
  'hold_for_decision',
  'awaiting_approval',
  'blocked_authorization',
  'blocked_security',
  'execution_failed',
  'incident_mode',
  /**
   * FR-022:同一カテゴリ・同一根本原因の自動差戻しが上限に達したときの停止状態。
   * QA の判定結果ではなくワークフロー側のループ遮断であるため、
   * FR-020 が列挙する 9 状態とは別に保持する。
   */
  'human_review_required',
] as const;

export type CaseState = (typeof CASE_STATES)[number];

/** 工程の識別子。再開地点として使う。 */
export type StageId =
  | 'intake'
  | 'supervisor'
  | 'knowledge'
  | 'improvement'
  | 'qa'
  | 'approval'
  | 'execution'
  | 'closed';

/** 介入者の役割(要件定義 §3)。 */
export type ActorRole =
  | 'requester'
  | 'process_owner'
  | 'approver'
  | 'data_owner'
  | 'ai_ops'
  | 'security'
  | 'executive'
  | 'system';

export interface StateDefinition {
  readonly state: CaseState;
  /** システムがその状態で行う動作。 */
  readonly systemAction: string;
  /** 介入する人間の役割。空配列は原則不要(定期監査のみ)。 */
  readonly interveners: readonly ActorRole[];
  /** 停止範囲。 */
  readonly halts: {
    readonly agentPipeline: boolean;
    readonly executionQueue: boolean;
    readonly chatNotifications: boolean;
  };
  /** 是正後に処理を再開する工程。 */
  readonly resumeAt: StageId;
  /** 自動ループで再試行してよい状態か。 */
  readonly autoRetryable: boolean;
  /** 事故モード扱い(P0/P1)。自律再開を禁止する。 */
  readonly incident: boolean;
}

export const STATE_DEFINITIONS: Record<CaseState, StateDefinition> = {
  pass: {
    state: 'pass',
    systemAction: 'Green かつ可逆な操作だけを実行可能にする',
    interveners: [],
    halts: { agentPipeline: false, executionQueue: false, chatNotifications: false },
    resumeAt: 'execution',
    autoRetryable: false,
    incident: false,
  },
  needs_revision: {
    state: 'needs_revision',
    systemAction: '修正要求を作り、業務改善エージェントへ戻す',
    interveners: ['ai_ops'],
    halts: { agentPipeline: false, executionQueue: true, chatNotifications: false },
    resumeAt: 'improvement',
    autoRetryable: true,
    incident: false,
  },
  needs_clarification: {
    state: 'needs_clarification',
    systemAction: '不足している必須項目を依頼者へ照会し、処理を止める',
    interveners: ['requester', 'process_owner'],
    halts: { agentPipeline: true, executionQueue: true, chatNotifications: false },
    resumeAt: 'supervisor',
    autoRetryable: false,
    incident: false,
  },
  hold_for_decision: {
    state: 'hold_for_decision',
    systemAction: '選択肢・根拠・影響を提示し、正解を推測しない',
    interveners: ['process_owner'],
    halts: { agentPipeline: true, executionQueue: true, chatNotifications: false },
    resumeAt: 'knowledge',
    autoRetryable: false,
    incident: false,
  },
  awaiting_approval: {
    state: 'awaiting_approval',
    systemAction: '承認パケットを作り、実行キューを停止する',
    interveners: ['approver'],
    halts: { agentPipeline: true, executionQueue: true, chatNotifications: false },
    resumeAt: 'approval',
    autoRetryable: false,
    incident: false,
  },
  blocked_authorization: {
    state: 'blocked_authorization',
    systemAction: '権限外の資料・ツール利用を停止する',
    interveners: ['data_owner'],
    halts: { agentPipeline: true, executionQueue: true, chatNotifications: false },
    resumeAt: 'knowledge',
    autoRetryable: false,
    incident: false,
  },
  blocked_security: {
    state: 'blocked_security',
    systemAction: '出力・連携を停止し、証跡を保全する',
    interveners: ['security', 'ai_ops'],
    halts: { agentPipeline: true, executionQueue: true, chatNotifications: true },
    resumeAt: 'knowledge',
    autoRetryable: false,
    incident: false,
  },
  execution_failed: {
    state: 'execution_failed',
    systemAction: '再試行可否と外部影響を記録する',
    interveners: ['ai_ops'],
    halts: { agentPipeline: true, executionQueue: true, chatNotifications: false },
    resumeAt: 'execution',
    autoRetryable: false,
    incident: false,
  },
  incident_mode: {
    state: 'incident_mode',
    systemAction: 'キルスイッチを引き、ログを保全し、自律再開しない',
    interveners: ['security', 'executive'],
    halts: { agentPipeline: true, executionQueue: true, chatNotifications: true },
    resumeAt: 'intake',
    autoRetryable: false,
    incident: true,
  },
  human_review_required: {
    state: 'human_review_required',
    systemAction: '同一原因の自動差戻しループを遮断し、人間レビューへ渡す',
    interveners: ['process_owner', 'ai_ops'],
    halts: { agentPipeline: true, executionQueue: true, chatNotifications: false },
    resumeAt: 'improvement',
    autoRetryable: false,
    incident: false,
  },
};

/**
 * FR-021 の優先順:
 * security/incident > authorization > fact conflict > approval > clarification > revision > pass
 *
 * 数値が大きいほど強い。`human_review_required` は差戻しループの遮断であり、
 * revision より強く clarification より弱い位置に置く。
 * `execution_failed` は実行後の状態であり QA 判定とは競合しないため最下位に置く。
 */
export const STATE_PRIORITY: Record<CaseState, number> = {
  incident_mode: 70,
  blocked_security: 60,
  blocked_authorization: 50,
  hold_for_decision: 40,
  awaiting_approval: 30,
  needs_clarification: 20,
  human_review_required: 15,
  needs_revision: 10,
  pass: 0,
  execution_failed: -1,
};

/** 同時に立った候補状態のうち、最も強いものを採用する(FR-021)。 */
export function strongestState(candidates: readonly CaseState[]): CaseState {
  if (candidates.length === 0) return 'pass';
  return candidates.reduce((strongest, candidate) =>
    STATE_PRIORITY[candidate] > STATE_PRIORITY[strongest] ? candidate : strongest,
  );
}

export function stateDefinition(state: CaseState): StateDefinition {
  const def = STATE_DEFINITIONS[state];
  if (!def) throw new Error(`未定義の状態: ${state}`);
  return def;
}

/** その状態で実行キューを進めてよいか。 */
export function allowsExecution(state: CaseState): boolean {
  return !stateDefinition(state).halts.executionQueue;
}

/** 自律再開が禁じられる状態か(FR-024)。 */
export function requiresExplicitHumanRestart(state: CaseState): boolean {
  const def = stateDefinition(state);
  return def.incident || def.state === 'blocked_security';
}

/**
 * リスク区分と操作カタログ(要件定義 §2 / §5.5、手順書 A-2)。
 *
 * Green は可逆な社内操作のみ。Yellow/Red は承認記録なしに実行しない。
 * MVP では「外部メール送信」「CRM 確定更新」「削除・上書き」を
 * 自動実行の対象外とし、承認後も人間実行へ引き渡す。
 */

export type RiskTier = 'green' | 'yellow' | 'red';

export const RISK_ORDER: Record<RiskTier, number> = { green: 0, yellow: 1, red: 2 };

/** MVP が知っている操作の識別子。 */
export type OperationId =
  | 'internal_draft.save'
  | 'task_draft.create'
  | 'approval_request.post'
  | 'external_email.send'
  | 'crm.record.commit'
  | 'storage.delete'
  | 'storage.overwrite'
  | 'contract.sign'
  | 'pricing.commit'
  | 'spend.commit'
  | 'hr.decision';

export interface OperationSpec {
  readonly id: OperationId;
  readonly label: string;
  readonly risk: RiskTier;
  /** 取り消せる操作か(Green の必須条件)。 */
  readonly reversible: boolean;
  /**
   * MVP が自動実行してよいか。
   * false の操作は、承認されても実行アダプタが人間実行へ引き渡す(要件定義 §2)。
   */
  readonly autoExecutableInMvp: boolean;
  /** ロールバック方法の説明。承認パケットの必須項目(FR-023)。 */
  readonly rollback: string;
}

export const OPERATIONS: Record<OperationId, OperationSpec> = {
  'internal_draft.save': {
    id: 'internal_draft.save',
    label: '社内下書きの保存',
    risk: 'green',
    reversible: true,
    autoExecutableInMvp: true,
    rollback: '下書きの版を1つ前に戻す(版数管理)',
  },
  'task_draft.create': {
    id: 'task_draft.create',
    label: 'タスク下書きの作成',
    risk: 'green',
    reversible: true,
    autoExecutableInMvp: true,
    rollback: '作成したタスク下書きを削除する',
  },
  'approval_request.post': {
    id: 'approval_request.post',
    label: '承認依頼の投稿',
    risk: 'green',
    reversible: true,
    autoExecutableInMvp: true,
    rollback: '投稿カードを取り下げ状態へ更新する',
  },
  'external_email.send': {
    id: 'external_email.send',
    label: '顧客向けメールの送信',
    risk: 'yellow',
    reversible: false,
    autoExecutableInMvp: false,
    rollback: '送信は取り消せない。誤送信時は訂正連絡を人間が行う',
  },
  'crm.record.commit': {
    id: 'crm.record.commit',
    label: 'CRM レコードの確定更新',
    risk: 'yellow',
    reversible: false,
    autoExecutableInMvp: false,
    rollback: '更新前の値を人間が復元する(変更前値を承認パケットに保持)',
  },
  'storage.delete': {
    id: 'storage.delete',
    label: '資料の削除',
    risk: 'red',
    reversible: false,
    autoExecutableInMvp: false,
    rollback: 'ゴミ箱からの復元可否は保管先に依存する。人間が判断する',
  },
  'storage.overwrite': {
    id: 'storage.overwrite',
    label: '資料の上書き',
    risk: 'red',
    reversible: false,
    autoExecutableInMvp: false,
    rollback: '版管理がある場合のみ人間が復元する',
  },
  'contract.sign': {
    id: 'contract.sign',
    label: '契約の締結',
    risk: 'red',
    reversible: false,
    autoExecutableInMvp: false,
    rollback: '不可。契約は人間が締結する',
  },
  'pricing.commit': {
    id: 'pricing.commit',
    label: '価格・見積の確定',
    risk: 'red',
    reversible: false,
    autoExecutableInMvp: false,
    rollback: '不可。価格提示は人間が行う',
  },
  'spend.commit': {
    id: 'spend.commit',
    label: '支出・投資の確定',
    risk: 'red',
    reversible: false,
    autoExecutableInMvp: false,
    rollback: '不可。支出は人間が確定する',
  },
  'hr.decision': {
    id: 'hr.decision',
    label: '人事判断の確定',
    risk: 'red',
    reversible: false,
    autoExecutableInMvp: false,
    rollback: '不可。人事判断は人間が行う',
  },
};

export function operationSpec(id: OperationId): OperationSpec {
  const spec = OPERATIONS[id];
  if (!spec) throw new Error(`未登録の操作: ${id}`);
  return spec;
}

export function isKnownOperation(id: string): id is OperationId {
  return Object.prototype.hasOwnProperty.call(OPERATIONS, id);
}

/**
 * Green として自動実行してよい操作か(FR-040)。
 * 可逆かつ Green かつ MVP 自動実行対象、の 3 条件をすべて満たす場合のみ true。
 */
export function isGreenAutoExecutable(id: OperationId): boolean {
  const spec = operationSpec(id);
  return spec.risk === 'green' && spec.reversible && spec.autoExecutableInMvp;
}

/** 複数操作のうち最も強いリスク区分を返す。 */
export function highestRisk(ids: readonly OperationId[]): RiskTier {
  return ids.reduce<RiskTier>((acc, id) => {
    const tier = operationSpec(id).risk;
    return RISK_ORDER[tier] > RISK_ORDER[acc] ? tier : acc;
  }, 'green');
}

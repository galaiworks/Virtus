/**
 * 個人情報・秘密情報の検出(非機能要件「個人情報・機密」、FR-021)。
 *
 * 成果物・カード・ログには「目的に不要な」個人情報を含めない。
 * 案件が `permitted_personal_data` で宣言した値だけを目的上必要とみなし、
 * それ以外の検出は blocked_security へ倒す。
 */

export type PiiKind =
  | 'email'
  | 'phone'
  | 'my_number'
  | 'credit_card'
  | 'bank_account'
  | 'date_of_birth'
  | 'postal_address'
  | 'credential';

export interface PiiFinding {
  kind: PiiKind;
  value: string;
  /** 案件で目的上必要と宣言されていれば false。 */
  unnecessary: boolean;
}

const PATTERNS: readonly { kind: PiiKind; re: RegExp }[] = [
  { kind: 'email', re: /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g },
  { kind: 'phone', re: /(?:\+81[-\s]?|0)\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4}/g },
  { kind: 'my_number', re: /(?<!\d)\d{4}[-\s]?\d{4}[-\s]?\d{4}(?!\d)/g },
  { kind: 'credit_card', re: /(?<!\d)(?:\d{4}[-\s]?){3}\d{4}(?!\d)/g },
  { kind: 'bank_account', re: /(?:口座番号|普通預金|当座)\s*[:：]?\s*\d{6,8}/g },
  { kind: 'date_of_birth', re: /(?:生年月日|誕生日)\s*[:：]?\s*\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日/g },
  { kind: 'postal_address', re: /〒\s?\d{3}-\d{4}/g },
  {
    kind: 'credential',
    re: /(?:sk-[A-Za-z0-9]{16,}|xox[baprs]-[A-Za-z0-9-]{10,}|(?:password|passwd|パスワード|secret|token)\s*[:：=]\s*\S{6,})/gi,
  },
];

/**
 * 検出順序の都合で、クレジットカード番号はマイナンバーの形にも一致する。
 * 桁構成が同じであるため、より強い区分(credit_card)を優先して重複を落とす。
 */
const KIND_PRIORITY: Record<PiiKind, number> = {
  credential: 100,
  credit_card: 90,
  my_number: 80,
  bank_account: 70,
  date_of_birth: 60,
  postal_address: 50,
  phone: 40,
  email: 30,
};

export function scanForPii(text: string, permitted: readonly string[] = []): PiiFinding[] {
  const permittedSet = new Set(permitted.map((v) => v.trim().toLowerCase()));
  const byValue = new Map<string, PiiFinding>();

  for (const { kind, re } of PATTERNS) {
    for (const match of text.matchAll(new RegExp(re.source, re.flags))) {
      const value = match[0].trim();
      const existing = byValue.get(value);
      if (existing && KIND_PRIORITY[existing.kind] >= KIND_PRIORITY[kind]) continue;
      byValue.set(value, {
        kind,
        value,
        unnecessary: !permittedSet.has(value.toLowerCase()),
      });
    }
  }

  return [...byValue.values()];
}

/** 目的に不要な個人情報だけを返す。 */
export function unnecessaryPii(text: string, permitted: readonly string[] = []): PiiFinding[] {
  return scanForPii(text, permitted).filter((f) => f.unnecessary);
}

/** 認証情報らしき文字列が含まれるか。含まれる場合は常に P0/P1 扱い。 */
export function containsCredential(text: string): boolean {
  return scanForPii(text).some((f) => f.kind === 'credential');
}

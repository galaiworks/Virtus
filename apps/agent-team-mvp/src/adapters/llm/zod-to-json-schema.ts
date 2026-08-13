/**
 * Zod スキーマから JSON Schema を作る最小変換器。
 *
 * Structured Outputs のツール定義に渡すために使う。
 * MVP のプロンプト契約で使う型(object / string / number / boolean / array /
 * enum / nullable / optional / default / literal)だけを扱い、
 * 未対応の型に出会ったら黙って通さずに例外を投げる。
 */

import { z } from 'zod';

export type JsonSchema = Record<string, unknown>;

export function zodToJsonSchema(schema: z.ZodTypeAny): JsonSchema {
  // Zod v3 の内部表現を読む。対応する型は下の switch に限定する。
  const def = schema._def as unknown as Record<string, any>;

  switch (def.typeName) {
    case z.ZodFirstPartyTypeKind.ZodString:
      return { type: 'string' };
    case z.ZodFirstPartyTypeKind.ZodNumber:
      return { type: 'number' };
    case z.ZodFirstPartyTypeKind.ZodBoolean:
      return { type: 'boolean' };
    case z.ZodFirstPartyTypeKind.ZodLiteral:
      return { const: def.value as unknown };
    case z.ZodFirstPartyTypeKind.ZodEnum:
      return { type: 'string', enum: [...(def.values as string[])] };
    case z.ZodFirstPartyTypeKind.ZodArray:
      return {
        type: 'array',
        items: zodToJsonSchema(def.type as z.ZodTypeAny),
      };
    case z.ZodFirstPartyTypeKind.ZodObject: {
      const shape = (schema as z.ZodObject<z.ZodRawShape>).shape;
      const properties: Record<string, JsonSchema> = {};
      const required: string[] = [];
      for (const [key, value] of Object.entries(shape)) {
        properties[key] = zodToJsonSchema(value);
        if (!isOptionalLike(value)) required.push(key);
      }
      return {
        type: 'object',
        properties,
        required,
        additionalProperties: false,
      };
    }
    case z.ZodFirstPartyTypeKind.ZodNullable: {
      const inner = zodToJsonSchema(def.innerType as z.ZodTypeAny);
      return { anyOf: [inner, { type: 'null' }] };
    }
    case z.ZodFirstPartyTypeKind.ZodOptional:
    case z.ZodFirstPartyTypeKind.ZodDefault:
      return zodToJsonSchema(def.innerType as z.ZodTypeAny);
    case z.ZodFirstPartyTypeKind.ZodUnion: {
      const options = def.options as z.ZodTypeAny[];
      return { anyOf: options.map((option) => zodToJsonSchema(option)) };
    }
    default:
      throw new Error(`JSON Schema へ変換できない型です: ${def.typeName}`);
  }
}

function isOptionalLike(schema: z.ZodTypeAny): boolean {
  const typeName = (schema._def as unknown as Record<string, unknown>).typeName;
  return (
    typeName === z.ZodFirstPartyTypeKind.ZodOptional ||
    typeName === z.ZodFirstPartyTypeKind.ZodDefault
  );
}

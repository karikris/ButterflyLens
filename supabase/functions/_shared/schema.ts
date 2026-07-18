export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | {
  [key: string]: JsonValue;
};
export type JsonObject = { [key: string]: JsonValue };

export type JsonSchema = {
  readonly type?: string | readonly string[];
  readonly const?: JsonValue;
  readonly enum?: readonly JsonValue[];
  readonly properties?: Readonly<Record<string, JsonSchema>>;
  readonly required?: readonly string[];
  readonly additionalProperties?: boolean;
  readonly items?: JsonSchema;
  readonly minItems?: number;
  readonly maxItems?: number;
  readonly uniqueItems?: boolean;
  readonly minLength?: number;
  readonly maxLength?: number;
  readonly pattern?: string;
  readonly minimum?: number;
  readonly maximum?: number;
};

export class SchemaValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SchemaValidationError";
  }
}

export function assertJsonSchema(
  schema: JsonSchema,
  value: unknown,
  path = "value",
): asserts value is JsonValue {
  if ("const" in schema && !jsonEqual(value, schema.const)) {
    throw new SchemaValidationError(
      `${path} does not match the required constant`,
    );
  }
  if (
    schema.enum && !schema.enum.some((candidate) => jsonEqual(value, candidate))
  ) {
    throw new SchemaValidationError(`${path} is not an allowed value`);
  }
  const allowedTypes = Array.isArray(schema.type)
    ? schema.type
    : schema.type
    ? [schema.type]
    : [];
  if (
    allowedTypes.length > 0 &&
    !allowedTypes.some((type) => hasJsonType(value, type))
  ) {
    throw new SchemaValidationError(`${path} has the wrong JSON type`);
  }

  if (typeof value === "string") {
    if (schema.minLength !== undefined && value.length < schema.minLength) {
      throw new SchemaValidationError(
        `${path} is shorter than ${schema.minLength}`,
      );
    }
    if (schema.maxLength !== undefined && value.length > schema.maxLength) {
      throw new SchemaValidationError(
        `${path} is longer than ${schema.maxLength}`,
      );
    }
    if (schema.pattern && !new RegExp(schema.pattern, "u").test(value)) {
      throw new SchemaValidationError(`${path} has an invalid format`);
    }
  }

  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new SchemaValidationError(`${path} must be finite`);
    }
    if (schema.minimum !== undefined && value < schema.minimum) {
      throw new SchemaValidationError(`${path} is below ${schema.minimum}`);
    }
    if (schema.maximum !== undefined && value > schema.maximum) {
      throw new SchemaValidationError(`${path} is above ${schema.maximum}`);
    }
  }

  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) {
      throw new SchemaValidationError(`${path} has too few items`);
    }
    if (schema.maxItems !== undefined && value.length > schema.maxItems) {
      throw new SchemaValidationError(`${path} has too many items`);
    }
    if (schema.uniqueItems) {
      const canonical = value.map((item) => canonicalJson(item as JsonValue));
      if (new Set(canonical).size !== canonical.length) {
        throw new SchemaValidationError(`${path} has duplicate items`);
      }
    }
    if (schema.items) {
      value.forEach((item, index) =>
        assertJsonSchema(schema.items!, item, `${path}[${index}]`)
      );
    }
  }

  if (isJsonObject(value)) {
    const properties = schema.properties ?? {};
    for (const field of schema.required ?? []) {
      if (!(field in value)) {
        throw new SchemaValidationError(`${path}.${field} is required`);
      }
    }
    if (schema.additionalProperties === false) {
      for (const field of Object.keys(value)) {
        if (!(field in properties)) {
          throw new SchemaValidationError(`${path}.${field} is not allowed`);
        }
      }
    }
    for (const [field, childSchema] of Object.entries(properties)) {
      if (field in value) {
        assertJsonSchema(childSchema, value[field], `${path}.${field}`);
      }
    }
  }
}

function hasJsonType(value: unknown, type: string): boolean {
  if (type === "null") return value === null;
  if (type === "array") return Array.isArray(value);
  if (type === "object") return isJsonObject(value);
  if (type === "integer") {
    return typeof value === "number" && Number.isInteger(value);
  }
  if (type === "number") {
    return typeof value === "number" && Number.isFinite(value);
  }
  return typeof value === type;
}

export function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function jsonEqual(left: unknown, right: unknown): boolean {
  try {
    return canonicalJson(left as JsonValue) ===
      canonicalJson(right as JsonValue);
  } catch {
    return false;
  }
}

export function canonicalJson(value: JsonValue): string {
  if (value === null || typeof value !== "object") {
    const encoded = JSON.stringify(value);
    if (encoded === undefined) {
      throw new SchemaValidationError("value is not JSON serializable");
    }
    return encoded;
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  }
  const fields = Object.keys(value).sort();
  return `{${
    fields
      .map((field) => `${JSON.stringify(field)}:${canonicalJson(value[field])}`)
      .join(",")
  }}`;
}

export async function sha256Fingerprint(value: JsonValue): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalJson(value));
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return `sha256:${
    Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join("")
  }`;
}

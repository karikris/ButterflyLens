type JsonObject = Record<string, unknown>

interface ValidationContext {
  readonly schemas: Readonly<Record<string, JsonObject>>
  readonly root: JsonObject
  readonly errors: string[]
}

interface ResolvedSchema {
  readonly schema: JsonObject
  readonly root: JsonObject
}

export function validateSchema(
  schemas: Readonly<Record<string, JsonObject>>,
  schemaId: string,
  value: unknown,
): readonly string[] {
  const root = schemas[schemaId]
  if (root === undefined) {
    return [`$: unknown schema ${schemaId}`]
  }
  const errors: string[] = []
  validateNode(root, value, '$', { schemas, root, errors })
  return errors
}

function validateNode(
  schema: JsonObject,
  value: unknown,
  path: string,
  context: ValidationContext,
): void {
  const reference = schema.$ref
  if (typeof reference === 'string') {
    const resolved = resolveReference(reference, context)
    if (resolved === null) {
      context.errors.push(`${path}: unresolved reference ${reference}`)
      return
    }
    validateNode(resolved.schema, value, path, {
      ...context,
      root: resolved.root,
    })
  }

  if (Array.isArray(schema.allOf)) {
    for (const child of schema.allOf) {
      if (isObject(child)) {
        validateNode(child, value, path, context)
      }
    }
  }

  if (Array.isArray(schema.anyOf)) {
    const matched = schema.anyOf.some((child) =>
      isObject(child) && branchMatches(child, value, path, context),
    )
    if (!matched) {
      context.errors.push(`${path}: no anyOf branch matched`)
    }
  }

  if (Array.isArray(schema.oneOf)) {
    const matches = schema.oneOf.filter((child) =>
      isObject(child) && branchMatches(child, value, path, context),
    ).length
    if (matches !== 1) {
      context.errors.push(`${path}: expected one oneOf branch, received ${matches}`)
    }
  }

  if (isObject(schema.if)) {
    const conditionalMatches = branchMatches(schema.if, value, path, context)
    const selected = conditionalMatches ? schema.then : schema.else
    if (isObject(selected)) {
      validateNode(selected, value, path, context)
    }
  }

  if ('const' in schema && !deepEqual(schema.const, value)) {
    context.errors.push(`${path}: value does not match const`)
  }

  if (Array.isArray(schema.enum) && !schema.enum.some((item) => deepEqual(item, value))) {
    context.errors.push(`${path}: value is outside enum`)
  }

  if (typeof schema.type === 'string' && !matchesType(schema.type, value)) {
    context.errors.push(`${path}: expected ${schema.type}`)
    return
  }

  if (isObject(value)) {
    validateObject(schema, value, path, context)
  } else if (Array.isArray(value)) {
    validateArray(schema, value, path, context)
  } else if (typeof value === 'string') {
    validateString(schema, value, path, context)
  } else if (typeof value === 'number') {
    validateNumber(schema, value, path, context)
  }
}

function validateObject(
  schema: JsonObject,
  value: JsonObject,
  path: string,
  context: ValidationContext,
): void {
  if (Array.isArray(schema.required)) {
    for (const key of schema.required) {
      if (typeof key === 'string' && !(key in value)) {
        context.errors.push(`${path}: missing required property ${key}`)
      }
    }
  }
  const properties = isObject(schema.properties) ? schema.properties : {}
  for (const [key, childValue] of Object.entries(value)) {
    const childSchema = properties[key]
    if (isObject(childSchema)) {
      validateNode(childSchema, childValue, `${path}.${key}`, context)
    } else if (schema.additionalProperties === false) {
      context.errors.push(`${path}: additional property ${key}`)
    }
  }
}

function validateArray(
  schema: JsonObject,
  value: readonly unknown[],
  path: string,
  context: ValidationContext,
): void {
  if (typeof schema.minItems === 'number' && value.length < schema.minItems) {
    context.errors.push(`${path}: fewer than ${schema.minItems} items`)
  }
  if (typeof schema.maxItems === 'number' && value.length > schema.maxItems) {
    context.errors.push(`${path}: more than ${schema.maxItems} items`)
  }
  if (schema.uniqueItems === true) {
    const identities = value.map(canonicalIdentity)
    if (new Set(identities).size !== identities.length) {
      context.errors.push(`${path}: duplicate array items`)
    }
  }
  if (isObject(schema.items)) {
    value.forEach((item, index) => {
      validateNode(schema.items as JsonObject, item, `${path}[${index}]`, context)
    })
  }
}

function validateString(
  schema: JsonObject,
  value: string,
  path: string,
  context: ValidationContext,
): void {
  if (typeof schema.minLength === 'number' && [...value].length < schema.minLength) {
    context.errors.push(`${path}: shorter than ${schema.minLength}`)
  }
  if (typeof schema.maxLength === 'number' && [...value].length > schema.maxLength) {
    context.errors.push(`${path}: longer than ${schema.maxLength}`)
  }
  if (typeof schema.pattern === 'string' && !(new RegExp(schema.pattern, 'u')).test(value)) {
    context.errors.push(`${path}: pattern mismatch`)
  }
  if (schema.format === 'date' && !isDate(value)) {
    context.errors.push(`${path}: invalid date`)
  }
  if (schema.format === 'date-time' && !isDateTime(value)) {
    context.errors.push(`${path}: invalid date-time`)
  }
}

function validateNumber(
  schema: JsonObject,
  value: number,
  path: string,
  context: ValidationContext,
): void {
  if (typeof schema.minimum === 'number' && value < schema.minimum) {
    context.errors.push(`${path}: below minimum`)
  }
  if (typeof schema.maximum === 'number' && value > schema.maximum) {
    context.errors.push(`${path}: above maximum`)
  }
  if (typeof schema.exclusiveMinimum === 'number' && value <= schema.exclusiveMinimum) {
    context.errors.push(`${path}: below exclusive minimum`)
  }
  if (typeof schema.exclusiveMaximum === 'number' && value >= schema.exclusiveMaximum) {
    context.errors.push(`${path}: above exclusive maximum`)
  }
}

function branchMatches(
  schema: JsonObject,
  value: unknown,
  path: string,
  context: ValidationContext,
): boolean {
  const errors: string[] = []
  validateNode(schema, value, path, { ...context, errors })
  return errors.length === 0
}

function resolveReference(
  reference: string,
  context: ValidationContext,
): ResolvedSchema | null {
  const [identifier, fragment = ''] = reference.split('#', 2)
  const root = identifier === '' ? context.root : context.schemas[identifier]
  if (root === undefined) {
    return null
  }
  if (fragment === '') {
    return { schema: root, root }
  }
  if (!fragment.startsWith('/')) {
    return null
  }
  let current: unknown = root
  for (const rawPart of fragment.slice(1).split('/')) {
    const part = decodeURIComponent(rawPart.replaceAll('~1', '/').replaceAll('~0', '~'))
    if (!isObject(current) || !(part in current)) {
      return null
    }
    current = current[part]
  }
  return isObject(current) ? { schema: current, root } : null
}

function matchesType(type: string, value: unknown): boolean {
  switch (type) {
    case 'object': return isObject(value)
    case 'array': return Array.isArray(value)
    case 'string': return typeof value === 'string'
    case 'integer': return typeof value === 'number' && Number.isInteger(value)
    case 'number': return typeof value === 'number' && Number.isFinite(value)
    case 'boolean': return typeof value === 'boolean'
    case 'null': return value === null
    default: return false
  }
}

function isObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/u.test(value) &&
    !Number.isNaN(Date.parse(`${value}T00:00:00Z`))
}

function isDateTime(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/u.test(value) &&
    !Number.isNaN(Date.parse(value))
}

function deepEqual(left: unknown, right: unknown): boolean {
  return canonicalIdentity(left) === canonicalIdentity(right)
}

function canonicalIdentity(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(canonicalIdentity).join(',')}]`
  }
  if (isObject(value)) {
    return `{${Object.keys(value).sort().map((key) =>
      `${JSON.stringify(key)}:${canonicalIdentity(value[key])}`
    ).join(',')}}`
  }
  return JSON.stringify(value) ?? 'undefined'
}

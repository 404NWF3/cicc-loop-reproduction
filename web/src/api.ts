export class ApiError extends Error {
  constructor(
    message: string,
    public code = 'request_failed',
    public requestId?: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      ...init,
      headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('暂时无法连接后端，请确认 API 服务已启动。', 'connection_failed');
  }
  let body;
  try {
    body = await response.json();
  } catch {
    throw new ApiError('服务返回了无法识别的响应，请检查后端连接。');
  }
  if (!response.ok)
    throw new ApiError(body.message || '请求失败，请稍后重试。', body.code, body.request_id);
  return body as T;
}

export function post<T>(
  path: string,
  body?: unknown,
  headers?: Record<string, string>,
): Promise<T> {
  return api<T>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
    headers,
  });
}

export const messageOf = (error: unknown) =>
  error instanceof Error ? error.message : '发生了未预期的错误。';

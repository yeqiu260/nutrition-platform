/**
 * API 集成工具
 * 处理本地化响应和错误处理
 */

export interface ApiResponse<T = any> {
  data?: T;
  message?: string;
  detail?: string;
  error?: string;
  status: number;
  locale?: string;
}

export interface ApiError {
  message: string;
  status: number;
  locale?: string;
  originalError?: any;
}

/**
 * 获取当前语言
 */
export function getCurrentLocale(): string {
  if (typeof window === 'undefined') {
    return 'zh-TW';
  }
  return localStorage.getItem('NEXT_LOCALE') || 'zh-TW';
}

/**
 * 获取 API 请求头
 */
export function getApiHeaders(additionalHeaders: Record<string, string> = {}): Record<string, string> {
  const locale = getCurrentLocale();
  return {
    'Content-Type': 'application/json',
    'Accept-Language': locale,
    ...additionalHeaders,
  };
}

/**
 * 处理 API 响应
 */
export async function handleApiResponse<T = any>(response: Response): Promise<ApiResponse<T>> {
  const locale = getCurrentLocale();
  const status = response.status;
  
  try {
    const data = await response.json();
    
    return {
      data: data.data || data,
      message: data.message || data.detail,
      status,
      locale,
    };
  } catch (error) {
    return {
      message: 'Failed to parse response',
      status,
      locale,
      error: String(error),
    };
  }
}

/**
 * 处理 API 错误
 */
export function handleApiError(error: any): ApiError {
  const locale = getCurrentLocale();
  
  if (error instanceof Response) {
    return {
      message: error.statusText || 'API Error',
      status: error.status,
      locale,
      originalError: error,
    };
  }
  
  if (error instanceof Error) {
    return {
      message: error.message,
      status: 500,
      locale,
      originalError: error,
    };
  }
  
  return {
    message: String(error),
    status: 500,
    locale,
    originalError: error,
  };
}

/**
 * 发送 API 请求
 */
export async function apiRequest<T = any>(
  url: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: getApiHeaders(options.headers as Record<string, string>),
    });
    
    const result = await handleApiResponse<T>(response);
    
    if (!response.ok) {
      throw new Error(result.message || `HTTP ${response.status}`);
    }
    
    return result;
  } catch (error) {
    const apiError = handleApiError(error);
    throw apiError;
  }
}

/**
 * GET 请求
 */
export async function apiGet<T = any>(url: string): Promise<ApiResponse<T>> {
  return apiRequest<T>(url, { method: 'GET' });
}

/**
 * POST 请求
 */
export async function apiPost<T = any>(
  url: string,
  data: any = {}
): Promise<ApiResponse<T>> {
  return apiRequest<T>(url, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * PUT 请求
 */
export async function apiPut<T = any>(
  url: string,
  data: any = {}
): Promise<ApiResponse<T>> {
  return apiRequest<T>(url, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * DELETE 请求
 */
export async function apiDelete<T = any>(url: string): Promise<ApiResponse<T>> {
  return apiRequest<T>(url, { method: 'DELETE' });
}

/**
 * 获取本地化错误消息
 */
export function getLocalizedErrorMessage(error: ApiError | Error): string {
  if (error instanceof Error) {
    return error.message;
  }
  
  if ('message' in error) {
    return error.message;
  }
  
  return 'An error occurred';
}

/**
 * 检查响应是否成功
 */
export function isApiSuccess(response: ApiResponse): boolean {
  return response.status >= 200 && response.status < 300;
}

/**
 * 检查响应是否是错误
 */
export function isApiError(response: ApiResponse): boolean {
  return response.status >= 400;
}

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";

/** Minimal shapes; refine later if needed */
export interface UploadResponse {
  file_id: string;
  filename?: string;
  size?: number;
  content_type?: string;
  dimensions?: { width: number; height: number };
  faces_detected?: number; // 0 or 1 in current backend
  status?: 'ready' | 'no_faces' | 'error';
}
export interface Suggestion { [k: string]: any }
export interface CropSuggestionsResponse {
  crop_suggestions: Suggestion[];
  face_detection: { center_y: number; [k: string]: any };
  [k: string]: any;
}
export interface PreviewRequest { [k: string]: any }
export interface ExportRequest {
  preset?: string;
  format?: "png" | "jpg" | "jpeg" | "webp";
  quality?: number;
  [k: string]: any;
}
export interface ValidateRequest { [k: string]: any }
export interface ProcessStatus { [k: string]: any }

/** Relative base so Next.js rewrites proxy in all envs */
const client = axios.create({ baseURL: "" });

/** ---- Interceptors for DEBUG logging ---- */
client.interceptors.request.use((config: AxiosRequestConfig) => {
  try {
    const url = (config.baseURL || "") + (config.url || "");
    // eslint-disable-next-line no-console
    console.log(`[api] → ${config.method?.toUpperCase()} ${url}`);
  } catch {}
  return config;
});

client.interceptors.response.use(
  (resp: AxiosResponse) => {
    try {
      const url = (resp.config.baseURL || "") + (resp.config.url || "");
      // eslint-disable-next-line no-console
      console.log(`[api] ← ${resp.status} ${resp.config.method?.toUpperCase()} ${url}`);
    } catch {}
    return resp;
  },
  (error) => {
    try {
      const cfg = error?.config || {};
      const url = (cfg.baseURL || "") + (cfg.url || "");
      // eslint-disable-next-line no-console
      console.error(`[api] ✖ ${cfg.method?.toUpperCase()} ${url}:`, error?.response?.status, error?.message);
    } catch {}
    return Promise.reject(error);
  }
);

/** ---- Helpers mapped to backend routes ---- */

// Upload
async function uploadSingle(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await client.post("/api/v1/upload/single", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

// Suggestions (backend returns an object with crop_suggestions, image_dimensions, face_detection)
async function getCropSuggestions(uploadId: string): Promise<CropSuggestionsResponse> {
  const { data } = await client.get(
    `/api/v1/suggestions/${encodeURIComponent(uploadId)}/suggestions`
  );
  return data;
}

// Process
async function preview(uploadId: string, body: PreviewRequest): Promise<any> {
  const { data } = await client.post(
    `/api/v1/process/${encodeURIComponent(uploadId)}/preview`,
    body
  );
  return data;
}

async function exportResult(uploadId: string, body: ExportRequest): Promise<any> {
  const { data } = await client.post(
    `/api/v1/process/${encodeURIComponent(uploadId)}/export`,
    body
  );
  return data;
}

/** Export an image (binary): return Blob and auto-download in browser */
function triggerDownload(blob: Blob, fallbackName = "quickcrop-export.png") {
  if (typeof window === "undefined") return; // SSR: no-op
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fallbackName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

async function exportImage(uploadId: string, body: ExportRequest): Promise<Blob> {
  const resp = await client.post(
    `/api/v1/process/${encodeURIComponent(uploadId)}/export`,
    body,
    { responseType: "blob" }
  );
  const blob = resp.data as Blob;

  // filename from headers or fallback
  const cd = (resp.headers?.["content-disposition"] || "") as string;
  let filename = "quickcrop-export.png";
  const m = cd.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i);
  if (m && m[1]) {
    try { filename = decodeURIComponent(m[1]); } catch { /* ignore */ }
  } else {
    const ext = body?.format ? (body.format === "jpg" ? "jpg" : body.format) : "png";
    const preset = body?.preset ? `-${body.preset}` : "";
    filename = `quickcrop${preset}-${Date.now()}.${ext}`;
  }
  // Do not auto-download here; caller handles naming and download trigger.
  return blob;
}

async function getStatus(uploadId: string): Promise<ProcessStatus> {
  const { data } = await client.get(
    `/api/v1/process/${encodeURIComponent(uploadId)}/status`
  );
  return data;
}

async function deleteUpload(uploadId: string): Promise<void> {
  await client.delete(`/api/v1/process/${encodeURIComponent(uploadId)}`);
}

async function validate(body: ValidateRequest): Promise<any> {
  const { data } = await client.post(`/api/v1/process/validate`, body);
  return data;
}

// Health
async function healthStatus(): Promise<any> {
  const { data } = await client.get(`/api/v1/health/status`);
  return data;
}
async function healthReady(): Promise<any> {
  const { data } = await client.get(`/api/v1/health/ready`);
  return data;
}

/** ---- Expose as a typed client with helpers ---- */
export const apiClient = client as AxiosInstance & {
  uploadSingle: (file: File) => Promise<UploadResponse>;
  getCropSuggestions: (uploadId: string) => Promise<CropSuggestionsResponse>;
  preview: (uploadId: string, body: PreviewRequest) => Promise<any>;
  exportResult: (uploadId: string, body: ExportRequest) => Promise<any>;
  exportImage: (uploadId: string, body: ExportRequest) => Promise<Blob>;
  getStatus: (uploadId: string) => Promise<ProcessStatus>;
  deleteUpload: (uploadId: string) => Promise<void>;
  validate: (body: ValidateRequest) => Promise<any>;
  healthStatus: () => Promise<any>;
  healthReady: () => Promise<any>;
};

// attach methods
(apiClient as any).uploadSingle = uploadSingle;
(apiClient as any).getCropSuggestions = getCropSuggestions;
(apiClient as any).preview = preview;
(apiClient as any).exportResult = exportResult;
(apiClient as any).exportImage = exportImage;
(apiClient as any).getStatus = getStatus;
(apiClient as any).deleteUpload = deleteUpload;
(apiClient as any).validate = validate;
(apiClient as any).healthStatus = healthStatus;
(apiClient as any).healthReady = healthReady;

export default apiClient;

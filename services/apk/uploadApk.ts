import {
  InvalidUploadApkResponseError,
  mapUploadApkResponse,
} from "../../lib/scan/mapUploadApkResponse";
import type { ScanAssessment } from "../../types/scan-assessment";

export type ApkInstallSource =
  | "google_play_store"
  | "website_download"
  | "apk_sideload"
  | "unknown_source";

export type ApkUploadAsset = {
  uri: string;
  name: string;
  mimeType?: string | null;
  /** Present for an Expo DocumentPicker asset selected on web. */
  file?: Blob | null;
};

export type ApkUploadPhase = "uploading" | "analysing";

export type ApkUploadProgress = {
  loadedBytes: number;
  totalBytes: number | null;
  fraction: number | null;
};

export type UploadApkCallbacks = {
  onPhaseChange?: (phase: ApkUploadPhase) => void;
  onUploadProgress?: (progress: ApkUploadProgress) => void;
};

export type UploadApkRequest = {
  asset: ApkUploadAsset;
  installSource: ApkInstallSource;
};

export type ApkUploadErrorKind =
  | "invalid-request"
  | "network"
  | "timeout"
  | "aborted"
  | "http"
  | "invalid-response";

export class ApkUploadError extends Error {
  readonly kind: ApkUploadErrorKind;
  readonly status: number | null;
  readonly retryable: boolean;

  constructor(
    kind: ApkUploadErrorKind,
    message: string,
    options: { status?: number; retryable?: boolean } = {},
  ) {
    super(message);
    this.name = "ApkUploadError";
    this.kind = kind;
    this.status = options.status ?? null;
    this.retryable = options.retryable ?? false;
  }
}

type XhrFactory = () => XMLHttpRequest;

export type CreateUploadApkOptions = {
  apiBaseUrl?: string;
  xhrFactory?: XhrFactory;
  timeoutMs?: number;
};

function parseJson(text: string): unknown {
  if (text.trim() === "") return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

function responseBody(xhr: XMLHttpRequest): unknown {
  if (
    xhr.response !== null &&
    typeof xhr.response === "object" &&
    !(xhr.response instanceof ArrayBuffer) &&
    !(typeof Blob !== "undefined" && xhr.response instanceof Blob)
  ) {
    return xhr.response as unknown;
  }
  return parseJson(typeof xhr.responseText === "string" ? xhr.responseText : "");
}

function errorDetail(body: unknown, status: number): string {
  if (
    body !== null &&
    typeof body === "object" &&
    !Array.isArray(body) &&
    "detail" in body &&
    typeof body.detail === "string" &&
    body.detail.trim() !== ""
  ) {
    return body.detail;
  }
  return `APK analysis failed with HTTP ${status}.`;
}

function validateRequest(request: UploadApkRequest): void {
  if (
    !request ||
    !request.asset ||
    typeof request.asset.uri !== "string" ||
    request.asset.uri.trim() === "" ||
    typeof request.asset.name !== "string" ||
    request.asset.name.trim() === ""
  ) {
    throw new ApkUploadError(
      "invalid-request",
      "Select a valid APK file before starting analysis.",
    );
  }
}

function createMultipartBody(request: UploadApkRequest): FormData {
  const body = new FormData();
  const { asset } = request;

  if (asset.file) {
    body.append("file", asset.file, asset.name);
  } else {
    // React Native's FormData accepts a URI-backed file descriptor. Its public
    // TypeScript declaration only models browser Blob values, hence this narrow
    // boundary cast.
    body.append(
      "file",
      {
        uri: asset.uri,
        name: asset.name,
        type: asset.mimeType || "application/vnd.android.package-archive",
      } as unknown as Blob,
    );
  }
  body.append("install_source", request.installSource);
  return body;
}

export function createUploadApk({
  apiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://10.0.2.2:8000",
  xhrFactory = () => new XMLHttpRequest(),
  timeoutMs = 120_000,
}: CreateUploadApkOptions = {}) {
  const endpoint = `${apiBaseUrl.replace(/\/+$/, "")}/upload-apk`;

  return function uploadApkRequest(
    request: UploadApkRequest,
    callbacks: UploadApkCallbacks = {},
  ): Promise<ScanAssessment> {
    try {
      validateRequest(request);
    } catch (error) {
      return Promise.reject(error);
    }

    return new Promise<ScanAssessment>((resolve, reject) => {
      const xhr = xhrFactory();
      let settled = false;
      let analysingStarted = false;

      const rejectOnce = (error: ApkUploadError) => {
        if (settled) return;
        settled = true;
        reject(error);
      };

      const startAnalysing = () => {
        if (analysingStarted || settled) return;
        analysingStarted = true;
        callbacks.onPhaseChange?.("analysing");
      };

      callbacks.onPhaseChange?.("uploading");
      xhr.open("POST", endpoint, true);
      xhr.timeout = timeoutMs;

      // Deliberately do not set Content-Type: XHR must generate the multipart
      // boundary for both React Native and web implementations.
      xhr.upload.onprogress = (event) => {
        const totalBytes = event.lengthComputable ? event.total : null;
        callbacks.onUploadProgress?.({
          loadedBytes: event.loaded,
          totalBytes,
          fraction:
            totalBytes !== null && totalBytes > 0
              ? Math.min(1, event.loaded / totalBytes)
              : null,
        });
      };
      xhr.upload.onload = startAnalysing;

      xhr.onload = () => {
        startAnalysing();
        const body = responseBody(xhr);

        if (xhr.status < 200 || xhr.status >= 300) {
          rejectOnce(
            new ApkUploadError("http", errorDetail(body, xhr.status), {
              status: xhr.status,
              retryable: xhr.status >= 500,
            }),
          );
          return;
        }

        try {
          const assessment = mapUploadApkResponse(body);
          if (settled) return;
          settled = true;
          resolve(assessment);
        } catch (error) {
          const detail =
            error instanceof InvalidUploadApkResponseError
              ? error.message
              : "The backend returned an invalid APK analysis response.";
          rejectOnce(
            new ApkUploadError("invalid-response", detail, {
              status: xhr.status,
            }),
          );
        }
      };

      xhr.onerror = () => {
        rejectOnce(
          new ApkUploadError(
            "network",
            "Could not reach the APK analysis server. Check the backend address and connection.",
            { retryable: true },
          ),
        );
      };

      xhr.ontimeout = () => {
        rejectOnce(
          new ApkUploadError(
            "timeout",
            "APK analysis timed out. Check the connection and try again.",
            { retryable: true },
          ),
        );
      };

      xhr.onabort = () => {
        rejectOnce(new ApkUploadError("aborted", "APK analysis was cancelled."));
      };

      try {
        xhr.send(createMultipartBody(request));
      } catch {
        rejectOnce(
          new ApkUploadError(
            "network",
            "The APK upload could not be started. Check the selected file and connection.",
            { retryable: true },
          ),
        );
      }
    });
  };
}

export const uploadApk = createUploadApk();

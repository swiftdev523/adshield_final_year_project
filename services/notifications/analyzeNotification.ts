import type {
  NotificationAnalysisResult,
  NotificationPrediction,
} from "../../types/notifications";

type FetchLike = typeof fetch;

export type NotificationAnalysisErrorKind =
  | "invalid-request"
  | "network"
  | "http"
  | "invalid-response";

export class NotificationAnalysisError extends Error {
  readonly kind: NotificationAnalysisErrorKind;
  readonly status: number | null;

  constructor(
    kind: NotificationAnalysisErrorKind,
    message: string,
    options: { status?: number } = {},
  ) {
    super(message);
    this.name = "NotificationAnalysisError";
    this.kind = kind;
    this.status = options.status ?? null;
  }
}

export type CreateAnalyzeNotificationOptions = {
  fetchImpl?: FetchLike;
  apiBaseUrl?: string;
};

function isPrediction(value: unknown): value is NotificationPrediction {
  return value === "Spam" || value === "Ham";
}

function mapResponse(body: unknown): NotificationAnalysisResult {
  if (
    body === null ||
    typeof body !== "object" ||
    Array.isArray(body) ||
    !("prediction" in body) ||
    !isPrediction(body.prediction) ||
    !("confidence" in body) ||
    typeof body.confidence !== "number" ||
    !Number.isFinite(body.confidence) ||
    body.confidence < 0 ||
    body.confidence > 100
  ) {
    throw new NotificationAnalysisError(
      "invalid-response",
      "The backend returned an invalid notification analysis response.",
    );
  }

  return {
    prediction: body.prediction,
    modelScorePercent: body.confidence,
  };
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
  return `Notification analysis failed with HTTP ${status}.`;
}

export function createAnalyzeNotification({
  fetchImpl = fetch,
  apiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://10.0.2.2:8000",
}: CreateAnalyzeNotificationOptions = {}) {
  const endpoint = `${apiBaseUrl.replace(/\/+$/, "")}/analyze-notification`;

  return async function analyzeNotificationText(
    text: string,
  ): Promise<NotificationAnalysisResult> {
    const cleaned = typeof text === "string" ? text.trim() : "";
    if (!cleaned) {
      throw new NotificationAnalysisError(
        "invalid-request",
        "Select a notification with analyzable text.",
      );
    }

    let response: Response;
    try {
      response = await fetchImpl(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Deliberately omit package: the backend must not retain a package-linked
        // preview for this user-triggered content analysis.
        body: JSON.stringify({ text: cleaned }),
      });
    } catch {
      throw new NotificationAnalysisError(
        "network",
        "Could not reach the notification analysis server.",
      );
    }

    const body: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      throw new NotificationAnalysisError(
        "http",
        errorDetail(body, response.status),
        { status: response.status },
      );
    }

    return mapResponse(body);
  };
}

export const analyzeNotification = createAnalyzeNotification();

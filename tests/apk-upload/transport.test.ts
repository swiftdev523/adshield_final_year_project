import {
  ApkUploadError,
  createUploadApk,
} from "../../services/apk/uploadApk";
import { uploadResponse } from "./fixtures";

const OriginalFormData = global.FormData;

class CapturingFormData {
  readonly _parts: [string, unknown][] = [];

  append(name: string, value: unknown) {
    this._parts.push([name, value]);
  }
}

beforeAll(() => {
  global.FormData = CapturingFormData as unknown as typeof FormData;
});

afterAll(() => {
  global.FormData = OriginalFormData;
});

class FakeXmlHttpRequest {
  method = "";
  url = "";
  async = false;
  timeout = 0;
  status = 0;
  response: unknown = null;
  responseText = "";
  requestBody: Document | XMLHttpRequestBodyInit | null = null;
  readonly setRequestHeader = jest.fn();
  readonly upload: {
    onprogress: ((event: ProgressEvent) => void) | null;
    onload: (() => void) | null;
  } = {
    onprogress: null,
    onload: null,
  };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  ontimeout: (() => void) | null = null;
  onabort: (() => void) | null = null;

  open(method: string, url: string, async: boolean) {
    this.method = method;
    this.url = url;
    this.async = async;
  }

  send(body: Document | XMLHttpRequestBodyInit | null) {
    this.requestBody = body;
  }

  complete(status: number, body: unknown) {
    this.status = status;
    this.responseText = JSON.stringify(body);
    this.onload?.();
  }

  completeText(status: number, body: string) {
    this.status = status;
    this.responseText = body;
    this.onload?.();
  }
}

function setup(apiBaseUrl = "http://backend.test/") {
  const xhr = new FakeXmlHttpRequest();
  const upload = createUploadApk({
    apiBaseUrl,
    xhrFactory: () => xhr as unknown as XMLHttpRequest,
  });
  return { xhr, upload };
}

const request = {
  asset: {
    uri: "file:///storage/emulated/0/Download/sample.apk",
    name: "sample.apk",
    mimeType: "application/vnd.android.package-archive",
  },
  installSource: "apk_sideload" as const,
};

function formDataParts(body: unknown): [string, unknown][] {
  const formData = body as {
    _parts?: [string, unknown][];
    entries?: () => IterableIterator<[string, unknown]>;
  };
  if (formData._parts) return formData._parts;
  return formData.entries ? Array.from(formData.entries()) : [];
}

describe("APK multipart transport", () => {
  it("posts file and install_source without manually setting Content-Type", async () => {
    const { xhr, upload } = setup();
    const phases: string[] = [];
    const progress: unknown[] = [];

    const pending = upload(request, {
      onPhaseChange: (phase) => phases.push(phase),
      onUploadProgress: (value) => progress.push(value),
    });

    expect(xhr.method).toBe("POST");
    expect(xhr.url).toBe("http://backend.test/upload-apk");
    expect(xhr.async).toBe(true);
    expect(xhr.setRequestHeader).not.toHaveBeenCalled();
    expect(formDataParts(xhr.requestBody)).toEqual([
      [
        "file",
        {
          uri: request.asset.uri,
          name: request.asset.name,
          type: request.asset.mimeType,
        },
      ],
      ["install_source", "apk_sideload"],
    ]);

    xhr.upload.onprogress?.({
      lengthComputable: true,
      loaded: 25,
      total: 100,
    } as ProgressEvent);
    xhr.upload.onload?.();
    expect(phases).toEqual(["uploading", "analysing"]);
    expect(progress).toEqual([
      { loadedBytes: 25, totalBytes: 100, fraction: 0.25 },
    ]);

    xhr.complete(200, uploadResponse());
    await expect(pending).resolves.toMatchObject({
      overallRiskScore: 56,
      modelPrediction: "Malicious",
    });
  });

  it.each([
    [400, "Uploaded file must have a .apk extension."],
    [413, "APK file exceeds the 200 MB limit."],
    [422, "Failed to parse APK: invalid manifest"],
  ])("returns backend detail for HTTP %i", async (status, detail) => {
    const { xhr, upload } = setup();
    const pending = upload(request);

    xhr.complete(status, { detail });

    await expect(pending).rejects.toMatchObject({
      name: "ApkUploadError",
      kind: "http",
      status,
      message: detail,
    });
  });

  it("distinguishes network failures from invalid successful responses", async () => {
    const first = setup();
    const networkFailure = first.upload(request);
    first.xhr.onerror?.();
    await expect(networkFailure).rejects.toMatchObject({
      kind: "network",
      retryable: true,
    });

    const second = setup();
    const invalidResponse = second.upload(request);
    second.xhr.complete(200, { status: "ok" });
    await expect(invalidResponse).rejects.toMatchObject({
      kind: "invalid-response",
      status: 200,
    });
  });

  it("rejects invalid JSON returned with a successful status", async () => {
    const { xhr, upload } = setup();
    const pending = upload(request);

    xhr.completeText(200, "{not valid JSON");

    await expect(pending).rejects.toMatchObject({
      kind: "invalid-response",
      status: 200,
    });
  });

  it("reports a timeout as a retryable transport failure", async () => {
    const { xhr, upload } = setup();
    const pending = upload(request);

    xhr.ontimeout?.();

    await expect(pending).rejects.toMatchObject({
      kind: "timeout",
      retryable: true,
    });
  });

  it("rejects an invalid picker asset before creating a request", async () => {
    const xhrFactory = jest.fn(
      () => new FakeXmlHttpRequest() as unknown as XMLHttpRequest,
    );
    const upload = createUploadApk({ xhrFactory });

    await expect(
      upload({
        asset: { uri: "", name: "" },
        installSource: "apk_sideload",
      }),
    ).rejects.toBeInstanceOf(ApkUploadError);
    expect(xhrFactory).not.toHaveBeenCalled();
  });
});

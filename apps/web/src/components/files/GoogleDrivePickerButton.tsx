"use client";

import { useState } from "react";

import { primaryButtonClass, secondaryButtonClass } from "@/lib/ui";

const GOOGLE_PICKER_SCOPE = "https://www.googleapis.com/auth/drive.file";
const GOOGLE_API_SCRIPT = "https://apis.google.com/js/api.js";
const GOOGLE_IDENTITY_SCRIPT = "https://accounts.google.com/gsi/client";

const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() ?? "";
const googleApiKey = process.env.NEXT_PUBLIC_GOOGLE_API_KEY?.trim() ?? "";
const googleAppId = process.env.NEXT_PUBLIC_GOOGLE_APP_ID?.trim() ?? "";

type GoogleScriptWindow = Window &
  typeof globalThis & {
    gapi?: {
      load: (api: string, callback: () => void) => void;
    };
    google?: {
      accounts?: {
        oauth2?: {
          initTokenClient: (config: GoogleTokenClientConfig) => GoogleTokenClient;
        };
      };
      picker?: GooglePickerApi;
    };
  };

type GoogleTokenClientConfig = {
  client_id: string;
  scope: string;
  callback: (response: GoogleTokenResponse) => void;
};

type GoogleTokenResponse = {
  access_token?: string;
  error?: string;
  error_description?: string;
};

type GoogleTokenClient = {
  requestAccessToken: (overrideConfig?: { prompt?: string }) => void;
};

type GooglePickerDocumentKeys = {
  ID: string;
  NAME: string;
  MIME_TYPE: string;
  URL: string;
  ICON_URL: string;
  THUMBNAILS: string;
};

type GooglePickerApi = {
  Action: {
    PICKED: string;
    CANCEL: string;
  };
  Document: GooglePickerDocumentKeys;
  Response: {
    ACTION: string;
    DOCUMENTS: string;
  };
  ViewId: {
    DOCS: string;
  };
  DocsView: new (viewId: string) => unknown;
  PickerBuilder: new () => GooglePickerBuilder;
};

type GooglePickerBuilder = {
  addView: (view: unknown) => GooglePickerBuilder;
  setAppId: (appId: string) => GooglePickerBuilder;
  setCallback: (callback: (data: GooglePickerCallback) => void) => GooglePickerBuilder;
  setDeveloperKey: (developerKey: string) => GooglePickerBuilder;
  setOAuthToken: (token: string) => GooglePickerBuilder;
  build: () => {
    setVisible: (visible: boolean) => void;
  };
};

type GooglePickerDocument = Record<string, unknown>;

type GooglePickerCallback = Record<string, unknown>;

export type GoogleDrivePickedFile = {
  drive_file_id: string;
  name: string;
  mime_type: string | null;
  url: string | null;
  icon_url: string | null;
  thumbnail_url: string | null;
};

type GoogleDrivePickerButtonProps = {
  onPicked: (file: GoogleDrivePickedFile) => void | Promise<void>;
  disabled?: boolean;
  label?: string;
  className?: string;
  showConfigNote?: boolean;
};

const scriptPromises = new Map<string, Promise<void>>();

function loadScript(src: string): Promise<void> {
  if (scriptPromises.has(src)) {
    return scriptPromises.get(src)!;
  }

  const promise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${src}"]`);
    if (existing?.dataset.loaded === "true") {
      resolve();
      return;
    }

    const script = existing ?? document.createElement("script");
    script.src = src;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      script.dataset.loaded = "true";
      resolve();
    };
    script.onerror = () => {
      scriptPromises.delete(src);
      reject(new Error("Google Picker could not be loaded."));
    };

    if (!existing) {
      document.head.appendChild(script);
    }
  });

  scriptPromises.set(src, promise);
  return promise;
}

function loadPickerApi(): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      reject(new Error("Google Picker timed out while loading."));
    }, 10000);

    const gapi = (window as GoogleScriptWindow).gapi;
    if (!gapi) {
      window.clearTimeout(timeout);
      reject(new Error("Google API loader is unavailable."));
      return;
    }

    gapi.load("picker", () => {
      window.clearTimeout(timeout);
      resolve();
    });
  });
}

async function loadGooglePickerDependencies(): Promise<GoogleScriptWindow> {
  await Promise.all([loadScript(GOOGLE_API_SCRIPT), loadScript(GOOGLE_IDENTITY_SCRIPT)]);
  await loadPickerApi();

  const googleWindow = window as GoogleScriptWindow;
  if (!googleWindow.google?.picker || !googleWindow.google.accounts?.oauth2) {
    throw new Error("Google Picker is not available in this browser session.");
  }
  return googleWindow;
}

function getStringField(
  doc: GooglePickerDocument,
  pickerKey: string,
  fallbackKey: string,
): string | null {
  const value = doc[pickerKey] ?? doc[fallbackKey];
  return typeof value === "string" && value.trim() ? value : null;
}

function getThumbnailUrl(doc: GooglePickerDocument, pickerKey: string): string | null {
  const thumbnails = doc[pickerKey] ?? doc.thumbnails;
  if (!Array.isArray(thumbnails)) {
    return null;
  }
  const first = thumbnails.find((item) => item && typeof item === "object");
  if (!first || typeof first !== "object") {
    return null;
  }
  const url = (first as Record<string, unknown>).url;
  return typeof url === "string" && url.trim() ? url : null;
}

function toPickedFile(
  doc: GooglePickerDocument | undefined,
  keys: GooglePickerDocumentKeys,
): GoogleDrivePickedFile | null {
  if (!doc) {
    return null;
  }

  const driveFileId = getStringField(doc, keys.ID, "id");
  const name = getStringField(doc, keys.NAME, "name");
  if (!driveFileId || !name) {
    return null;
  }

  return {
    drive_file_id: driveFileId,
    name,
    mime_type: getStringField(doc, keys.MIME_TYPE, "mimeType"),
    url: getStringField(doc, keys.URL, "url") ?? getStringField(doc, "webViewLink", "webViewLink"),
    icon_url: getStringField(doc, keys.ICON_URL, "iconUrl"),
    thumbnail_url: getThumbnailUrl(doc, keys.THUMBNAILS),
  };
}

export default function GoogleDrivePickerButton({
  onPicked,
  disabled = false,
  label = "Select from Google Drive",
  className,
  showConfigNote = true,
}: GoogleDrivePickerButtonProps) {
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const configured = Boolean(googleClientId && googleApiKey);

  async function openPicker() {
    if (!configured || disabled || opening) {
      return;
    }

    setOpening(true);
    setError(null);

    try {
      const googleWindow = await loadGooglePickerDependencies();
      const oauth = googleWindow.google?.accounts?.oauth2;
      const picker = googleWindow.google?.picker;
      if (!oauth || !picker) {
        throw new Error("Google Picker is not ready.");
      }

      const tokenClient = oauth.initTokenClient({
        client_id: googleClientId,
        scope: GOOGLE_PICKER_SCOPE,
        callback: (response) => {
          if (response.error || !response.access_token) {
            setOpening(false);
            setError(response.error_description ?? "Google Drive access was not granted.");
            return;
          }

          const view = new picker.DocsView(picker.ViewId.DOCS);
          let builder = new picker.PickerBuilder()
            .addView(view)
            .setDeveloperKey(googleApiKey)
            .setOAuthToken(response.access_token)
            .setCallback((data) => {
              const action = data[picker.Response.ACTION];
              if (action === picker.Action.CANCEL) {
                setOpening(false);
                return;
              }
              if (action !== picker.Action.PICKED) {
                return;
              }

              setOpening(false);
              const docs = data[picker.Response.DOCUMENTS];
              const pickedFile = toPickedFile(
                Array.isArray(docs) ? (docs[0] as GooglePickerDocument | undefined) : undefined,
                picker.Document,
              );
              if (!pickedFile) {
                setError("Google Drive did not return usable file metadata.");
                return;
              }
              void Promise.resolve(onPicked(pickedFile)).catch((caught) => {
                setError(caught instanceof Error ? caught.message : "Could not save the selected file.");
              });
            });

          if (googleAppId) {
            builder = builder.setAppId(googleAppId);
          }

          builder.build().setVisible(true);
        },
      });

      tokenClient.requestAccessToken({ prompt: "" });
    } catch (caught) {
      setOpening(false);
      setError(caught instanceof Error ? caught.message : "Google Picker could not be opened.");
    }
  }

  if (!configured) {
    return (
      <div className={className}>
        <button type="button" className={secondaryButtonClass} disabled>
          Configure Google Drive Picker
        </button>
        {showConfigNote ? (
          <p className="mt-1 max-w-xs text-xs leading-5 text-text-muted">
            Set browser-safe Google Picker credentials to select Drive files here.
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className={className}>
      <button
        type="button"
        className={primaryButtonClass}
        onClick={() => void openPicker()}
        disabled={disabled || opening}
      >
        {opening ? "Opening..." : label}
      </button>
      {error ? (
        <p className="mt-1 max-w-sm text-xs leading-5 text-[color:var(--red)]">
          {error}
        </p>
      ) : null}
    </div>
  );
}

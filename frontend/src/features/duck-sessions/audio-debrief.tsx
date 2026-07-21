"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { SupabaseSessionProvider } from "@/features/auth/supabase-session-provider";
import { createApiClient } from "@/lib/api/client";
import styles from "./audio-debrief.module.css";

type SuggestedAction = "complete" | "keep_open" | "archive";

interface ResolutionSuggestion {
  actual_easiness_score: number | null;
  actual_minutes: number | null;
  suggested_action: SuggestedAction;
  task_id: string;
}

interface DuckSession {
  confirmed_at: string | null;
  failure_code: string | null;
  id: string;
  resolution_suggestions: ResolutionSuggestion[];
  root_task_id: string | null;
  status: "processing" | "completed" | "failed";
  transcript: string | null;
}

interface AudioDebriefProps {
  mode: "capture" | "debrief";
  onComplete?: () => void | Promise<void>;
  taskTitles?: Readonly<Record<string, string>>;
}

const acceptedAudio = [
  "audio/m4a",
  "audio/mp4",
  "audio/mpeg",
  "audio/wav",
  "audio/webm",
].join(",");

function uploadMediaType(file: File): string {
  if (acceptedAudio.split(",").includes(file.type)) return file.type;
  const extension = file.name.split(".").pop()?.toLowerCase();
  return (
    {
      m4a: "audio/m4a",
      mp3: "audio/mpeg",
      mp4: "audio/mp4",
      wav: "audio/wav",
      webm: "audio/webm",
    }[extension ?? ""] ?? "audio/webm"
  );
}

export function AudioDebrief({
  mode,
  onComplete,
  taskTitles = {},
}: AudioDebriefProps) {
  const apiClient = useMemo(
    () => createApiClient(new SupabaseSessionProvider()),
    [],
  );
  const [session, setSession] = useState<DuckSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const microphoneStream = useRef<MediaStream | null>(null);
  const recordedChunks = useRef<Blob[]>([]);
  const discardRecording = useRef(false);

  useEffect(
    () => () => {
      discardRecording.current = true;
      if (recorder.current?.state !== "inactive") recorder.current?.stop();
      microphoneStream.current?.getTracks().forEach((track) => {
        track.stop();
      });
    },
    [],
  );

  async function processAudio(audio: Blob, mediaType: string): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      const result = await apiClient.request<DuckSession>(
        "/api/v1/duck-sessions",
        {
          body: audio,
          headers: { "Content-Type": mediaType },
          method: "POST",
        },
      );
      setSession(result);
      if (result.status === "failed") {
        setError("Duky could not understand that recording. Try another one.");
      } else {
        await onComplete?.();
      }
    } catch {
      setError("The recording could not be processed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const audio = form.get("audio");
    if (!(audio instanceof File) || !audio.size) return;
    await processAudio(audio, uploadMediaType(audio));
  }

  async function startMicrophone(): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia || !globalThis.MediaRecorder) {
      setError(
        "A microphone is not available here. Choose an audio file instead.",
      );
      setShowUpload(true);
      return;
    }
    setError(null);
    setSession(null);
    discardRecording.current = false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const nextRecorder = new MediaRecorder(stream);
      microphoneStream.current = stream;
      recorder.current = nextRecorder;
      recordedChunks.current = [];
      nextRecorder.addEventListener("dataavailable", (event) => {
        if (event.data.size) recordedChunks.current.push(event.data);
      });
      nextRecorder.addEventListener("stop", () => {
        stream.getTracks().forEach((track) => {
          track.stop();
        });
        setRecording(false);
        if (discardRecording.current || !recordedChunks.current.length) return;
        const audio = new Blob(recordedChunks.current, { type: "audio/webm" });
        void processAudio(audio, "audio/webm");
      });
      nextRecorder.start();
      setRecording(true);
    } catch {
      setError(
        "Microphone access was not available. Choose an audio file instead.",
      );
      setShowUpload(true);
    }
  }

  function stopMicrophone(): void {
    if (recorder.current?.state === "recording") recorder.current.stop();
  }

  async function confirm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const decisions = session.resolution_suggestions.map((suggestion) => {
        const action = form.get(
          `${suggestion.task_id}:action`,
        ) as SuggestedAction;
        return {
          task_id: suggestion.task_id,
          action,
          actual_minutes:
            action === "complete"
              ? Number(form.get(`${suggestion.task_id}:minutes`))
              : null,
          actual_easiness_score:
            action === "complete"
              ? Number(form.get(`${suggestion.task_id}:ease`))
              : null,
        };
      });
      const confirmed = await apiClient.request<DuckSession>(
        `/api/v1/duck-sessions/${session.id}/confirm`,
        {
          body: JSON.stringify({ decisions }),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        },
      );
      setSession(confirmed);
      await onComplete?.();
    } catch {
      setError("Those choices could not be saved. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const uploadForm = (
    <form className={styles.upload} onSubmit={upload}>
      <input accept={acceptedAudio} name="audio" required type="file" />
      <button disabled={busy} type="submit">
        {busy ? "Listening…" : "Upload audio"}
      </button>
    </form>
  );

  const result = (
    <>
      {error ? (
        <p className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
      {session?.transcript ? (
        <blockquote>{session.transcript}</blockquote>
      ) : null}
      {session?.status === "completed" && session.root_task_id ? (
        <p className={styles.success}>Tasks added. Review them below.</p>
      ) : null}
      {session?.resolution_suggestions.length && !session.confirmed_at ? (
        <form className={styles.suggestions} onSubmit={confirm}>
          <h3>Your call</h3>
          {session.resolution_suggestions.map((suggestion) => (
            <fieldset key={suggestion.task_id}>
              <legend>
                {taskTitles[suggestion.task_id] ?? "Matched open task"}
              </legend>
              <select
                defaultValue={suggestion.suggested_action}
                name={`${suggestion.task_id}:action`}
              >
                <option value="complete">Complete</option>
                <option value="keep_open">Keep open</option>
                <option value="archive">Archive</option>
              </select>
              <label>
                Minutes
                <input
                  defaultValue={suggestion.actual_minutes ?? 30}
                  min="1"
                  name={`${suggestion.task_id}:minutes`}
                  type="number"
                />
              </label>
              <label>
                Easiness
                <select
                  defaultValue={suggestion.actual_easiness_score ?? 3}
                  name={`${suggestion.task_id}:ease`}
                >
                  {[1, 2, 3, 4, 5].map((score) => (
                    <option key={score} value={score}>
                      {score} / 5
                    </option>
                  ))}
                </select>
              </label>
            </fieldset>
          ))}
          <button disabled={busy} type="submit">
            Confirm choices
          </button>
        </form>
      ) : null}
      {session?.confirmed_at ? (
        <p className={styles.success}>Debrief saved.</p>
      ) : null}
    </>
  );

  if (mode === "capture") {
    return (
      <details className={styles.panel}>
        <summary>Add by voice</summary>
        <p>
          Talk through the work on your mind and Duky will pull out the tasks.
        </p>
        {uploadForm}
        {result}
      </details>
    );
  }

  return (
    <section className={styles.panel} aria-labelledby="debrief-heading">
      <h2 id="debrief-heading">Debrief with Duky</h2>
      <p>Talk through what happened. You’ll review every suggested change.</p>
      <div className={styles.microphoneActions}>
        <button
          className={styles.microphoneButton}
          disabled={busy}
          onClick={recording ? stopMicrophone : () => void startMicrophone()}
          type="button"
        >
          {recording ? "Stop and review" : "Start debrief"}
        </button>
        {!recording ? (
          <button
            className={styles.uploadInstead}
            onClick={() => setShowUpload((current) => !current)}
            type="button"
          >
            Use an audio file instead
          </button>
        ) : null}
      </div>
      {recording ? <p className={styles.recording}>Listening…</p> : null}
      {showUpload ? uploadForm : null}
      {result}
    </section>
  );
}

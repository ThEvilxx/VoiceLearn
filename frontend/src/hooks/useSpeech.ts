import { useCallback, useRef, useState } from "react";

interface UseSpeechReturn {
  isRecording: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob | null>;
  error: string | null;
}

export function useSpeech(): UseSpeechReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const resolveRef = useRef<((blob: Blob | null) => void) | null>(null);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        chunksRef.current = [];
        resolveRef.current?.(blob);
        resolveRef.current = null;
      };

      recorder.onerror = () => {
        setError("Microphone error. Check your browser permissions.");
        setIsRecording(false);
        resolveRef.current?.(null);
        resolveRef.current = null;
      };

      recorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      setError(
        "Cannot access microphone. Please allow microphone access in your browser settings.",
      );
    }
  }, []);

  const stopRecording = useCallback((): Promise<Blob | null> => {
    const stopPromise = new Promise<Blob | null>((resolve) => {
      resolveRef.current = resolve;
      recorderRef.current?.stop();
      setIsRecording(false);
    });

    const timeoutPromise = new Promise<Blob | null>((resolve) => {
      setTimeout(() => {
        if (resolveRef.current) {
          resolveRef.current = null;
          setIsRecording(false);
          if (recorderRef.current?.state === "recording") {
            recorderRef.current.stop();
          }
          resolve(null);
        }
      }, 5000);
    });

    return Promise.race([stopPromise, timeoutPromise]);
  }, []);

  return { isRecording, startRecording, stopRecording, error };
}

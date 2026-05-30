import { useSpeech } from "../../hooks/useSpeech";

interface VoiceButtonProps {
  onAudioReady: (blob: Blob) => void;
  disabled?: boolean;
}

export function VoiceButton({ onAudioReady, disabled }: VoiceButtonProps) {
  const { isRecording, startRecording, stopRecording, error } = useSpeech();

  const handleClick = async () => {
    if (isRecording) {
      const blob = await stopRecording();
      if (blob) onAudioReady(blob);
    } else {
      await startRecording();
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <button
        onClick={handleClick}
        disabled={disabled}
        style={{
          width: 48,
          height: 48,
          borderRadius: "50%",
          border: "none",
          background: isRecording ? "#e74c3c" : "#4a90d9",
          color: "#fff",
          fontSize: "1.4rem",
          cursor: disabled ? "default" : "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          animation: isRecording ? "pulse 1.5s infinite" : "none",
        }}
        title={isRecording ? "Stop recording" : "Start recording"}
      >
        {isRecording ? "⏹" : "🎤"}
      </button>
      {isRecording && (
        <span style={{ color: "#e74c3c", fontSize: "0.85rem" }}>Listening...</span>
      )}
      {error && <span style={{ color: "#e74c3c", fontSize: "0.8rem" }}>{error}</span>}
    </div>
  );
}

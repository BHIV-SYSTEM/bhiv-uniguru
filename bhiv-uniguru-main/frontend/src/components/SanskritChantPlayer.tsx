import React, { useState, useRef, useEffect } from "react";
import { Play, Pause, RotateCcw, Volume2, VolumeX, Music } from "lucide-react";
import type { ChantAudioInfo } from "../types/sanskrit";

interface SanskritChantPlayerProps {
  audio: ChantAudioInfo;
  title?: string;
  className?: string;
}

export const SanskritChantPlayer: React.FC<SanskritChantPlayerProps> = ({
  audio,
  title = "Vāgdhenu Sanskrit Chanting",
  className = "",
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(audio.metadata?.duration_seconds || 0);
  const [isMuted, setIsMuted] = useState(false);

  // Derive correct audio URL (handle relative / absolute / backend host)
  const getAudioSource = () => {
    if (!audio.audio_url) return "";
    if (audio.audio_url.startsWith("http://") || audio.audio_url.startsWith("https://")) {
      return audio.audio_url;
    }
    const backendPort = "8001";
    return `http://localhost:${backendPort}${audio.audio_url}`;
  };

  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;

    const onTimeUpdate = () => setCurrentTime(el.currentTime);
    const onLoadedMetadata = () => {
      if (el.duration && !isNaN(el.duration)) {
        setDuration(el.duration);
      }
    };
    const onEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    el.addEventListener("timeupdate", onTimeUpdate);
    el.addEventListener("loadedmetadata", onLoadedMetadata);
    el.addEventListener("ended", onEnded);

    return () => {
      el.removeEventListener("timeupdate", onTimeUpdate);
      el.removeEventListener("loadedmetadata", onLoadedMetadata);
      el.removeEventListener("ended", onEnded);
    };
  }, []);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => {
        setIsPlaying(true);
      }).catch((err) => {
        console.warn("Audio playback failed:", err);
      });
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setCurrentTime(val);
    if (audioRef.current) {
      audioRef.current.currentTime = val;
    }
  };

  const handleReset = () => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = 0;
    setCurrentTime(0);
    if (!isPlaying) {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    audioRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  if (!audio.available) {
    return (
      <div className={`rounded-xl bg-gray-900/60 border border-gray-800 p-3 text-xs text-gray-400 ${className}`}>
        <div className="flex items-center gap-2">
          <Music size={14} className="text-gray-500" />
          <span>Chanting audio unavailable</span>
          {audio.reason && <span className="text-gray-600">({audio.reason})</span>}
        </div>
      </div>
    );
  }

  const meter = audio.meter;
  const audioSrc = getAudioSource();

  return (
    <div className={`rounded-xl bg-gradient-to-r from-purple-950/40 via-violet-950/20 to-gray-900 border border-purple-800/40 p-3.5 shadow-lg ${className}`}>
      <audio ref={audioRef} src={audioSrc} preload="metadata" />

      {/* Top row: Title and Meter badge */}
      <div className="flex items-center justify-between gap-2 mb-2.5 flex-wrap">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-purple-600/30 border border-purple-500/40 flex items-center justify-center text-purple-300">
            <Music size={12} />
          </div>
          <div>
            <div className="text-xs font-semibold text-purple-200 flex items-center gap-1.5">
              {title}
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-purple-900/60 text-purple-300 border border-purple-700/50">
                {audio.engine || "Vāgdhenu TTS"}
              </span>
            </div>
            {meter && (
              <div className="text-[11px] text-gray-400 mt-0.5 flex items-center gap-2">
                <span>
                  छन्दस् (Meter): <strong className="text-purple-300">{meter.meter_name}</strong>
                  {meter.sanskrit_name && ` (${meter.sanskrit_name})`}
                </span>
                {meter.syllable_count ? (
                  <span className="text-gray-500">· {meter.syllable_count} syllables</span>
                ) : null}
              </div>
            )}
          </div>
        </div>

        {meter?.laghu_guru_pattern && (
          <div className="text-[10px] font-mono text-purple-400/80 bg-purple-950/50 px-2 py-0.5 rounded border border-purple-800/30">
            {meter.laghu_guru_pattern.slice(0, 32)}
          </div>
        )}
      </div>

      {/* Center row: Playback controls and progress */}
      <div className="flex items-center gap-3">
        <button
          onClick={togglePlay}
          className="w-8 h-8 rounded-full bg-purple-600 hover:bg-purple-500 text-white flex items-center justify-center shadow-md transition-all active:scale-95"
          title={isPlaying ? "Pause" : "Play Chanting"}
        >
          {isPlaying ? <Pause size={14} /> : <Play size={14} className="ml-0.5" />}
        </button>

        <button
          onClick={handleReset}
          className="text-gray-400 hover:text-purple-300 transition-colors p-1"
          title="Replay from start"
        >
          <RotateCcw size={14} />
        </button>

        <span className="text-[11px] font-mono text-gray-400 w-9 text-right">
          {formatTime(currentTime)}
        </span>

        <input
          type="range"
          min={0}
          max={duration || 100}
          step={0.1}
          value={currentTime}
          onChange={handleSeek}
          className="flex-1 h-1.5 rounded-lg appearance-none bg-gray-800 accent-purple-500 cursor-pointer"
        />

        <span className="text-[11px] font-mono text-gray-400 w-9">
          {formatTime(duration)}
        </span>

        <button
          onClick={toggleMute}
          className="text-gray-400 hover:text-purple-300 transition-colors p-1"
          title={isMuted ? "Unmute" : "Mute"}
        >
          {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
        </button>
      </div>
    </div>
  );
};

export default SanskritChantPlayer;

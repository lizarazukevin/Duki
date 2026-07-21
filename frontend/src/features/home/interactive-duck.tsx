"use client";

import Image from "next/image";
import { useEffect, useRef } from "react";

interface SqueakProfile {
  duration: number;
  endFrequency: number;
  filterFrequency: number;
  startFrequency: number;
  wobble: number;
}

const SQUEAK_PROFILES: readonly SqueakProfile[] = [
  {
    startFrequency: 300,
    endFrequency: 600,
    duration: 0.38,
    wobble: 10,
    filterFrequency: 1950,
  },
];

export function InteractiveDuck() {
  const audioContext = useRef<AudioContext | null>(null);
  const squeakIndex = useRef(0);

  useEffect(
    () => () => {
      void audioContext.current?.close();
    },
    [],
  );

  async function squeak(): Promise<void> {
    const context = audioContext.current ?? new AudioContext();
    audioContext.current = context;
    await context.resume();

    const profile =
      SQUEAK_PROFILES[squeakIndex.current % SQUEAK_PROFILES.length];
    squeakIndex.current += 1;
    const now = context.currentTime;
    const oscillator = context.createOscillator();
    const wobble = context.createOscillator();
    const wobbleDepth = context.createGain();
    const filter = context.createBiquadFilter();
    const volume = context.createGain();

    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(profile.startFrequency, now);
    oscillator.frequency.exponentialRampToValueAtTime(
      profile.endFrequency,
      now + 0.14,
    );
    wobble.frequency.setValueAtTime(profile.wobble, now);
    wobbleDepth.gain.setValueAtTime(38, now);
    wobble.connect(wobbleDepth).connect(oscillator.detune);

    filter.type = "bandpass";
    filter.frequency.setValueAtTime(profile.filterFrequency, now);
    filter.Q.setValueAtTime(2.8, now);
    volume.gain.setValueAtTime(0.0001, now);
    volume.gain.exponentialRampToValueAtTime(0.78, now + 0.02);
    volume.gain.linearRampToValueAtTime(0.52, now + profile.duration * 0.72);
    volume.gain.exponentialRampToValueAtTime(0.0001, now + profile.duration);

    oscillator.connect(filter).connect(volume).connect(context.destination);
    oscillator.start(now);
    wobble.start(now);
    oscillator.stop(now + profile.duration);
    wobble.stop(now + profile.duration);
  }

  return (
    <button
      aria-label="Squeak Duky"
      className="interactive-duck"
      onClick={() => void squeak().catch(() => undefined)}
      title="Tap Duky for a squeak"
      type="button"
    >
      <Image
        alt=""
        aria-hidden="true"
        className="home-duck duck-awake"
        height={720}
        priority
        sizes="(max-width: 560px) 88vw, 360px"
        src="/images/duky-3d.webp"
        width={720}
      />
      <Image
        alt=""
        aria-hidden="true"
        className="home-duck duck-blink"
        height={720}
        sizes="(max-width: 560px) 88vw, 360px"
        src="/images/duky-3d-blink.webp"
        width={720}
      />
    </button>
  );
}

import { useEffect, useState } from "react";

export function useCountdown(initialSeconds) {
  const [seconds, setSeconds] = useState(initialSeconds);

  useEffect(() => {
    setSeconds(initialSeconds);
  }, [initialSeconds]);

  useEffect(() => {
    if (initialSeconds == null || initialSeconds <= 0) return undefined;

    const timer = setInterval(() => {
      setSeconds((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [initialSeconds]);

  return seconds;
}

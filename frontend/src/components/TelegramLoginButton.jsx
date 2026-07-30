import { useEffect, useRef } from "react";

// Embeds the official Telegram Login Widget (plan §3). On approval Telegram
// calls window.onTelegramAuth with the signed payload, which we forward to
// the backend for HMAC verification.
export default function TelegramLoginButton({ botUsername, onAuth }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!botUsername || !containerRef.current) return undefined;

    window.onTelegramAuth = (user) => onAuth(user);
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", botUsername);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    containerRef.current.appendChild(script);

    return () => {
      delete window.onTelegramAuth;
      containerRef.current?.replaceChildren();
    };
  }, [botUsername, onAuth]);

  return <div ref={containerRef} className="flex justify-center" />;
}

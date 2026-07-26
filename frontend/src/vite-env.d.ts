/// <reference types="vite/client" />

interface Window {
  turnstile?: {
    render: (
      element: HTMLElement,
      options: {
        sitekey: string;
        action: "nutshellm_run";
        callback: (token: string) => void;
        "expired-callback": () => void;
        "error-callback": () => void;
        theme: "light" | "dark";
      },
    ) => string;
    remove: (widgetId: string) => void;
    reset: (widgetId: string) => void;
  };
}

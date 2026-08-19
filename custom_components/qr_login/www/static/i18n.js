/**
 * Page translations. English is the base language; every other language is a
 * translation of it and falls back to English for missing keys.
 *
 * Language detection mirrors the frontend's getLocalLanguage():
 * localStorage.selectedLanguage, navigator.languages, navigator.language, en.
 */
window.QRLoginI18n = (function () {
  "use strict";

  var DEFAULT_LANGUAGE = "en";

  var TRANSLATIONS = {
    en: {
      "channel.qr": "QR code",
      "channel.notify": "Push notification",

      "error.generic": "Something went wrong, please try again.",
      "error.connection": "Connection error.",
      "error.disabled": "QR Login is currently disabled.",
      "error.rate_limited": "Too many attempts from this device. Try again shortly.",
      "error.rate_limited_global": "Too many requests in progress. Try again shortly.",
      "error.recaptcha_required": "reCAPTCHA verification unavailable. Reload the page.",
      "error.recaptcha_failed": "reCAPTCHA verification failed. Reload the page.",
      "error.recaptcha_unavailable":
        "reCAPTCHA could not issue a token for this page. Check that {origin} is listed among the allowed domains of the site key, that the key is a reCAPTCHA v3 key, and that this browser can reach google.com.",
      "error.invalid_json": "Invalid request.",
      "error.invalid_request": "Invalid request.",
      "error.not_initialized": "QR Login is not ready yet. Try again in a few seconds.",
      "error.session_not_found": "Session not found or already used.",
      "error.session_already_processed": "This request has already been handled.",
      "error.target_user_not_found": "Target account not found.",
      "error.token_creation_failed":
        "Could not issue the token. Check the Home Assistant logs.",
      "error.session_id_required": "Missing session ID.",
      "error.admin_required":
        "This request is for another account: only an administrator can approve it.",
      "error.server": "Server error ({status}).",

      "start.title": "QR Login - Home Assistant",
      "start.heading": "QR Login",
      "start.subtitle": "Sign in to Home Assistant using a device you are already signed in on",
      "start.tab_qr": "QR code",
      "start.tab_notify": "Notification",
      "start.qr_instruction": "Scan it with a device already connected to your instance",
      "start.qr_notice":
        "Works with a browser you are already signed in on. If you do not have one, the page it opens will offer the Companion App.",
      "start.username_label": "Username to request access for",
      "start.username_placeholder": "e.g. guest_qr",
      "start.request_button": "Request access",
      "start.request_sending": "Sending...",
      "start.waiting": "Waiting for approval...",
      "start.username_required": "Enter a username",
      "start.qr_failed": "Could not generate the QR code. Reload the page.",
      "start.session_lost": "Session not found or expired, please try again",
      "start.denied": "Request rejected",
      "start.expired": "Session expired, please try again",
      "start.approved": "Access approved! Redirecting...",

      "approve.title": "Approve access - Home Assistant",
      "approve.heading": "Approve access",
      "approve.subtitle": "A device is requesting access to your Home Assistant instance",
      "approve.details": "Request details",
      "approve.ip": "IP",
      "approve.user_agent": "User agent",
      "approve.channel": "Channel",
      "approve.target_label": "Account access is requested for",
      "approve.target_mapped": "Preconfigured account from the mapping.",
      "approve.target_unmapped": "No mapping: the token will be issued for your account.",
      "approve.approve": "Approve",
      "approve.deny": "Reject",
      "approve.approving": "Approving...",
      "approve.denying": "Rejecting...",
      "approve.external_notice":
        "Companion App authentication detected. The token will be retrieved automatically.",
      "approve.missing_session": "Missing session ID",
      "approve.details_failed": "Could not load the request details.",
      "approve.connection_failed":
        "Connection error. Check that the server is reachable.",
      "approve.no_session": "This browser has no active Home Assistant session.",
      "approve.open_app": "Open in the Companion App",
      "approve.no_app_prefix": "No app? You can ",
      "approve.no_app_link": "sign in to Home Assistant",
      "approve.no_app_suffix": " in this browser.",
      "approve.external_failed":
        "Could not get credentials from the Companion App. Reopen the request from the app or sign in from a browser.",
      "approve.approved_for": "Access approved for ",
      "approve.rejected": "Request rejected",

      "sessions.title": "QR Login sessions",
      "sessions.heading": "QR Login sessions",
      "sessions.enabled": "Active",
      "sessions.disabled": "Disabled",
      "sessions.loading": "Loading...",
      "sessions.empty": "No access request in progress.",
      "sessions.recent": "Recent requests",
      "sessions.badge_mapped": "from mapping",
      "sessions.badge_unmapped": "no mapping",
      "sessions.approver_account": "Approver's account",
      "sessions.requested_username": "Requested username",
      "sessions.username_empty": "(empty)",
      "sessions.channel": "Channel",
      "sessions.ip": "IP",
      "sessions.user_agent": "User agent",
      "sessions.requested": "Requested",
      "sessions.expires": "Expires in",
      "sessions.cancel": "Cancel",
      "sessions.cancelling": "Cancelling...",
      "sessions.cancelled": "Session cancelled.",
      "sessions.cancel_failed": "Could not cancel the session (HTTP {status}).",
      "sessions.cancel_connection": "Connection error while cancelling.",
      "sessions.admin_required": "Administrator rights are required.",
      "sessions.admin_only":
        "This page is restricted to Home Assistant administrators.",
      "sessions.read_failed": "Could not read the sessions. Retrying...",
      "sessions.retrying": "Connection error. Retrying...",
      "sessions.no_tokens":
        'No Home Assistant session found in this browser. Open Home Assistant, sign in with "Keep me logged in", then reload.',
      "sessions.whoever_approves": "whoever approves",
      "sessions.suffix_unmapped": " (no mapping)",
      "outcome.approved": "Approved",
      "outcome.denied": "Rejected",
      "outcome.cancelled": "Cancelled",
      "outcome.expired": "Expired",
      "outcome.error": "Error",
      "time.seconds": "{n}s ago",
      "time.minutes": "{n} min ago",
      "time.hours": "{n} h ago",
      "time.seconds_short": "{n}s",
    },

    it: {
      "channel.qr": "QR code",
      "channel.notify": "Notifica push",

      "error.generic": "Si è verificato un errore, riprova.",
      "error.connection": "Errore di connessione.",
      "error.disabled": "QR Login è disattivato al momento.",
      "error.rate_limited": "Troppi tentativi da questo dispositivo. Riprova tra poco.",
      "error.rate_limited_global": "Troppe richieste in corso. Riprova tra poco.",
      "error.recaptcha_required": "Verifica reCAPTCHA non disponibile. Ricarica la pagina.",
      "error.recaptcha_failed": "Verifica reCAPTCHA non superata. Ricarica la pagina.",
      "error.recaptcha_unavailable":
        "reCAPTCHA non ha rilasciato un token per questa pagina. Verifica che {origin} sia tra i domini autorizzati della chiave del sito, che la chiave sia di tipo reCAPTCHA v3 e che questo browser riesca a raggiungere google.com.",
      "error.invalid_json": "Richiesta non valida.",
      "error.invalid_request": "Richiesta non valida.",
      "error.not_initialized": "QR Login non è ancora pronto. Riprova tra qualche secondo.",
      "error.session_not_found": "Sessione non trovata o già utilizzata.",
      "error.session_already_processed": "Questa richiesta è già stata gestita.",
      "error.target_user_not_found": "Account di destinazione non trovato.",
      "error.token_creation_failed":
        "Impossibile emettere il token. Controlla i log di Home Assistant.",
      "error.session_id_required": "Session ID mancante.",
      "error.admin_required":
        "Questa richiesta riguarda un altro account: solo un amministratore può approvarla.",
      "error.server": "Errore del server ({status}).",

      "start.title": "QR Login - Home Assistant",
      "start.heading": "QR Login",
      "start.subtitle": "Accedi a Home Assistant con un dispositivo già collegato",
      "start.tab_qr": "QR code",
      "start.tab_notify": "Notifica",
      "start.qr_instruction": "Scansiona con un dispositivo già collegato alla tua istanza",
      "start.qr_notice":
        "Funziona con un browser dove hai già fatto l'accesso. Se non ne hai uno, la pagina che si apre ti proporrà l'app Companion.",
      "start.username_label": "Username per cui richiedere l'accesso",
      "start.username_placeholder": "es. guest_qr",
      "start.request_button": "Richiedi accesso",
      "start.request_sending": "Invio...",
      "start.waiting": "In attesa di approvazione...",
      "start.username_required": "Inserisci uno username",
      "start.qr_failed": "Impossibile generare il QR code. Ricarica la pagina.",
      "start.session_lost": "Sessione non trovata o scaduta, riprova",
      "start.denied": "Richiesta rifiutata",
      "start.expired": "Sessione scaduta, riprova",
      "start.approved": "Accesso approvato! Reindirizzamento...",

      "approve.title": "Approva accesso - Home Assistant",
      "approve.heading": "Approva accesso",
      "approve.subtitle":
        "Un dispositivo sta richiedendo l'accesso alla tua istanza Home Assistant",
      "approve.details": "Dettagli richiesta",
      "approve.ip": "IP",
      "approve.user_agent": "User-Agent",
      "approve.channel": "Canale",
      "approve.target_label": "Account per cui viene richiesto l'accesso",
      "approve.target_mapped": "Account preconfigurato nel mapping.",
      "approve.target_unmapped":
        "Nessun mapping: il token verrà emesso per il tuo account.",
      "approve.approve": "Approva",
      "approve.deny": "Rifiuta",
      "approve.approving": "Approvazione...",
      "approve.denying": "Rifiuto...",
      "approve.external_notice":
        "Autenticazione tramite Companion App rilevata. Il token verrà recuperato automaticamente.",
      "approve.missing_session": "Session ID mancante",
      "approve.details_failed": "Errore nel caricamento dei dettagli.",
      "approve.connection_failed":
        "Errore di connessione. Verifica che il server sia raggiungibile.",
      "approve.no_session": "Questo browser non ha una sessione di Home Assistant attiva.",
      "approve.open_app": "Apri nell'app Companion",
      "approve.no_app_prefix": "Non hai l'app? Puoi ",
      "approve.no_app_link": "accedere a Home Assistant",
      "approve.no_app_suffix": " in questo browser.",
      "approve.external_failed":
        "Impossibile ottenere le credenziali dall'app Companion. Riapri la richiesta dall'app o accedi da un browser.",
      "approve.approved_for": "Accesso approvato per ",
      "approve.rejected": "Richiesta rifiutata",

      "sessions.title": "Sessioni QR Login",
      "sessions.heading": "Sessioni QR Login",
      "sessions.enabled": "Attivo",
      "sessions.disabled": "Disattivato",
      "sessions.loading": "Caricamento...",
      "sessions.empty": "Nessuna richiesta di accesso in corso.",
      "sessions.recent": "Richieste recenti",
      "sessions.badge_mapped": "da mapping",
      "sessions.badge_unmapped": "senza mapping",
      "sessions.approver_account": "Account di chi approva",
      "sessions.requested_username": "Username richiesto",
      "sessions.username_empty": "(vuoto)",
      "sessions.channel": "Canale",
      "sessions.ip": "IP",
      "sessions.user_agent": "User-Agent",
      "sessions.requested": "Richiesta da",
      "sessions.expires": "Scade tra",
      "sessions.cancel": "Annulla",
      "sessions.cancelling": "Annullamento...",
      "sessions.cancelled": "Sessione annullata.",
      "sessions.cancel_failed": "Impossibile annullare la sessione (HTTP {status}).",
      "sessions.cancel_connection": "Errore di connessione durante l'annullamento.",
      "sessions.admin_required": "Servono i privilegi di amministratore.",
      "sessions.admin_only":
        "Questa pagina è riservata agli amministratori di Home Assistant.",
      "sessions.read_failed": "Impossibile leggere le sessioni. Riprovo...",
      "sessions.retrying": "Errore di connessione. Riprovo...",
      "sessions.no_tokens":
        'Nessuna sessione di Home Assistant trovata in questo browser. Apri Home Assistant, accedi selezionando "Mantieni l\'accesso", poi ricarica.',
      "sessions.whoever_approves": "chi ha approvato",
      "sessions.suffix_unmapped": " (senza mapping)",
      "outcome.approved": "Approvata",
      "outcome.denied": "Rifiutata",
      "outcome.cancelled": "Annullata",
      "outcome.expired": "Scaduta",
      "outcome.error": "Errore",
      "time.seconds": "{n}s fa",
      "time.minutes": "{n} min fa",
      "time.hours": "{n} h fa",
      "time.seconds_short": "{n}s",
    },
  };

  function findAvailableLanguage(locale) {
    if (!locale) {
      return undefined;
    }
    var lower = String(locale).toLowerCase();
    if (TRANSLATIONS[lower]) {
      return lower;
    }
    var base = lower.split("-")[0];
    return TRANSLATIONS[base] ? base : undefined;
  }

  function getLocalLanguage() {
    var storage = window.localStorage || {};
    var language;

    if (storage.selectedLanguage) {
      try {
        var stored = JSON.parse(storage.selectedLanguage);
        if (stored) {
          language = findAvailableLanguage(stored);
          if (language) {
            return language;
          }
        }
      } catch (err) {
      }
    }

    if (navigator.languages) {
      for (var i = 0; i < navigator.languages.length; i++) {
        language = findAvailableLanguage(navigator.languages[i]);
        if (language) {
          return language;
        }
      }
    }

    language = findAvailableLanguage(navigator.language);
    return language || DEFAULT_LANGUAGE;
  }

  var language = getLocalLanguage();
  var strings = TRANSLATIONS[language] || TRANSLATIONS[DEFAULT_LANGUAGE];
  var fallback = TRANSLATIONS[DEFAULT_LANGUAGE];

  function t(key, vars) {
    var value = strings[key];
    if (value === undefined) {
      value = fallback[key];
    }
    if (value === undefined) {
      return key;
    }
    if (vars) {
      Object.keys(vars).forEach(function (name) {
        value = value.split("{" + name + "}").join(String(vars[name]));
      });
    }
    return value;
  }

  /** Replace the English text baked into the HTML with the active language. */
  function apply(root) {
    var scope = root || document;

    scope.querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    scope.querySelectorAll("[data-i18n-placeholder]").forEach(function (el) {
      el.placeholder = t(el.getAttribute("data-i18n-placeholder"));
    });

    var titleKey = document.documentElement.getAttribute("data-i18n-title");
    if (titleKey) {
      document.title = t(titleKey);
    }
    document.documentElement.lang = language;
  }

  return { language: language, t: t, apply: apply };
})();

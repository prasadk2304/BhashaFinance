/**
 * Supported language configurations for BhashaFinance AI.
 * Strict Guard: Language selector shows ONLY languages listed and verified here.
 * Defaults: Marathi, Hindi, English.
 */

export interface SupportedLanguage {
  code: string;
  bcp47: string;
  label: string;
  nativeLabel: string;
  isVerified: boolean;
  sarvamSpeaker: string;
}

export const SUPPORTED_LANGUAGES: SupportedLanguage[] = [
  {
    code: "mr",
    bcp47: "mr-IN",
    label: "Marathi",
    nativeLabel: "मराठी",
    isVerified: true,
    sarvamSpeaker: "meera",
  },
  {
    code: "hi",
    bcp47: "hi-IN",
    label: "Hindi",
    nativeLabel: "हिंदी",
    isVerified: true,
    sarvamSpeaker: "meera",
  },
  {
    code: "en",
    bcp47: "en-IN",
    label: "English",
    nativeLabel: "English",
    isVerified: true,
    sarvamSpeaker: "meera",
  },
];

/**
 * Guard function: Filters out any unverified or unlisted languages.
 */
export function getVerifiedLanguages(): SupportedLanguage[] {
  return SUPPORTED_LANGUAGES.filter((lang) => lang.isVerified === true);
}

/**
 * Checks if a language code is verified in the system.
 */
export function isLanguageVerified(code: string): boolean {
  return SUPPORTED_LANGUAGES.some(
    (lang) => (lang.code === code || lang.bcp47 === code) && lang.isVerified
  );
}

/**
 * Resolves standard BCP-47 tag for a given language code. Defaults to mr-IN.
 */
export function resolveBcp47Code(code: string): string {
  const match = SUPPORTED_LANGUAGES.find(
    (lang) => (lang.code === code || lang.bcp47 === code) && lang.isVerified
  );
  return match ? match.bcp47 : "mr-IN";
}


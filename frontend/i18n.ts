import { notFound } from 'next/navigation';
import { getRequestConfig } from 'next-intl/server';

// Supported locales
export const locales = ['es', 'en', 'pt-BR'] as const;
type AppLocale = (typeof locales)[number];

export default getRequestConfig(async ({ locale }) => {
  const l = (locale ?? 'es') as AppLocale;
  if (!locales.includes(l)) notFound();

  return {
    locale: l,
    messages: (await import(`./messages/${l}.json`)).default,
    timeZone: 'America/Buenos_Aires'
  };
});

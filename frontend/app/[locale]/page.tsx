'use client';

import Link from 'next/link';
import { useTranslations, useLocale } from 'next-intl';
import { 
  ShieldCheckIcon, 
  FingerPrintIcon, 
  LockClosedIcon, 
  ChartBarIcon,
  ClockIcon,
  BoltIcon
} from '@heroicons/react/24/outline';
import { ThemeToggle } from '@/components/ThemeToggle';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';

export default function Home() {
  const t = useTranslations('home');
  const tCommon = useTranslations('common');
  const locale = useLocale();

  return (
    <main className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-indigo-950">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <ShieldCheckIcon className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {tCommon('appName')}
            </span>
          </div>
          
          <div className="flex items-center space-x-2">
            <ThemeToggle />
            <LanguageSwitcher />
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center max-w-4xl mx-auto">
          <div className="flex justify-center mb-8 animate-bounce">
            <ShieldCheckIcon className="w-20 h-20 text-indigo-600 dark:text-indigo-400" />
          </div>
          
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 dark:text-white mb-6">
            {tCommon('appName')}
          </h1>
          
          <p className="text-xl md:text-2xl text-gray-600 dark:text-gray-300 mb-4">
            {t('hero.title')}
          </p>
          
          <p className="text-lg text-gray-500 dark:text-gray-400 mb-8">
            {t('hero.subtitle')}
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href={`/${locale}/auth/login`}
              className="px-8 py-4 bg-indigo-600 dark:bg-indigo-500 text-white rounded-lg font-semibold hover:bg-indigo-700 dark:hover:bg-indigo-600 transition-colors shadow-lg hover:shadow-xl"
            >
              {t('hero.cta.getStarted')}
            </Link>
            <Link
              href={`/${locale}/demo`}
              className="px-8 py-4 bg-white dark:bg-gray-800 text-indigo-600 dark:text-indigo-400 border-2 border-indigo-600 dark:border-indigo-400 rounded-lg font-semibold hover:bg-indigo-50 dark:hover:bg-gray-700 transition-colors"
            >
              {t('hero.cta.viewDemo')}
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
            {t('features.title')}
          </h2>
          <p className="text-xl text-gray-600 dark:text-gray-400">
            {t('features.subtitle')}
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Feature 1 - Biometric */}
          <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-md hover:shadow-xl transition-all hover:-translate-y-1 border border-gray-100 dark:border-gray-700">
            <div className="bg-indigo-100 dark:bg-indigo-900 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
              <FingerPrintIcon className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
              {t('features.biometric.title')}
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {t('features.biometric.description')}
            </p>
          </div>

          {/* Feature 2 - Real-time */}
          <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-md hover:shadow-xl transition-all hover:-translate-y-1 border border-gray-100 dark:border-gray-700">
            <div className="bg-green-100 dark:bg-green-900 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
              <BoltIcon className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
              {t('features.realtime.title')}
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {t('features.realtime.description')}
            </p>
          </div>

          {/* Feature 3 - Security */}
          <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-md hover:shadow-xl transition-all hover:-translate-y-1 border border-gray-100 dark:border-gray-700">
            <div className="bg-red-100 dark:bg-red-900 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
              <LockClosedIcon className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
              {t('features.security.title')}
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {t('features.security.description')}
            </p>
          </div>

          {/* Feature 4 - Audit */}
          <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-md hover:shadow-xl transition-all hover:-translate-y-1 border border-gray-100 dark:border-gray-700">
            <div className="bg-purple-100 dark:bg-purple-900 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
              <ChartBarIcon className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3">
              {t('features.audit.title')}
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {t('features.audit.description')}
            </p>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="bg-indigo-600 dark:bg-indigo-900 py-20">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8 text-center text-white">
            <div className="hover:scale-105 transition-transform">
              <div className="text-5xl font-bold mb-2">99.9%</div>
              <div className="text-indigo-200 dark:text-indigo-300">{t('stats.uptime')}</div>
            </div>
            <div className="hover:scale-105 transition-transform">
              <div className="text-5xl font-bold mb-2">&lt;1s</div>
              <div className="text-indigo-200 dark:text-indigo-300">{t('stats.response')}</div>
            </div>
            <div className="hover:scale-105 transition-transform">
              <div className="text-5xl font-bold mb-2">10K+</div>
              <div className="text-indigo-200 dark:text-indigo-300">{t('stats.requests')}</div>
            </div>
            <div className="hover:scale-105 transition-transform">
              <div className="text-5xl font-bold mb-2">256-bit</div>
              <div className="text-indigo-200 dark:text-indigo-300">Encryption</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-800 dark:to-purple-800 rounded-3xl p-12 text-center text-white shadow-2xl">
          <h2 className="text-4xl font-bold mb-4">{t('cta.title')}</h2>
          <p className="text-xl text-indigo-100 dark:text-indigo-200 mb-8">
            {t('cta.subtitle')}
          </p>
          <Link
            href={`/${locale}/subscribe`}
            className="inline-block px-10 py-4 bg-white text-indigo-600 rounded-lg font-bold text-lg hover:bg-gray-100 transition-colors shadow-lg hover:shadow-xl"
          >
            {t('cta.button')}
          </Link>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">Planes</h2>
          <p className="text-gray-600 dark:text-gray-400">Elige el plan que se adapta a tu equipo</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Starter */}
          <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 shadow">
            <h3 className="text-xl font-semibold mb-2">Starter</h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">Hasta 2 aprobadores</p>
            <div className="text-4xl font-bold mb-6">$25<span className="text-base font-medium text-gray-500">/mes</span></div>
            <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-300 mb-6">
              <li>• 2 aprobadores</li>
              <li>• Solicitudes ilimitadas</li>
              <li>• Autenticación biométrica</li>
            </ul>
            <Link href={`/${locale}/subscribe?plan=starter`} className="block text-center w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded px-4 py-2">Suscribirme</Link>
          </div>
          {/* Growth */}
          <div className="rounded-2xl border border-indigo-300 dark:border-indigo-700 bg-white dark:bg-gray-800 p-8 shadow relative">
            <div className="absolute -top-3 right-6 bg-indigo-600 text-white text-xs px-2 py-1 rounded">Popular</div>
            <h3 className="text-xl font-semibold mb-2">Growth</h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">Hasta 6 aprobadores</p>
            <div className="text-4xl font-bold mb-6">$45<span className="text-base font-medium text-gray-500">/mes</span></div>
            <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-300 mb-6">
              <li>• 6 aprobadores</li>
              <li>• Solicitudes ilimitadas</li>
              <li>• Auditoría avanzada</li>
            </ul>
            <Link href={`/${locale}/subscribe?plan=growth`} className="block text-center w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded px-4 py-2">Suscribirme</Link>
          </div>
          {/* Scale */}
          <div className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 shadow">
            <h3 className="text-xl font-semibold mb-2">Scale</h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">Aprobadores ilimitados</p>
            <div className="text-4xl font-bold mb-6">$65<span className="text-base font-medium text-gray-500">/mes</span></div>
            <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-300 mb-6">
              <li>• Aprobadores ilimitados</li>
              <li>• Solicitudes ilimitadas</li>
              <li>• Integraciones premium</li>
            </ul>
            <Link href={`/${locale}/subscribe?plan=scale`} className="block text-center w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded px-4 py-2">Suscribirme</Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 dark:bg-black text-white py-12">
        <div className="container mx-auto px-4 text-center">
          <div className="flex justify-center items-center space-x-2 mb-4">
            <ShieldCheckIcon className="w-6 h-6 text-indigo-400" />
            <span className="text-xl font-bold">{tCommon('appName')}</span>
          </div>
          <p className="text-gray-400">
            © 2025 SecureApprove. All rights reserved.
          </p>
          <p className="text-gray-500 mt-2">
            Built with ❤️ for Enterprise Security
          </p>
        </div>
      </footer>
    </main>
  );
}

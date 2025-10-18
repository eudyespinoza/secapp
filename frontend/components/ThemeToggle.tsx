'use client';

import { SunIcon, MoonIcon, ComputerDesktopIcon } from '@heroicons/react/24/outline';
import { useTheme } from '@/lib/theme-context';
import { useTranslations } from 'next-intl';
import { Fragment } from 'react';
import { Menu, Transition } from '@headlessui/react';

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const t = useTranslations('theme');

  const tSettings = useTranslations('settings.theme');
  
  const themes = [
    { value: 'light' as const, icon: SunIcon, label: tSettings('light') },
    { value: 'dark' as const, icon: MoonIcon, label: tSettings('dark') },
    { value: 'system' as const, icon: ComputerDesktopIcon, label: tSettings('system') },
  ];

  const currentTheme = themes.find((t) => t.value === theme) || themes[0];
  const CurrentIcon = currentTheme.icon;

  return (
    <Menu as="div" className="relative inline-block text-left">
      <Menu.Button
        className="inline-flex items-center justify-center rounded-lg p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 transition-colors"
        aria-label={t('toggle')}
      >
        <CurrentIcon className="h-5 w-5" />
      </Menu.Button>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items className="absolute right-0 mt-2 w-48 origin-top-right rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
          <div className="py-1">
            {themes.map((themeOption) => {
              const Icon = themeOption.icon;
              return (
                <Menu.Item key={themeOption.value}>
                  {({ active }) => (
                    <button
                      onClick={() => setTheme(themeOption.value)}
                      className={`${
                        active
                          ? 'bg-gray-100 dark:bg-gray-700'
                          : ''
                      } ${
                        theme === themeOption.value
                          ? 'text-indigo-600 dark:text-indigo-400'
                          : 'text-gray-700 dark:text-gray-300'
                      } group flex w-full items-center px-4 py-2 text-sm transition-colors`}
                    >
                      <Icon className="mr-3 h-5 w-5" aria-hidden="true" />
                      {themeOption.label}
                    </button>
                  )}
                </Menu.Item>
              );
            })}
          </div>
        </Menu.Items>
      </Transition>
    </Menu>
  );
}

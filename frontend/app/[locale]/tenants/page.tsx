'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/lib/api-client';
import { authService } from '@/lib/auth-service';

interface Tenant {
  _id: string;
  key: string;
  name: string;
  domains: string[];
  isActive: boolean;
  createdAt: string;
}

export default function TenantsPage({ params }: { params: { locale: string } }) {
  const t = useTranslations('tenants');
  const router = useRouter();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [form, setForm] = useState({ key: '', name: '', domains: '' });

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    if (!currentUser) {
      router.push(`/${params.locale}/auth/login`);
      return;
    }
    if (currentUser.role !== 'superadmin') {
      router.push(`/${params.locale}/dashboard`);
      return;
    }
    loadTenants();
  }, [params.locale, router]);

  const loadTenants = async () => {
    try {
      const res = await apiClient.get<Tenant[]>('/tenants');
      if (res.data) setTenants(res.data);
    } catch (e) {
      console.error('Failed to load tenants', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        key: form.key.trim(),
        name: form.name.trim(),
        domains: form.domains.split(',').map(d => d.trim()).filter(Boolean),
      };
      const res = await apiClient.post<Tenant>('/tenants', payload);
      if (res.error) {
        alert(res.error);
      } else {
        setForm({ key: '', name: '', domains: '' });
        await loadTenants();
      }
    } catch (e) {
      console.error('Failed to create tenant', e);
      alert('Failed to create tenant');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{t('title')}</h1>
            <Link href={`/${params.locale}/dashboard`} className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">← Dashboard</Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{t('list')}</h2>
              </div>
              <div className="p-6">
                {isLoading ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                  </div>
                ) : tenants.length === 0 ? (
                  <p className="text-gray-500 dark:text-gray-400">{t('empty')}</p>
                ) : (
                  <ul className="divide-y divide-gray-200 dark:divide-gray-700">
                    {tenants.map(ten => (
                      <li key={ten._id} className="py-4 flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">{ten.name}</p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">key: {ten.key} • domains: {ten.domains.join(', ') || '—'}</p>
                        </div>
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${ten.isActive ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'}`}>
                          {ten.isActive ? t('active') : t('inactive')}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>

          <div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{t('create')}</h2>
              </div>
              <form className="p-6 space-y-4" onSubmit={handleCreate}>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Key</label>
                  <input value={form.key} onChange={e => setForm({ ...form, key: e.target.value })} className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm" required />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Name</label>
                  <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm" required />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Domains (comma separated)</label>
                  <input value={form.domains} onChange={e => setForm({ ...form, domains: e.target.value })} className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm" placeholder="acme.com, app.acme.com" />
                </div>
                <div className="pt-2">
                  <button type="submit" className="inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-sm font-medium text-white hover:bg-indigo-700">{t('createAction')}</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

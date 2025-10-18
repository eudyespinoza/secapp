'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { apiClient } from '@/lib/api-client';
import { authService } from '@/lib/auth-service';

interface UserItem {
  id: string;
  email: string;
  name?: string;
  role: string;
  isActive: boolean;
}

interface InviteItem {
  id: string;
  email: string;
  role: string;
  token: string;
  expiresAt: string;
  status: string;
}

interface TenantInfo {
  _id: string;
  name: string;
  planId: string;
  seats: number;
  status: string;
}

export default function TeamSettingsPage({ params }: { params: { locale: string } }) {
  const router = useRouter();
  const t = useTranslations('team');
  const [users, setUsers] = useState<UserItem[]>([]);
  const [invites, setInvites] = useState<InviteItem[]>([]);
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('requester');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const current = authService.getCurrentUser();
    if (!current) {
      router.push(`/${params.locale}/auth/login`);
      return;
    }
    loadAll();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [usersRes, invitesRes, tenantRes] = await Promise.all([
        apiClient.get<UserItem[]>('/users'),
        apiClient.get<InviteItem[]>('/users/invites'),
        apiClient.get<TenantInfo>('/tenants/me'),
      ]);
      setUsers(usersRes.data || []);
      setInvites(invitesRes.data || []);
      setTenant(tenantRes.data || null);
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || 'Failed to load team');
    } finally {
      setLoading(false);
    }
  };

  const onInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await apiClient.post('/users/invites', { email, role });
      setEmail('');
      setRole('requester');
      await loadAll();
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || 'Failed to create invite');
    } finally {
      setSubmitting(false);
    }
  };

  const onRevoke = async (id: string) => {
    try {
      await apiClient.delete(`/users/invites/${id}`);
      await loadAll();
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || 'Failed to revoke invite');
    }
  };

  const seatsUsed = users.filter(u => u.isActive).length;
  const seatsFull = tenant ? seatsUsed >= tenant.seats : false;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('title')}</h1>
            <Link href={`/${params.locale}/dashboard`} className="text-sm text-indigo-600 dark:text-indigo-400">← {t('back')}</Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-4 p-3 rounded bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-200">{error}</div>
        )}

        {tenant && (
          <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="text-xs text-gray-500 dark:text-gray-400">{t('plan')}</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-white">{tenant.planId} <span className="text-xs font-normal text-gray-500">({tenant.status})</span></div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="text-xs text-gray-500 dark:text-gray-400">{t('seats')}</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-white">{seatsUsed} / {tenant.seats}</div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="text-xs text-gray-500 dark:text-gray-400">{t('tenant')}</div>
              <div className="text-lg font-semibold text-gray-900 dark:text-white">{tenant.name}</div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{t('users')}</h2>
            </div>
            <div className="p-6">
              {loading ? (
                <div className="text-sm text-gray-500">{t('loading')}</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-600 dark:text-gray-300">
                        <th className="py-2 pr-4">{t('table.name')}</th>
                        <th className="py-2 pr-4">{t('table.email')}</th>
                        <th className="py-2 pr-4">{t('table.role')}</th>
                        <th className="py-2 pr-4">{t('table.status')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map(u => (
                        <tr key={u.id} className="border-t border-gray-100 dark:border-gray-700">
                          <td className="py-2 pr-4">{u.name || '-'}</td>
                          <td className="py-2 pr-4">{u.email}</td>
                          <td className="py-2 pr-4">{u.role}</td>
                          <td className="py-2 pr-4">{u.isActive ? t('active') : t('inactive')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{t('invite.title')}</h2>
            </div>
            <div className="p-6">
              <form onSubmit={onInvite} className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1">{t('invite.email')}</label>
                  <input value={email} onChange={e => setEmail(e.target.value)} type="email" required className="w-full rounded border-gray-300 dark:border-gray-700 dark:bg-gray-900" placeholder="user@company.com" />
                </div>
                <div>
                  <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1">{t('invite.role')}</label>
                  <select value={role} onChange={e => setRole(e.target.value)} className="w-full rounded border-gray-300 dark:border-gray-700 dark:bg-gray-900">
                    <option value="requester">{t('roles.requester')}</option>
                    <option value="approver">{t('roles.approver')}</option>
                    <option value="auditor">{t('roles.auditor')}</option>
                    <option value="tenant_admin">{t('roles.tenant_admin')}</option>
                  </select>
                </div>
                <button type="submit" disabled={submitting || seatsFull} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded px-4 py-2 disabled:opacity-50">
                  {submitting ? t('invite.sending') : (seatsFull ? t('invite.full') : t('invite.send'))}
                </button>
              </form>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">{t('pending')}</h3>
              <div className="space-y-3">
                {invites.length === 0 && (
                  <div className="text-xs text-gray-500">{t('none')}</div>
                )}
                {invites.map(inv => (
                  <div key={inv.id} className="text-sm p-3 rounded border border-gray-200 dark:border-gray-700 flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">{inv.email} <span className="text-xs text-gray-500">({inv.role})</span></div>
                      <div className="text-xs text-gray-500 break-all">{t('link')}: {typeof window !== 'undefined' ? `${window.location.origin}/${params.locale}/auth/invite/${inv.token}` : ''}</div>
                      <div className="text-xs text-gray-500">{t('expires')}: {new Date(inv.expiresAt).toLocaleString()}</div>
                    </div>
                    <button onClick={() => onRevoke(inv.id)} className="text-xs text-red-600 hover:text-red-700">{t('revoke')}</button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { authService } from '@/lib/auth-service';

export default function AcceptInvitePage({ params }: { params: { locale: string; token: string } }) {
  const router = useRouter();
  const [name, setName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Ensure logged out to avoid token conflicts
    authService.logout();
  }, []);

  const onAccept = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await apiClient.post<{ accessToken: string; refreshToken: string; user: { id: string; email: string; role: string } }>(
        '/auth/invite/accept',
        { token: params.token, name }
      );
      if (!res.error && res.data?.accessToken) {
        apiClient.setToken(res.data.accessToken);
        if (typeof window !== 'undefined') {
          localStorage.setItem('refreshToken', res.data.refreshToken);
          localStorage.setItem('user', JSON.stringify(res.data.user));
        }
        router.push(`/${params.locale}/dashboard`);
      } else {
        setError('Unexpected response');
      }
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || 'Failed to accept invite');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
      <form onSubmit={onAccept} className="w-full max-w-md bg-white dark:bg-gray-800 p-6 rounded-lg shadow space-y-4">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Accept Invite</h1>
        {error && <div className="text-sm text-red-600 dark:text-red-400">{error}</div>}
        <label className="block text-sm text-gray-700 dark:text-gray-300">Full name</label>
        <input className="w-full rounded border-gray-300 dark:border-gray-700 dark:bg-gray-900" value={name} onChange={e => setName(e.target.value)} required placeholder="Your full name" />
        <button type="submit" disabled={submitting} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded px-4 py-2 disabled:opacity-50">
          {submitting ? 'Joining...' : 'Join'}
        </button>
      </form>
    </div>
  );
}

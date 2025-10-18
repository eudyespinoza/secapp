'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { authService } from '@/lib/auth-service';
import { apiClient } from '@/lib/api-client';

interface Request {
  id: string;
  requesterId?: string;
  title: string;
  description: string;
  priority: string; // 'low' | 'medium' | 'high' | 'critical'
  status: string;   // 'pending' | 'approved' | 'rejected' | 'cancelled'
  approverId?: string;
  approverComment?: string;
  approvedAt?: string;
  metadata?: any; // may include amount, category, etc.
  expiresAt?: string;
  createdAt: string;
  updatedAt?: string;
}

interface PaginatedRequests {
  data: Request[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export default function RequestsPage({ params }: { params: { locale: string } }) {
  const t = useTranslations('requests');
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [requests, setRequests] = useState<Request[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [page, setPage] = useState<number>(() => {
    const sp = searchParams?.get('page');
    const n = sp ? parseInt(sp, 10) : 1;
    return Number.isFinite(n) && n > 0 ? n : 1;
  });
  const [limit] = useState<number>(10);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [total, setTotal] = useState<number>(0);

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    if (!currentUser) {
      router.push(`/${params.locale}/auth/login`);
      return;
    }
    loadRequests();
  }, [params.locale, router, page, filter]);

  // Keep URL query in sync with page/filter for shareable state
  useEffect(() => {
    const sp = new URLSearchParams(searchParams?.toString());
    sp.set('page', String(page));
    if (filter && filter !== 'all') sp.set('status', filter); else sp.delete('status');
    router.replace(`${pathname}?${sp.toString()}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, filter]);

  const loadRequests = async () => {
    try {
      setIsLoading(true);
      const qp = new URLSearchParams();
      qp.set('page', String(page));
      qp.set('limit', String(limit));
      if (filter !== 'all') qp.set('status', filter);
      const response = await apiClient.get<PaginatedRequests>(`/requests?${qp.toString()}`);
      const list = response.data?.data;
      if (Array.isArray(list)) {
        setRequests(list);
      } else {
        setRequests([]);
      }
      if (response.data) {
        setTotal(response.data.total);
        setTotalPages(response.data.totalPages);
      } else {
        setTotal(0);
        setTotalPages(1);
      }
    } catch (error) {
      console.error('Failed to load requests:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredRequests = requests.filter(req => {
    if (filter === 'all') return true;
    return req.status === filter;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'approved': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'rejected': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-red-600 dark:text-red-400';
      case 'critical': return 'text-red-600 dark:text-red-400';
      case 'high': return 'text-orange-600 dark:text-orange-400';
      case 'medium': return 'text-yellow-600 dark:text-yellow-400';
      case 'low': return 'text-green-600 dark:text-green-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              {t('title')}
            </h1>
            <div className="flex space-x-4">
              <Link
                href={`/${params.locale}/requests/new`}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
              >
                + {t('new.title')}
              </Link>
              <Link
                href={`/${params.locale}/dashboard`}
                className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 flex items-center"
              >
                ← Dashboard
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="mb-6 flex space-x-2">
          <button
            onClick={() => { setPage(1); setFilter('all'); }}
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              filter === 'all'
                ? 'bg-indigo-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            {t('filters.all')}
          </button>
          <button
            onClick={() => { setPage(1); setFilter('pending'); }}
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              filter === 'pending'
                ? 'bg-indigo-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            {t('pending')}
          </button>
          <button
            onClick={() => { setPage(1); setFilter('approved'); }}
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              filter === 'approved'
                ? 'bg-indigo-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            {t('approved')}
          </button>
          <button
            onClick={() => { setPage(1); setFilter('rejected'); }}
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              filter === 'rejected'
                ? 'bg-indigo-600 text-white'
                : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            {t('rejected')}
          </button>
        </div>

        {/* Requests List */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          </div>
        ) : filteredRequests.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
            <p className="text-gray-500 dark:text-gray-400">{t('noRequests')}</p>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200 dark:divide-gray-700">
              {filteredRequests.map((request) => {
                const amount = typeof request.metadata?.amount === 'number' ? request.metadata.amount as number : null;
                const category = typeof request.metadata?.category === 'string' ? request.metadata.category as string : null;
                return (
                <li key={request.id}>
                  <Link
                    href={`/${params.locale}/requests/${request.id}`}
                    className="block hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    <div className="px-4 py-4 sm:px-6">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400 truncate">
                            {request.title}
                          </p>
                          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
                            {request.description}
                          </p>
                        </div>
                        <div className="ml-4 flex-shrink-0 flex items-center space-x-4">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(request.status)}`}>
                            {t(`status.${request.status}`)}
                          </span>
                          {amount !== null && (
                            <span className="text-sm font-medium text-gray-900 dark:text-white">
                              ${amount.toFixed(2)}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="mt-2 sm:flex sm:justify-between">
                        <div className="sm:flex space-x-4">
                          <p className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                            {category && <span className="capitalize">{category}</span>}
                          </p>
                          <p className={`flex items-center text-sm font-medium ${getPriorityColor(request.priority)}`}>
                            {t(`new.priorities.${request.priority}`)}
                          </p>
                        </div>
                        <div className="mt-2 flex items-center text-sm text-gray-500 dark:text-gray-400 sm:mt-0">
                          <p>
                            {new Date(request.createdAt).toLocaleDateString(params.locale, {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            })}
                          </p>
                        </div>
                      </div>
                    </div>
                  </Link>
                </li>
              );})}
            </ul>
            {/* Pagination controls */}
            <div className="px-4 py-3 flex items-center justify-between border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
              <div className="flex-1 flex justify-between sm:hidden">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium rounded-md ${page <= 1 ? 'text-gray-400 dark:text-gray-500 border-gray-200 dark:border-gray-700' : 'text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'}`}
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages || p + 1, (totalPages || 1)))}
                  disabled={page >= (totalPages || 1)}
                  className={`ml-3 relative inline-flex items-center px-4 py-2 border text-sm font-medium rounded-md ${page >= (totalPages || 1) ? 'text-gray-400 dark:text-gray-500 border-gray-200 dark:border-gray-700' : 'text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'}`}
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  <span className="font-medium">{total}</span> items • Page <span className="font-medium">{page}</span> of <span className="font-medium">{totalPages || 1}</span>
                </p>
                <div className="inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className={`relative inline-flex items-center px-3 py-2 border text-sm font-medium rounded-l-md ${page <= 1 ? 'text-gray-400 dark:text-gray-500 border-gray-200 dark:border-gray-700' : 'text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'}`}
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min((totalPages || 1), p + 1))}
                    disabled={page >= (totalPages || 1)}
                    className={`relative inline-flex items-center px-3 py-2 border text-sm font-medium rounded-r-md ${page >= (totalPages || 1) ? 'text-gray-400 dark:text-gray-500 border-gray-200 dark:border-gray-700' : 'text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'}`}
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

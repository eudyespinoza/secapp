'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authService } from '@/lib/auth-service';
import { apiClient } from '@/lib/api-client';

type CreatedByRef =
  | string
  | {
      _id: string;
      name?: string;
      email?: string;
    };

interface Request {
  _id: string;
  title: string;
  description: string;
  category: string;
  amount: number;
  priority: string;
  status: string;
  createdBy: CreatedByRef;
  approvedBy?: {
    name: string;
    email: string;
    approvedAt: string;
  };
  rejectedBy?: {
    name: string;
    email: string;
    rejectedAt: string;
    reason: string;
  };
  createdAt: string;
  updatedAt: string;
}

export default function RequestDetailPage({ params }: { params: { locale: string; id: string } }) {
  const t = useTranslations('requests');
  const router = useRouter();
  const [request, setRequest] = useState<Request | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const formatAmount = (val: any) => {
    const num = typeof val === 'number' ? val : (val != null ? Number(val) : NaN);
    if (!isFinite(num)) return '-';
    return `$${num.toFixed(2)}`;
  };

  useEffect(() => {
    const user = authService.getCurrentUser();
    if (!user) {
      router.push(`/${params.locale}/auth/login`);
      return;
    }
    setCurrentUser(user);
    loadRequest();
  }, [params.id, params.locale, router]);

  const loadRequest = async () => {
    try {
      const response = await apiClient.get<Request>(`/requests/${params.id}`);
      if (response.data) {
        setRequest(response.data);
      }
    } catch (error) {
      console.error('Failed to load request:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = async () => {
    setIsProcessing(true);
    try {
      const response = await apiClient.put(`/requests/${params.id}/approve`, {});
      if (response.error) {
        alert(response.error);
      } else {
        await loadRequest();
        setShowApproveModal(false);
      }
    } catch (error) {
      console.error('Failed to approve request:', error);
      alert('Failed to approve request');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      alert('Please provide a reason for rejection');
      return;
    }
    
    setIsProcessing(true);
    try {
      const response = await apiClient.put(`/requests/${params.id}/reject`, {
        reason: rejectReason,
      });
      if (response.error) {
        alert(response.error);
      } else {
        await loadRequest();
        setShowRejectModal(false);
        setRejectReason('');
      }
    } catch (error) {
      console.error('Failed to reject request:', error);
      alert('Failed to reject request');
    } finally {
      setIsProcessing(false);
    }
  };

  const createdById = request && (typeof request.createdBy === 'string' ? request.createdBy : request.createdBy?._id);
  const createdByName = request && (typeof request.createdBy === 'object' ? (request.createdBy.name || request.createdBy.email || createdById) : createdById);
  const createdByEmail = request && (typeof request.createdBy === 'object' ? request.createdBy.email : undefined);

  const canApprove = !!(currentUser && request && 
    request.status === 'pending' && 
    (currentUser.role === 'approver' || currentUser.role === 'tenant_admin' || currentUser.role === 'superadmin') &&
    createdById && currentUser.id !== createdById);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'approved': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'rejected': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 dark:text-gray-400">Request not found</p>
          <Link href={`/${params.locale}/requests`} className="text-indigo-600 hover:text-indigo-500 mt-4 inline-block">
            ← Back to requests
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              {t('details.title')}
            </h1>
            <Link
              href={`/${params.locale}/requests`}
              className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
            >
              ← {t('backToList')}
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
          {/* Header with status and actions */}
          <div className="px-4 py-5 sm:px-6 border-b border-gray-200 dark:border-gray-700">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
                  {request.title}
                </h3>
                <p className="mt-1 max-w-2xl text-sm text-gray-500 dark:text-gray-400">
                  {t('details.requestedBy')}: {createdByName}
                </p>
              </div>
              <span className={`px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(request.status)}`}>
                {t(`status.${request.status}`)}
              </span>
            </div>
            
            {canApprove && (
              <div className="mt-4 flex space-x-3">
                <button
                  onClick={() => setShowApproveModal(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
                >
                  ✓ {t('details.actions.approve')}
                </button>
                <button
                  onClick={() => setShowRejectModal(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
                >
                  ✗ {t('details.actions.reject')}
                </button>
              </div>
            )}
          </div>

          {/* Details */}
          <div className="px-4 py-5 sm:p-6">
            <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('new.fields.description')}</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">{request.description}</dd>
              </div>

              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('new.fields.category')}</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white capitalize">{request.category}</dd>
              </div>

              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('new.fields.amount')}</dt>
                <dd className="mt-1 text-sm font-semibold text-gray-900 dark:text-white">{formatAmount(request.amount)}</dd>
              </div>

              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('new.fields.priority')}</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">{t(`new.priorities.${request.priority}`)}</dd>
              </div>

              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('details.requestedAt')}</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                  {new Date(request.createdAt).toLocaleString(params.locale)}
                </dd>
              </div>

              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Email</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">{createdByEmail || '-'}</dd>
              </div>

              {request.approvedBy && (
                <>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('details.approvedBy')}</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white">{request.approvedBy.name}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Fecha de aprobación</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                      {new Date(request.approvedBy.approvedAt).toLocaleString(params.locale)}
                    </dd>
                  </div>
                </>
              )}

              {request.rejectedBy && (
                <>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('details.rejectedBy')}</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white">{request.rejectedBy.name}</dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('details.reason')}</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white">{request.rejectedBy.reason}</dd>
                  </div>
                </>
              )}
            </dl>
          </div>
        </div>
      </main>

      {/* Approve Modal */}
      {showApproveModal && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowApproveModal(false)}></div>
            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
                  {t('details.actions.approve')} Request
                </h3>
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  Are you sure you want to approve this request for ${request.amount.toFixed(2)}?
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  onClick={handleApprove}
                  disabled={isProcessing}
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-green-600 text-base font-medium text-white hover:bg-green-700 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
                >
                  {isProcessing ? 'Processing...' : 'Approve'}
                </button>
                <button
                  onClick={() => setShowApproveModal(false)}
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-800 text-base font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowRejectModal(false)}></div>
            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
                  {t('details.actions.reject')} Request
                </h3>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('details.reason')}
                </label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  rows={4}
                  className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                  placeholder="Explain why you are rejecting this request..."
                />
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  onClick={handleReject}
                  disabled={isProcessing}
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
                >
                  {isProcessing ? 'Processing...' : 'Reject'}
                </button>
                <button
                  onClick={() => setShowRejectModal(false)}
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-800 text-base font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

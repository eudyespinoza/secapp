'use client';

import { useState, useEffect, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authService } from '@/lib/auth-service';
import { apiClient } from '@/lib/api-client';

export default function NewRequestPage({ params }: { params: { locale: string } }) {
  const t = useTranslations('requests.new');
  const router = useRouter();
  type Category = 'expense' | 'purchase' | 'travel' | 'contract' | 'document' | 'other';
  type ExtraKey = 'vendor' | 'costCenter' | 'expenseCategory' | 'receiptRef' | 'destination' | 'startDate' | 'endDate' | 'documentId' | 'reason';
  type BaseRequired = 'title' | 'description' | 'amount' | 'priority';
  type CategoryCfg = { showAmount: boolean; required: Array<BaseRequired | ExtraKey>; extras: ExtraKey[] };
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: 'expense' as Category, // expense | purchase | travel | contract | document | other
    amount: '',
    priority: 'medium',
    vendor: '',
    costCenter: '',
    expenseCategory: '',
    receiptRef: '',
    destination: '',
    startDate: '',
    endDate: '',
    documentId: '',
    reason: '',
  });

  const categoryConfig: Record<Category, CategoryCfg> = useMemo(() => ({
    expense: {
      showAmount: true,
      required: ['title', 'description', 'amount', 'priority', 'expenseCategory', 'receiptRef'],
      extras: ['expenseCategory', 'receiptRef', 'costCenter']
    },
    purchase: {
      showAmount: true,
      required: ['title', 'description', 'amount', 'priority', 'vendor', 'costCenter'],
      extras: ['vendor', 'costCenter']
    },
    travel: {
      showAmount: true,
      required: ['title', 'description', 'amount', 'priority', 'destination', 'startDate', 'endDate'],
      extras: ['destination', 'startDate', 'endDate']
    },
    contract: {
      showAmount: false,
      required: ['title', 'description', 'priority', 'vendor', 'reason'],
      extras: ['vendor', 'reason']
    },
    document: {
      showAmount: false,
      required: ['title', 'description', 'priority', 'documentId', 'reason'],
      extras: ['documentId', 'reason']
    },
    other: {
      showAmount: false,
      required: ['title', 'description', 'priority'],
      extras: []
    }
  }), []);

  const currentCfg: CategoryCfg = categoryConfig[formData.category];

  useEffect(() => {
    // Check authentication
    const currentUser = authService.getCurrentUser();
    if (!currentUser) {
      router.push(`/${params.locale}/auth/login`);
    }
  }, [params.locale, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      // Basic front-end required validation per type
      const missing = currentCfg.required.filter((key) => {
        const val = (formData as any)[key];
        return val === undefined || val === null || String(val).trim() === '';
      });
      if (missing.length) {
        setError(`Completa los campos requeridos: ${missing.join(', ')}`);
        setIsLoading(false);
        return;
      }

      const payload: any = {
        title: formData.title,
        description: formData.description,
        priority: formData.priority,
        metadata: {
          category: formData.category,
        },
      };

      if (currentCfg.showAmount) {
        const parsed = parseFloat(formData.amount);
        if (Number.isNaN(parsed) || parsed < 0) {
          setError('Monto inválido');
          setIsLoading(false);
          return;
        }
        payload.metadata.amount = parsed;
      }

      // attach extras
      currentCfg.extras.forEach((k) => {
        const v = (formData as any)[k];
        if (v) payload.metadata[k] = v;
      });

      const response = await apiClient.post('/requests', payload);

      if (response.error) {
        setError(response.error);
      } else {
        // Redirect to dashboard on success
        router.push(`/${params.locale}/dashboard`);
      }
    } catch (err: any) {
      console.error('Create request error:', err);
      setError(err.message || 'Failed to create request. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              {t('title')}
            </h1>
            <Link
              href={`/${params.locale}/dashboard`}
              className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
            >
              ← {t('backToDashboard')}
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {error && (
              <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
                <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
              </div>
            )}

            <div>
              <label htmlFor="title" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('fields.title')}
              </label>
              <input
                type="text"
                name="title"
                id="title"
                required
                value={formData.title}
                onChange={handleChange}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                placeholder={t('placeholders.title')}
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('fields.description')}
              </label>
              <textarea
                name="description"
                id="description"
                rows={4}
                required
                value={formData.description}
                onChange={handleChange}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                placeholder={t('placeholders.description')}
              />
            </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label htmlFor="category" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('fields.category')}
                </label>
                <select
                  name="category"
                  id="category"
                  value={formData.category}
                  onChange={handleChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                >
                  <option value="expense">{t('categories.expense')}</option>
                  <option value="purchase">{t('categories.purchase')}</option>
                  <option value="travel">{t('categories.travel')}</option>
                  <option value="contract">{t('categories.contract')}</option>
                    <option value="document">{t('categories.document')}</option>
                  <option value="other">{t('categories.other')}</option>
                </select>
              </div>
              {currentCfg.showAmount && (
                <div>
                  <label htmlFor="amount" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    {t('fields.amount')}
                  </label>
                  <input
                    type="number"
                    name="amount"
                    id="amount"
                    step="0.01"
                    min="0"
                    value={formData.amount}
                    onChange={handleChange}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                    placeholder="0.00"
                  />
                </div>
              )}

              <div>
                <label htmlFor="priority" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('fields.priority')}
                </label>
                <select
                  name="priority"
                  id="priority"
                  value={formData.priority}
                  onChange={handleChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                >
                  <option value="low">{t('priorities.low')}</option>
                  <option value="medium">{t('priorities.medium')}</option>
                  <option value="high">{t('priorities.high')}</option>
                  <option value="urgent">{t('priorities.urgent')}</option>
                </select>
              </div>
            </div>

            {/* Extra fields based on category */}
            {currentCfg.extras.includes('vendor') && (
              <div>
                <label htmlFor="vendor" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('fields.extra.vendor')}
                </label>
                <input
                  type="text"
                  name="vendor"
                  id="vendor"
                  value={formData.vendor}
                  onChange={handleChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                />
              </div>
            )}
            {currentCfg.extras.includes('costCenter') && (
              <div>
                <label htmlFor="costCenter" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('fields.extra.costCenter')}
                </label>
                <input
                  type="text"
                  name="costCenter"
                  id="costCenter"
                  value={formData.costCenter}
                  onChange={handleChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                />
              </div>
            )}
            {currentCfg.extras.includes('expenseCategory') && (
              <div>
                <label htmlFor="expenseCategory" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('fields.extra.expenseCategory')}
                </label>
                <input
                  type="text"
                  name="expenseCategory"
                  id="expenseCategory"
                  value={formData.expenseCategory}
                  onChange={handleChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                />
              </div>
            )}
            {currentCfg.extras.includes('receiptRef') && (
              <div>
                <label htmlFor="receiptRef" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('fields.extra.receiptRef')}
                </label>
                <input
                  type="text"
                  name="receiptRef"
                  id="receiptRef"
                  value={formData.receiptRef}
                  onChange={handleChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                />
              </div>
            )}
            {currentCfg.extras.includes('destination') && (
              <div>
                <label htmlFor="destination" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('fields.extra.destination')}
                </label>
                <input
                  type="text"
                  name="destination"
                  id="destination"
                  value={formData.destination}
                  onChange={handleChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                />
              </div>
            )}
            {currentCfg.extras.includes('startDate') && (
              <div>
                <label htmlFor="startDate" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('fields.extra.startDate')}
                </label>
                <input
                  type="date"
                  name="startDate"
                  id="startDate"
                  value={formData.startDate}
                  onChange={handleChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                />
              </div>
            )}
            {currentCfg.extras.includes('endDate') && (
              <div>
                <label htmlFor="endDate" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('fields.extra.endDate')}
                </label>
                <input
                  type="date"
                  name="endDate"
                  id="endDate"
                  value={formData.endDate}
                  onChange={handleChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                />
              </div>
            )}
            {currentCfg.extras.includes('documentId') && (
              <div>
                <label htmlFor="documentId" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('fields.extra.documentId')}
                </label>
                <input
                  type="text"
                  name="documentId"
                  id="documentId"
                  value={formData.documentId}
                  onChange={handleChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                />
              </div>
            )}
            {currentCfg.extras.includes('reason') && (
              <div>
                <label htmlFor="reason" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('fields.extra.reason')}
                </label>
                <textarea
                  name="reason"
                  id="reason"
                  rows={3}
                  value={formData.reason}
                  onChange={handleChange}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white sm:text-sm"
                />
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Link
                href={`/${params.locale}/dashboard`}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                {t('buttons.cancel')}
              </Link>
              <button
                type="submit"
                disabled={isLoading}
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? t('buttons.creating') : t('buttons.create')}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}

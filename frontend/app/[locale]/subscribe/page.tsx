'use client';

import { useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiClient } from '@/lib/api-client';

type PlanId = 'starter' | 'growth' | 'scale';

const PLANS: Array<{
  id: PlanId;
  name: string;
  price: number; // USD / mes
  approvers: string;
  featured?: boolean;
}> = [
  { id: 'starter', name: 'Starter', price: 25, approvers: 'Hasta 2 aprobadores' },
  { id: 'growth', name: 'Growth', price: 45, approvers: 'Hasta 6 aprobadores', featured: true },
  { id: 'scale', name: 'Scale', price: 65, approvers: 'Aprobadores ilimitados' },
];

export default function SubscribePage({ params }: { params: { locale: string } }) {
  const router = useRouter();
  const sp = useSearchParams();
  const planFromQuery = (sp.get('plan') as PlanId) || 'growth';
  const [selected, setSelected] = useState<PlanId>(planFromQuery);
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedPlan = useMemo(() => PLANS.find(p => p.id === selected)!, [selected]);

  const onCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.post('/billing/checkout', {
        planId: selected,
        seats: 10, // Asignamos 10 asientos por defecto; ajustable si lo deseas
        customerEmail: email,
        successUrl: `${window.location.origin}/${params.locale}/settings/team?status=success`,
        failureUrl: `${window.location.origin}/${params.locale}/settings/team?status=failure`,
      });
      const pref: any = res?.data ?? res;
      if (pref?.init_point) {
        window.location.href = pref.init_point as string;
        return;
      }
      if (pref?.sandbox_init_point) {
        window.location.href = pref.sandbox_init_point as string;
        return;
      }
      if (pref?.id) {
        window.location.href = `https://www.mercadopago.com/checkout/v1/redirect?pref_id=${pref.id}`;
        return;
      }
      setError('No se pudo iniciar el pago');
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || 'Error iniciando pago');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-5xl mx-auto px-4 py-10">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">Elige tu plan</h1>

        {/* Planes */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {PLANS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setSelected(p.id)}
              className={`text-left rounded-2xl p-6 border transition-all shadow-sm ${
                selected === p.id
                  ? 'border-indigo-500 ring-2 ring-indigo-300 dark:ring-indigo-700'
                  : 'border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-700'
              } bg-white dark:bg-gray-800`}
            >
              {p.featured && (
                <span className="inline-block mb-2 text-xs px-2 py-0.5 bg-indigo-600 text-white rounded">Popular</span>
              )}
              <div className="text-lg font-semibold mb-1">{p.name}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-4">{p.approvers}</div>
              <div className="text-4xl font-bold">${p.price}<span className="text-base font-medium text-gray-500">/mes</span></div>
            </button>
          ))}
        </div>

        {/* Formulario */}
        <form onSubmit={onCheckout} className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div className="md:col-span-2">
              <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1">Email</label>
              <input
                type="email"
                required
                className="w-full rounded border-gray-300 dark:border-gray-700 dark:bg-gray-900"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="tu@empresa.com"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Se usará para asociar tu tenant y enviarte el recibo</p>
            </div>
            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded px-4 py-2 disabled:opacity-50"
              >
                {loading ? 'Redirigiendo…' : `Pagar ${selectedPlan?.name} ($${selectedPlan?.price}/mes)`}
              </button>
            </div>
          </div>
          {error && <div className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</div>}
        </form>
      </div>
    </div>
  );
}

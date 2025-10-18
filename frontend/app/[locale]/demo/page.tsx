'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

type Step = 'create' | 'notify' | 'approve' | 'audited' | 'done';

export default function DemoPage({ params }: { params: { locale: string } }) {
  const [step, setStep] = useState<Step>('create');

  useEffect(() => {
    const order: Step[] = ['create', 'notify', 'approve', 'audited', 'done'];
    let i = 0;
    const id = setInterval(() => {
      i = (i + 1) % order.length;
      setStep(order[i]);
    }, 2000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-6xl mx-auto px-4 py-6 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Demo del Proceso de Aprobación</h1>
          <Link href={`/${params.locale}`} className="text-sm text-indigo-600 dark:text-indigo-400">← Volver</Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Create Request */}
          <div className={`rounded-2xl p-6 border ${step === 'create' ? 'border-indigo-500 ring-2 ring-indigo-300 dark:ring-indigo-700' : 'border-gray-200 dark:border-gray-700'} bg-white dark:bg-gray-800 transition-all`}>
            <div className="text-sm text-gray-500 dark:text-gray-400">Paso 1</div>
            <div className="text-xl font-semibold mb-2">Crear solicitud</div>
            <p className="text-sm text-gray-600 dark:text-gray-300">El solicitante carga el detalle y envía para aprobación.</p>
            <div className={`mt-4 h-2 rounded bg-gray-200 dark:bg-gray-700 overflow-hidden`}>
              <div className={`h-2 bg-indigo-500 transition-all ${step === 'create' ? 'w-full animate-pulse' : 'w-0'}`}></div>
            </div>
          </div>

          {/* Notify Approvers */}
          <div className={`rounded-2xl p-6 border ${step === 'notify' ? 'border-indigo-500 ring-2 ring-indigo-300 dark:ring-indigo-700' : 'border-gray-200 dark:border-gray-700'} bg-white dark:bg-gray-800 transition-all`}>
            <div className="text-sm text-gray-500 dark:text-gray-400">Paso 2</div>
            <div className="text-xl font-semibold mb-2">Notificar aprobadores</div>
            <p className="text-sm text-gray-600 dark:text-gray-300">Los aprobadores reciben notificación push/email en tiempo real.</p>
            <div className={`mt-4 h-2 rounded bg-gray-200 dark:bg-gray-700 overflow-hidden`}>
              <div className={`h-2 bg-indigo-500 transition-all ${step === 'notify' ? 'w-full animate-pulse' : 'w-0'}`}></div>
            </div>
          </div>

          {/* Approve */}
          <div className={`rounded-2xl p-6 border ${step === 'approve' ? 'border-indigo-500 ring-2 ring-indigo-300 dark:ring-indigo-700' : 'border-gray-200 dark:border-gray-700'} bg-white dark:bg-gray-800 transition-all`}>
            <div className="text-sm text-gray-500 dark:text-gray-400">Paso 3</div>
            <div className="text-xl font-semibold mb-2">Aprobar con biometría</div>
            <p className="text-sm text-gray-600 dark:text-gray-300">El aprobador confirma con huella/FaceID (WebAuthn, sin contraseñas).</p>
            <div className={`mt-4 h-2 rounded bg-gray-200 dark:bg-gray-700 overflow-hidden`}>
              <div className={`h-2 bg-green-500 transition-all ${step === 'approve' ? 'w-full animate-pulse' : 'w-0'}`}></div>
            </div>
          </div>

          {/* Audited */}
          <div className={`rounded-2xl p-6 border ${step === 'audited' ? 'border-indigo-500 ring-2 ring-indigo-300 dark:ring-indigo-700' : 'border-gray-200 dark:border-gray-700'} bg-white dark:bg-gray-800 transition-all`}>
            <div className="text-sm text-gray-500 dark:text-gray-400">Paso 4</div>
            <div className="text-xl font-semibold mb-2">Auditado</div>
            <p className="text-sm text-gray-600 dark:text-gray-300">Registro inmutable con timestamp, usuario y decisión.</p>
            <div className={`mt-4 h-2 rounded bg-gray-200 dark:bg-gray-700 overflow-hidden`}>
              <div className={`h-2 bg-purple-500 transition-all ${step === 'audited' ? 'w-full animate-pulse' : 'w-0'}`}></div>
            </div>
          </div>
        </div>

        {/* Connector animation */}
        <div className="mt-10 hidden md:block">
          <div className="h-1 bg-gradient-to-r from-indigo-300 via-green-300 to-purple-300 rounded-full animate-pulse"></div>
        </div>

        {/* Final CTA */}
        <div className="mt-12 text-center">
          <p className="text-gray-600 dark:text-gray-300 mb-4">¿Listo para probarlo?</p>
          <Link href={`/${params.locale}/subscribe`} className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white rounded px-6 py-3">
            Ver planes
          </Link>
        </div>
      </main>
    </div>
  );
}

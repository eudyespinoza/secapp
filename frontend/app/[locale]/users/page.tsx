'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authService } from '@/lib/auth-service';
import { apiClient } from '@/lib/api-client';

type Role = 'superadmin' | 'tenant_admin' | 'requester' | 'approver' | 'auditor';

const ROLE_OPTIONS: Role[] = ['requester', 'approver', 'auditor', 'tenant_admin'];

interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  isActive: boolean;
  createdAt: string;
  lastLoginAt?: string;
}

export default function UsersPage({ params }: { params: { locale: string } }) {
  const t = useTranslations('users');
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [tenantSeats, setTenantSeats] = useState<{ used: number; total: number } | null>(null);
  const [approverInfo, setApproverInfo] = useState<{ used: number; limit: number | null } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);

  useEffect(() => {
    const user = authService.getCurrentUser();
    if (!user) {
      router.push(`/${params.locale}/auth/login`);
      return;
    }
    setCurrentUser(user);
    loadUsersAndSeats();
  }, [params.locale, router]);

  const loadUsersAndSeats = async () => {
    try {
      const [usersRes, tenantRes] = await Promise.all([
        apiClient.get<User[]>('/users'),
        apiClient.get<any>('/tenants/me'),
      ]);
      setUsers(usersRes.data || []);
      const total = tenantRes.data?.seats ?? 0;
      const used = (usersRes.data || []).filter(u => u.isActive).length;
      setTenantSeats({ used, total });
      const approvers = (usersRes.data || []).filter(u => u.role === 'approver' && u.isActive).length;
      const limit = typeof tenantRes.data?.approverLimit === 'number' ? tenantRes.data.approverLimit : null;
      setApproverInfo({ used: approvers, limit });
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateRole = async (userId: string, newRole: string) => {
    try {
      // Client-side guard for approver limit
      if (newRole === 'approver' && approverInfo && approverInfo.limit !== null && approverInfo.used >= approverInfo.limit) {
        alert('Se alcanzó el límite de aprobadores para tu plan');
        return;
      }
      const response = await apiClient.put(`/users/${userId}`, { role: newRole });
      if (response.error) {
        alert(response.error);
      } else {
        await loadUsersAndSeats();
        setShowEditModal(false);
        setEditingUser(null);
      }
    } catch (error) {
      console.error('Failed to update user:', error);
      alert('Failed to update user role');
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'superadmin': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'tenant_admin': return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200';
      case 'approver': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'requester': return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
      case 'auditor': return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const canEditUser = (user: User) => {
    // superadmin puede editar cualquier usuario; tenant_admin puede editar usuarios de su tenant (asumido en backend)
    return currentUser && (currentUser.role === 'superadmin' || currentUser.role === 'tenant_admin' || currentUser.id === user.id);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                {t('title')}
              </h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Gestiona roles y permisos de usuarios
              </p>
            </div>
            <Link
              href={`/${params.locale}/dashboard`}
              className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
            >
              ← Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {tenantSeats && (
          <div className="mb-6 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
            <div className="text-sm text-amber-800 dark:text-amber-200">
              Seats: <strong>{tenantSeats.used}</strong> / <strong>{tenantSeats.total}</strong>
            </div>
          </div>
        )}
        {approverInfo && (
          <div className="mb-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="text-sm text-blue-800 dark:text-blue-200">
              Aprobadores: <strong>{approverInfo.used}</strong> / <strong>{approverInfo.limit ?? 'ilimitado'}</strong>
            </div>
          </div>
        )}
        {/* Info Box */}
        <div className="mb-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                Roles disponibles:
              </h3>
              <div className="mt-2 text-sm text-blue-700 dark:text-blue-300">
                <ul className="list-disc list-inside space-y-1">
                  <li><strong>User:</strong> Puede crear solicitudes</li>
                  <li><strong>Approver:</strong> Puede aprobar/rechazar solicitudes de otros</li>
                  <li><strong>Admin:</strong> Acceso completo al sistema</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Users Table */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-lg">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    {t('table.name')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    {t('table.email')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    {t('table.role')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Último acceso
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    {t('table.actions')}
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {user.name}
                        {currentUser?.id === user.id && (
                          <span className="ml-2 text-xs text-indigo-600 dark:text-indigo-400">(Tú)</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500 dark:text-gray-400">{user.email}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getRoleBadgeColor(user.role)}`}>
                        {t(`roles.${user.role}`)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {user.lastLoginAt ? new Date(user.lastLoginAt).toLocaleDateString() : 'Nunca'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {canEditUser(user) && (
                        <button
                          onClick={() => {
                            setEditingUser(user);
                            setShowEditModal(true);
                          }}
                          className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300"
                        >
                          Cambiar rol
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {/* Edit Role Modal */}
      {showEditModal && editingUser && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={() => setShowEditModal(false)}></div>
            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
                  Cambiar rol de {editingUser.name}
                </h3>
                <div className="space-y-3">
                  {ROLE_OPTIONS.map((role) => (
                    <label key={role} className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 dark:border-gray-600">
                      <input
                        type="radio"
                        name="role"
                        value={role}
                        checked={editingUser.role === role}
                        onChange={(e) => setEditingUser({ ...editingUser, role: e.target.value as Role })}
                        disabled={!!(role === 'approver' && approverInfo && approverInfo.limit !== null && approverInfo.used >= approverInfo.limit && editingUser.role !== 'approver')}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div className="ml-3">
                        <span className="block text-sm font-medium text-gray-900 dark:text-white">
                          {t(`roles.${role}`)}
                        </span>
                        <span className="block text-xs text-gray-500 dark:text-gray-400">
                          {role === 'requester' && 'Puede crear solicitudes'}
                          {role === 'approver' && 'Puede aprobar/rechazar solicitudes'}
                          {role === 'auditor' && 'Puede revisar registros y auditoría'}
                          {role === 'tenant_admin' && 'Administra usuarios y configuración del tenant'}
                        </span>
                        {role === 'approver' && approverInfo && approverInfo.limit !== null && approverInfo.used >= approverInfo.limit && editingUser.role !== 'approver' && (
                          <span className="block text-xs text-red-600 dark:text-red-400 mt-1">Límite de aprobadores alcanzado por tu plan</span>
                        )}
                      </div>
                    </label>
                  ))}
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  onClick={() => handleUpdateRole(editingUser.id, editingUser.role)}
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Guardar cambios
                </button>
                <button
                  onClick={() => setShowEditModal(false)}
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-800 text-base font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

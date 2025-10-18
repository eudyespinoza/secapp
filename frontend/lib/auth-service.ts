import { apiClient } from './api-client';
import {
  startRegistration,
  startAuthentication,
} from '@simplewebauthn/browser';

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
}

export interface AuthResponse {
  user: User;
  accessToken: string;
  refreshToken: string;
  message?: string;
}

export class AuthService {
  private ensureLocalhost() {
    if (typeof window !== 'undefined' && window.location.hostname === '127.0.0.1') {
      const target = `http://localhost:3000${window.location.pathname}${window.location.search}`;
      // Redirect immediately; throw to stop current flow safely
      window.location.replace(target);
      throw new Error('Redirecting to localhost for WebAuthn compatibility');
    }
  }

  async register(name: string, email: string): Promise<{ id: string; name: string; email: string; role: string }> {
    const response = await apiClient.post<{ id: string; name: string; email: string; role: string }>('/auth/register', { name, email });
    
    if (response.error || !response.data) {
      throw new Error(response.error || 'Registration failed');
    }

    return response.data;
  }

  async startRegistration(userId: string): Promise<void> {
    // Ensure host is localhost (WebAuthn does not allow 127.0.0.1)
    this.ensureLocalhost();
    // Get registration options from server
    const optionsResponse = await apiClient.post<any>('/auth/register/options', { userId });
    
    if (optionsResponse.error || !optionsResponse.data) {
      throw new Error(optionsResponse.error || 'Failed to get registration options');
    }

    const options = optionsResponse.data;

    // Start WebAuthn registration ceremony
    let attResp;
    try {
      attResp = await startRegistration(options as any);
    } catch (error: any) {
      throw new Error('WebAuthn registration failed: ' + error.message);
    }

    // Send registration response to server for verification
    const verificationResponse = await apiClient.post<AuthResponse>('/auth/register/verify', {
      userId,
      response: attResp,
    });

    if (verificationResponse.error || !verificationResponse.data) {
      throw new Error(verificationResponse.error || 'Registration verification failed');
    }

    // Store tokens
    const { accessToken, refreshToken } = verificationResponse.data;
    apiClient.setToken(accessToken);
    
    if (typeof window !== 'undefined') {
      localStorage.setItem('refreshToken', refreshToken);
      localStorage.setItem('user', JSON.stringify(verificationResponse.data.user));
    }

    return;
  }

  async startLogin(email: string): Promise<{ user: User }> {
    // Ensure host is localhost (WebAuthn does not allow 127.0.0.1)
    this.ensureLocalhost();
    // Get authentication options from server
    const optionsResponse = await apiClient.post<{ options: any; userId: string }>('/auth/login/options', { email });
    
    if (optionsResponse.error || !optionsResponse.data) {
      throw new Error(optionsResponse.error || 'Failed to get authentication options');
    }

    const { options, userId } = optionsResponse.data;

    // Start WebAuthn authentication ceremony
    let asseResp;
    try {
      asseResp = await startAuthentication(options as any);
    } catch (error: any) {
      throw new Error('WebAuthn authentication failed: ' + error.message);
    }

    // Send authentication response to server for verification
    const verificationResponse = await apiClient.post<AuthResponse>('/auth/login/verify', {
      userId,
      response: asseResp,
    });

    if (verificationResponse.error || !verificationResponse.data) {
      throw new Error(verificationResponse.error || 'Authentication verification failed');
    }

    // Store tokens
    const { accessToken, refreshToken, user } = verificationResponse.data;
    apiClient.setToken(accessToken);
    
    if (typeof window !== 'undefined') {
      localStorage.setItem('refreshToken', refreshToken);
      localStorage.setItem('user', JSON.stringify(user));
    }

    return { user };
  }

  async logout(): Promise<void> {
    const user = this.getCurrentUser();
    
    if (user) {
      await apiClient.post('/auth/logout', { userId: user.id });
    }

    apiClient.clearToken();
    
    if (typeof window !== 'undefined') {
      localStorage.removeItem('user');
    }
  }

  async refreshToken(): Promise<boolean> {
    if (typeof window === 'undefined') return false;

    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) return false;

    const response = await apiClient.post<{ accessToken: string; refreshToken: string }>('/auth/refresh', {
      refreshToken,
    });

    if (response.error || !response.data) {
      this.logout();
      return false;
    }

    apiClient.setToken(response.data.accessToken);
    localStorage.setItem('refreshToken', response.data.refreshToken);

    return true;
  }

  getCurrentUser(): User | null {
    if (typeof window === 'undefined') return null;

    const userStr = localStorage.getItem('user');
    if (!userStr) return null;

    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }

  isAuthenticated(): boolean {
    if (typeof window === 'undefined') return false;

    const token = localStorage.getItem('accessToken');
    const user = this.getCurrentUser();

    return !!(token && user);
  }
}

export const authService = new AuthService();

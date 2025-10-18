/**
 * Mock API Server para desarrollo
 * Proporciona endpoints básicos para testing del frontend
 */

const http = require('http');
const url = require('url');

const PORT = process.env.PORT || 3001;

// Datos mock
const mockUsers = [
  {
    id: '1',
    email: 'admin@secureapprove.com',
    name: 'Admin User',
    role: 'admin',
    isActive: true,
  },
  {
    id: '2',
    email: 'user@secureapprove.com',
    name: 'Regular User',
    role: 'user',
    isActive: true,
  },
];

const mockRequests = [
  {
    id: '1',
    title: 'Aprobación de Compra',
    description: 'Solicitud de aprobación para compra de equipos',
    amount: 5000,
    status: 'pending',
    requesterId: '2',
    requester: { name: 'Regular User', email: 'user@secureapprove.com' },
    createdAt: new Date().toISOString(),
    approvers: [],
  },
  {
    id: '2',
    title: 'Autorización de Pago',
    description: 'Pago a proveedor por servicios',
    amount: 15000,
    status: 'approved',
    requesterId: '2',
    requester: { name: 'Regular User', email: 'user@secureapprove.com' },
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    approvers: [{ userId: '1', approvedAt: new Date().toISOString() }],
  },
];

// Helper para respuestas JSON
function sendJSON(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  });
  res.end(JSON.stringify(data));
}

// Handler de rutas
const routes = {
  // Health check
  '/health': (req, res) => {
    sendJSON(res, 200, { status: 'ok', timestamp: new Date().toISOString() });
  },

  // Auth endpoints
  '/api/auth/register/options': (req, res) => {
    sendJSON(res, 200, {
      challenge: Buffer.from('mock-challenge').toString('base64'),
      rp: { name: 'SecureApprove', id: 'localhost' },
      user: {
        id: 'mock-user-id',
        name: 'test@example.com',
        displayName: 'Test User',
      },
      pubKeyCredParams: [
        { type: 'public-key', alg: -7 },
        { type: 'public-key', alg: -257 },
      ],
      timeout: 60000,
      attestation: 'none',
      authenticatorSelection: {
        authenticatorAttachment: 'platform',
        requireResidentKey: false,
        userVerification: 'preferred',
      },
    });
  },

  '/api/auth/login/options': (req, res) => {
    sendJSON(res, 200, {
      challenge: Buffer.from('mock-challenge').toString('base64'),
      timeout: 60000,
      rpId: 'localhost',
      userVerification: 'preferred',
    });
  },

  '/api/auth/me': (req, res) => {
    sendJSON(res, 200, mockUsers[0]);
  },

  // Users endpoints
  '/api/users': (req, res) => {
    sendJSON(res, 200, mockUsers);
  },

  '/api/users/stats': (req, res) => {
    sendJSON(res, 200, {
      totalUsers: mockUsers.length,
      activeUsers: mockUsers.filter((u) => u.isActive).length,
      adminUsers: mockUsers.filter((u) => u.role === 'admin').length,
    });
  },

  // Requests endpoints
  '/api/requests': (req, res) => {
    const parsedUrl = url.parse(req.url, true);
    const status = parsedUrl.query.status;

    let filteredRequests = mockRequests;
    if (status) {
      filteredRequests = mockRequests.filter((r) => r.status === status);
    }

    sendJSON(res, 200, {
      data: filteredRequests,
      total: filteredRequests.length,
      page: 1,
      limit: 10,
    });
  },

  '/api/requests/stats': (req, res) => {
    sendJSON(res, 200, {
      total: mockRequests.length,
      pending: mockRequests.filter((r) => r.status === 'pending').length,
      approved: mockRequests.filter((r) => r.status === 'approved').length,
      rejected: mockRequests.filter((r) => r.status === 'rejected').length,
      totalAmount: mockRequests.reduce((sum, r) => sum + r.amount, 0),
    });
  },

  // Dashboard stats
  '/api/dashboard/stats': (req, res) => {
    sendJSON(res, 200, {
      users: {
        total: mockUsers.length,
        active: mockUsers.filter((u) => u.isActive).length,
      },
      requests: {
        total: mockRequests.length,
        pending: mockRequests.filter((r) => r.status === 'pending').length,
        approved: mockRequests.filter((r) => r.status === 'approved').length,
        rejected: mockRequests.filter((r) => r.status === 'rejected').length,
      },
      amounts: {
        total: mockRequests.reduce((sum, r) => sum + r.amount, 0),
        pending: mockRequests
          .filter((r) => r.status === 'pending')
          .reduce((sum, r) => sum + r.amount, 0),
        approved: mockRequests
          .filter((r) => r.status === 'approved')
          .reduce((sum, r) => sum + r.amount, 0),
      },
      recentActivity: mockRequests.slice(0, 5).map((r) => ({
        id: r.id,
        type: 'approval_request',
        description: r.title,
        timestamp: r.createdAt,
        user: r.requester.name,
      })),
    });
  },
};

// Crear servidor
const server = http.createServer((req, res) => {
  // Manejar CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(200, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    });
    res.end();
    return;
  }

  // Parsear URL
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;

  console.log(`[${new Date().toISOString()}] ${req.method} ${pathname}`);

  // Buscar ruta exacta
  if (routes[pathname]) {
    routes[pathname](req, res);
    return;
  }

  // Buscar ruta con parámetros (ejemplo: /api/users/1)
  for (const [route, handler] of Object.entries(routes)) {
    if (pathname.startsWith(route) && route !== '/') {
      handler(req, res);
      return;
    }
  }

  // Ruta no encontrada
  sendJSON(res, 404, {
    error: 'Not Found',
    message: `Route ${pathname} not found`,
  });
});

// Iniciar servidor
server.listen(PORT, () => {
  console.log(`
╔═══════════════════════════════════════════╗
║   🚀 Mock API Server                      ║
║   ✅ Running on http://localhost:${PORT}    ║
║   📝 Available endpoints:                 ║
║      - GET  /health                       ║
║      - POST /api/auth/register/options    ║
║      - POST /api/auth/login/options       ║
║      - GET  /api/auth/me                  ║
║      - GET  /api/users                    ║
║      - GET  /api/requests                 ║
║      - GET  /api/requests/stats           ║
║      - GET  /api/dashboard/stats          ║
╚═══════════════════════════════════════════╝
  `);
});

// Manejo de errores
server.on('error', (err) => {
  console.error('❌ Server error:', err);
  process.exit(1);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('📋 SIGTERM received, closing server...');
  server.close(() => {
    console.log('✅ Server closed');
    process.exit(0);
  });
});

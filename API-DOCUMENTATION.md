# SecureApprove Django - API Documentation

## Overview

SecureApprove provides a comprehensive RESTful API for managing approval workflows. The API is built with Django REST Framework and includes authentication, request management, billing, and dashboard functionality.

## Base URL

```
http://localhost:8000/api/
```

## Authentication

The API supports multiple authentication methods:

1. **JWT Token Authentication** (Recommended for applications)
2. **Session Authentication** (For web interface)

### JWT Authentication

#### Obtain Token
```http
POST /api/auth/token/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "your_password"
}
```

Response:
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Refresh Token
```http
POST /api/auth/token/refresh/
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Using Token
Include the token in the Authorization header:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/token/` | Obtain JWT token |
| POST | `/api/auth/token/refresh/` | Refresh JWT token |
| POST | `/api/auth/register/` | User registration |
| GET | `/api/auth/user/` | Get current user info |
| PUT | `/api/auth/user/` | Update user profile |

### Requests Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/requests/` | List all requests |
| POST | `/api/requests/` | Create new request |
| GET | `/api/requests/{id}/` | Get request details |
| PUT | `/api/requests/{id}/` | Update request |
| DELETE | `/api/requests/{id}/` | Delete request |
| POST | `/api/requests/{id}/approve/` | Approve request |
| POST | `/api/requests/{id}/reject/` | Reject request |
| GET | `/api/requests/pending/` | List pending requests |
| GET | `/api/requests/export/` | Export requests to CSV |

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats/` | Get dashboard statistics |
| GET | `/api/dashboard/recent/` | Get recent requests |
| GET | `/api/dashboard/chart-data/` | Get chart data |

### Billing

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/billing/plans/` | List available plans |
| GET | `/api/billing/subscription/` | Get current subscription |
| POST | `/api/billing/subscribe/` | Subscribe to plan |
| POST | `/api/billing/cancel/` | Cancel subscription |
| GET | `/api/billing/invoices/` | List invoices |
| POST | `/api/billing/webhooks/mercadopago/` | MercadoPago webhook |

## Data Models

### ApprovalRequest

```json
{
    "id": 1,
    "title": "Office Supplies Purchase",
    "description": "Need new office supplies for Q1",
    "category": "expense",
    "priority": "medium",
    "status": "pending",
    "amount": "150.00",
    "created_by": {
        "id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe"
    },
    "created_at": "2024-01-15T10:30:00Z",
    "approved_by": null,
    "approved_at": null,
    "rejection_reason": null,
    "tenant": 1,
    "metadata": {
        "expense_category": "office_supplies",
        "cost_center": "IT Department"
    }
}
```

### User

```json
{
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "date_joined": "2024-01-01T00:00:00Z",
    "tenant": {
        "id": 1,
        "name": "Company Name"
    }
}
```

## Request Categories

The API supports the following request categories:

1. **expense** - Expense reimbursements
2. **purchase** - Purchase orders
3. **travel** - Travel requests
4. **contract** - Contract approvals
5. **document** - Document approvals
6. **other** - General requests

### Category-Specific Fields

#### Expense Requests
- `expense_category`: office_supplies, travel, meals, etc.
- `cost_center`: Department or cost center
- `receipt_reference`: Receipt number/reference

#### Purchase Requests
- `vendor`: Vendor/supplier name
- `cost_center`: Department or cost center

#### Travel Requests
- `destination`: Travel destination
- `start_date`: Travel start date
- `end_date`: Travel end date

#### Contract Requests
- `contract_type`: Type of contract
- `vendor`: Vendor/partner name

#### Document Requests
- `document_id`: Document identifier
- `document_type`: Type of document

## Filtering and Searching

### Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `search` | Search in title/description | `?search=office` |
| `category` | Filter by category | `?category=expense` |
| `status` | Filter by status | `?status=pending` |
| `priority` | Filter by priority | `?priority=high` |
| `created_by` | Filter by creator | `?created_by=1` |
| `date_from` | Filter from date | `?date_from=2024-01-01` |
| `date_to` | Filter to date | `?date_to=2024-01-31` |
| `ordering` | Order results | `?ordering=-created_at` |

### Example Requests

#### Get pending high-priority requests
```http
GET /api/requests/?status=pending&priority=high
```

#### Search for expense requests
```http
GET /api/requests/?category=expense&search=office
```

#### Get requests from last month
```http
GET /api/requests/?date_from=2024-01-01&date_to=2024-01-31
```

## Pagination

All list endpoints support pagination:

```json
{
    "count": 150,
    "next": "http://localhost:8000/api/requests/?page=2",
    "previous": null,
    "results": [...]
}
```

Default page size: 20 items

## Error Handling

The API uses standard HTTP status codes:

- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

### Error Response Format

```json
{
    "error": "Validation failed",
    "details": {
        "title": ["This field is required."],
        "amount": ["Ensure this value is greater than 0."]
    }
}
```

## Rate Limiting

API endpoints are rate limited:

- **Anonymous users**: 100 requests/hour
- **Authenticated users**: 1000 requests/hour
- **Premium plans**: 5000 requests/hour

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Webhooks

### MercadoPago Webhook

The API supports MercadoPago payment webhooks:

```http
POST /api/billing/webhooks/mercadopago/
Content-Type: application/json

{
    "action": "payment.created",
    "api_version": "v1",
    "data": {
        "id": "123456789"
    },
    "date_created": "2024-01-15T10:30:00.000-04:00",
    "id": 12345,
    "live_mode": true,
    "type": "payment",
    "user_id": "44444"
}
```

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## SDKs and Examples

### JavaScript/Node.js

```javascript
const axios = require('axios');

// Authenticate
const response = await axios.post('http://localhost:8000/api/auth/token/', {
    email: 'user@example.com',
    password: 'password'
});

const token = response.data.access;

// Create request
await axios.post('http://localhost:8000/api/requests/', {
    title: 'New Request',
    description: 'Request description',
    category: 'expense',
    priority: 'medium',
    amount: '100.00'
}, {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});
```

### Python

```python
import requests

# Authenticate
response = requests.post('http://localhost:8000/api/auth/token/', {
    'email': 'user@example.com',
    'password': 'password'
})

token = response.json()['access']

# Create request
requests.post('http://localhost:8000/api/requests/', {
    'title': 'New Request',
    'description': 'Request description',
    'category': 'expense',
    'priority': 'medium',
    'amount': '100.00'
}, headers={
    'Authorization': f'Bearer {token}'
})
```

### cURL

```bash
# Authenticate
TOKEN=$(curl -X POST http://localhost:8000/api/auth/token/ \
    -H "Content-Type: application/json" \
    -d '{"email":"user@example.com","password":"password"}' \
    | jq -r '.access')

# Create request
curl -X POST http://localhost:8000/api/requests/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
        "title": "New Request",
        "description": "Request description",
        "category": "expense",
        "priority": "medium",
        "amount": "100.00"
    }'
```
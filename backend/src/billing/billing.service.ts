import { Injectable, BadRequestException, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import { Tenant } from '../users/schemas/tenant.schema';
import { User } from '../users/schemas/user.schema';

// Lazy import to avoid issues if SDK not installed in some envs
let MercadoPago: any;
try {
  MercadoPago = require('mercadopago');
} catch (e) {
  // noop
}

@Injectable()
export class BillingService {
  private logger = new Logger(BillingService.name);

  constructor(
    private readonly config: ConfigService,
    @InjectModel(Tenant.name) private tenantModel: Model<Tenant>,
    @InjectModel(User.name) private userModel: Model<User>,
  ) {}

  async createCheckoutPreference(params: {
    planId: 'starter' | 'growth' | 'scale' | string;
    seats: number;
    customerEmail: string;
    successUrl: string;
    failureUrl: string;
    pendingUrl?: string;
    locale?: string;
  }) {
    const accessToken = this.config.get<string>('MP_ACCESS_TOKEN');
    if (!accessToken) throw new BadRequestException('Mercado Pago not configured');
    if (!MercadoPago) throw new BadRequestException('Mercado Pago SDK missing');

    MercadoPago.configure({ access_token: accessToken });

  const unitPrice = this.getPlanPrice(params.planId, params.seats);
    const preference = {
      items: [
        {
          id: params.planId,
          title: `SecureApprove ${params.planId} (${params.seats} seats)`,
          quantity: 1,
          currency_id: 'USD',
          unit_price: unitPrice,
        },
      ],
      payer: {
        email: params.customerEmail,
      },
      back_urls: {
        success: params.successUrl,
        failure: params.failureUrl,
        pending: params.pendingUrl || params.failureUrl,
      },
      auto_return: 'approved',
      metadata: {
        planId: params.planId,
        seats: params.seats,
        approverLimit: this.getApproverLimit(params.planId),
        customerEmail: params.customerEmail,
      },
      notification_url: this.config.get('MP_WEBHOOK_URL') || `http://localhost:3001/api/billing/webhook`,
    } as any;

    const result = await MercadoPago.preferences.create(preference);
    return result?.body;
  }

  async handleWebhook(body: any) {
    try {
      // Mercado Pago can send notifications in 2 steps: topic+id, then we fetch payment
      const accessToken = this.config.get<string>('MP_ACCESS_TOKEN');
      if (!accessToken) throw new BadRequestException('Mercado Pago not configured');
      if (!MercadoPago) throw new BadRequestException('Mercado Pago SDK missing');
      MercadoPago.configure({ access_token: accessToken });

      let paymentInfo: any = null;
      if (body?.type === 'payment' || body?.topic === 'payment') {
        const id = body?.data?.id || body?.id;
        if (id) {
          const resp = await MercadoPago.payment.findById(id);
          paymentInfo = resp?.body;
        }
      } else {
        // Some environments send entire payment object
        paymentInfo = body;
      }

      if (!paymentInfo) {
        this.logger.warn('Webhook without payment info');
        return { received: true };
      }

      if (paymentInfo.status === 'approved') {
        const metadata = paymentInfo?.metadata || {};
  const planId = metadata.planId || 'starter';
        const seats = Number(metadata.seats || 5);
  const approverLimit = Number(metadata.approverLimit ?? this.getApproverLimit(planId));
        const email = metadata.customerEmail || paymentInfo?.payer?.email;
        if (!email) {
          this.logger.warn('Approved payment without email');
          return { ok: true };
        }

        // Ensure user exists
        let user = await this.userModel.findOne({ email }).exec();
        if (!user) {
          user = new this.userModel({ email, role: 'tenant_admin', isActive: true });
          await user.save();
        }

        // Create tenant if not already linked
        if (!user.tenantId) {
          const key = email.split('@')[0].replace(/[^a-z0-9-]/gi, '').toLowerCase().slice(0, 24) || `tenant${Date.now()}`;
          const name = key.charAt(0).toUpperCase() + key.slice(1);
          const tenant = new this.tenantModel({
            key,
            name,
            isActive: true,
            planId,
            seats,
            approverLimit,
            status: 'active',
            billing: {
              provider: 'mercadopago',
              customerId: String(paymentInfo.payer?.id || ''),
              subscriptionId: String(paymentInfo.id || ''),
              currentPeriodEnd: undefined,
            },
          });
          await tenant.save();
          user.tenantId = tenant._id.toString();
          user.role = 'tenant_admin';
          await user.save();
        }
      }

      return { ok: true };
    } catch (e: any) {
      this.logger.error('Webhook processing failed', e?.stack || e?.message || e);
      throw new BadRequestException('Webhook error');
    }
  }

  private getPlanPrice(planId: string, seats: number) {
    // USD pricing per month (flat, not per seat) based on requested tiers
    // starter: 2 approvers = $25, growth: up to 6 approvers = $45, scale: unlimited approvers = $65
    const usdFlat: Record<string, number> = {
      starter: 25,
      growth: 45,
      scale: 65,
    };
    const unitUsd = usdFlat[planId] ?? 45;
    // If your MP account is in ARS, convert or set your account to USD; here we keep unit as-is
    return unitUsd;
  }

  private getApproverLimit(planId: string) {
    switch (planId) {
      case 'starter':
        return 2;
      case 'growth':
        return 6;
      case 'scale':
        return 999999; // effectively unlimited
      default:
        return 6;
    }
  }
}

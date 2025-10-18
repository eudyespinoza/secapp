import { Body, Controller, Headers, Post, Req } from '@nestjs/common';
import { BillingService } from './billing.service';

@Controller('billing')
export class BillingController {
  constructor(private readonly billing: BillingService) {}

  @Post('checkout')
  async createCheckout(@Body() body: any, @Headers('origin') origin?: string) {
    const {
      planId = 'pro',
      seats = 5,
      customerEmail,
      successUrl,
      failureUrl,
      pendingUrl,
      locale,
    } = body || {};
    const result = await this.billing.createCheckoutPreference({
      planId,
      seats: Number(seats || 1),
      customerEmail,
      successUrl: successUrl || `${origin || 'http://localhost:3000'}/es/settings/team?status=success`,
      failureUrl: failureUrl || `${origin || 'http://localhost:3000'}/es/settings/team?status=failure`,
      pendingUrl,
      locale,
    });
    return result;
  }

  // Mercado Pago send webhook as POST to configured notification_url
  @Post('webhook')
  async webhook(@Req() req: any, @Body() body: any) {
    // Body can be form or json; Nest will parse when possible
    return this.billing.handleWebhook(body || req.body || {});
  }
}

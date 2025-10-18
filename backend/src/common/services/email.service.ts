import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class EmailService {
  private readonly logger = new Logger(EmailService.name);
  private transporter: any | null = null;
  private initialized = false;

  constructor(private config: ConfigService) {}

  private init() {
    if (this.initialized) return;
    this.initialized = true;
    try {
      const host = this.config.get<string>('SMTP_HOST');
      const port = parseInt(this.config.get<string>('SMTP_PORT') || '0', 10);
      const user = this.config.get<string>('SMTP_USER');
      const pass = this.config.get<string>('SMTP_PASS');
      if (!host || !port || !user || !pass) {
        this.logger.warn('SMTP not configured (SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS). Falling back to console logging.');
        this.transporter = null;
        return;
      }
      // Dynamically require nodemailer so that absence doesn't break build
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const nodemailer = require('nodemailer');
      this.transporter = nodemailer.createTransport({
        host,
        port,
        secure: port === 465,
        auth: { user, pass },
      });
    } catch (err) {
      this.logger.warn(`Failed to initialize SMTP transporter: ${err?.message || err}`);
      this.transporter = null;
    }
  }

  async sendInviteEmail(params: { to: string; tenantName?: string; role: string; link: string; locale?: string }) {
    this.init();
    const from = this.config.get<string>('SMTP_FROM') || 'no-reply@secureapprove.local';
    const locale = params.locale || this.config.get<string>('DEFAULT_LOCALE') || 'en';

    const subjects: Record<string, string> = {
      en: `You're invited to SecureApprove`,
      es: `Has sido invitado a SecureApprove`,
      'pt-BR': `Você foi convidado para o SecureApprove`,
    };
    const subject = subjects[locale] || subjects['en'];

    const html = `
      <div style="font-family:Arial,sans-serif; max-width:600px;">
        <h2>${subject}</h2>
        <p>
          ${params.tenantName ? `<strong>${params.tenantName}</strong> ` : ''}
          invited you as <strong>${params.role}</strong>.
        </p>
        <p>
          Click the button below to join:
        </p>
        <p>
          <a href="${params.link}" style="background:#4f46e5;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;">
            Accept invite
          </a>
        </p>
        <p>If the button doesn't work, copy this link:</p>
        <code>${params.link}</code>
      </div>
    `;

    if (!this.transporter) {
      this.logger.log(`[INVITE EMAIL] to=${params.to} role=${params.role} link=${params.link}`);
      return { sent: false, logged: true };
    }

    await this.transporter.sendMail({ from, to: params.to, subject, html });
    this.logger.log(`Invite email sent to ${params.to}`);
    return { sent: true };
  }
}

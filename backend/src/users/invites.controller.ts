import { Controller, Get, Post, Delete, Body, Param, UseGuards, Req, ForbiddenException } from '@nestjs/common';
import { InvitesService } from './invites.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { EmailService } from '../common/services/email.service';

@Controller('users/invites')
@UseGuards(JwtAuthGuard)
export class InvitesController {
  constructor(
    private readonly invitesService: InvitesService,
    private readonly email: EmailService,
  ) {}

  @Get()
  async list(@Req() req: any) {
    const user = req.user;
    if (user.role !== 'superadmin' && user.role !== 'tenant_admin') {
      throw new ForbiddenException('Only tenant_admin or superadmin can create invites');
    }
    const tenantId = user.role === 'superadmin' ? (req.query.tenantId as string) : user.tenantId;
    return this.invitesService.list(tenantId);
  }

  @Post()
  async create(@Req() req: any, @Body() body: { email: string; role: string; tenantId?: string }) {
    const user = req.user;
    if (user.role !== 'superadmin' && user.role !== 'tenant_admin') {
      throw new ForbiddenException('Only tenant_admin or superadmin can create invites');
    }
    const tenantId = user.role === 'superadmin' ? (body.tenantId as string) : user.tenantId;
    const invite = await this.invitesService.create({ tenantId, email: body.email, role: body.role, createdBy: user.sub });
    // Best-effort email send; prefer Origin header (frontend URL), fall back to host headers
    try {
      const originHeader = req.headers.origin as string | undefined;
      const computedHost = (req.headers['x-forwarded-host'] as string) || (req.headers.host as string) || 'localhost:3000';
      const scheme = (req.headers['x-forwarded-proto'] as string) || 'http';
      const base = originHeader || `${scheme}://${computedHost}`;
      const rawLocale = (req.headers['x-locale'] as string) || 'en';
      const link = `${base}/${rawLocale}/auth/invite/${invite.token}`;
      await this.email.sendInviteEmail({ to: invite.email, role: invite.role, link, locale: String(rawLocale) });
    } catch (err) {
      // swallow email errors to not block API response
    }
    return invite;
  }

  @Delete(':id')
  async revoke(@Req() req: any, @Param('id') id: string) {
    const user = req.user;
    if (user.role !== 'superadmin' && user.role !== 'tenant_admin') {
      throw new ForbiddenException('Only tenant_admin or superadmin can revoke invites');
    }
    const tenantId = user.role === 'superadmin' ? (req.query.tenantId as string) : user.tenantId;
    return this.invitesService.revoke(tenantId, id);
  }
}

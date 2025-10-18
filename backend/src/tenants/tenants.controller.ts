import { Controller, Get, Post, Put, Delete, Body, Param, UseGuards, ForbiddenException, Req } from '@nestjs/common';
import { TenantsService } from './tenants.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';

@Controller('tenants')
@UseGuards(JwtAuthGuard)
export class TenantsController {
  constructor(private readonly tenantsService: TenantsService) {}

  private assertSuperAdmin(req: any) {
    if (!req.user || req.user.role !== 'superadmin') {
      throw new ForbiddenException('Superadmin role required');
    }
  }

  @Get()
  async list(@Req() req: any) {
    this.assertSuperAdmin(req);
    return this.tenantsService.list();
  }

  @Get('me')
  async getMe(@Req() req: any) {
    const user = req.user;
    if (user?.role === 'superadmin') {
      const tenantId = req.query.tenantId as string;
      if (!tenantId) {
        throw new ForbiddenException('tenantId query is required for superadmin');
      }
      return this.tenantsService.get(tenantId);
    }
    if (!user?.tenantId) {
      throw new ForbiddenException('No tenant associated with user');
    }
    return this.tenantsService.get(user.tenantId);
  }

  @Get(':id')
  async get(@Req() req: any, @Param('id') id: string) {
    this.assertSuperAdmin(req);
    return this.tenantsService.get(id);
  }

  @Post()
  async create(@Req() req: any, @Body() data: { key: string; name: string; domains?: string[] }) {
    this.assertSuperAdmin(req);
    return this.tenantsService.create(data);
  }

  @Put(':id')
  async update(@Req() req: any, @Param('id') id: string, @Body() data: any) {
    this.assertSuperAdmin(req);
    return this.tenantsService.update(id, data);
  }

  @Delete(':id')
  async remove(@Req() req: any, @Param('id') id: string) {
    this.assertSuperAdmin(req);
    return this.tenantsService.remove(id);
  }
}

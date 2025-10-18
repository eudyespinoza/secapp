import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards, ForbiddenException, Req } from '@nestjs/common';
import { UsersService } from './users.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { CurrentUser } from '../auth/decorators/current-user.decorator';

@Controller('users')
@UseGuards(JwtAuthGuard)
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Get()
  async findAll(
    @CurrentUser() user: any,
    @Query('role') role?: string,
    @Query('isActive') isActive?: string,
    @Query('search') search?: string,
  ) {
    const filters: any = {};
    if (role) filters.role = role;
    if (isActive !== undefined) filters.isActive = isActive === 'true';
    if (search) filters.search = search;
    if (user?.role !== 'superadmin') {
      filters.tenantId = user?.tenantId;
    }
    return this.usersService.findAll(filters);
  }

  @Get('stats')
  async getStats() {
    return this.usersService.getUserStats();
  }

  @Get(':id')
  async findOne(@Param('id') id: string) {
    return this.usersService.findOne(id);
  }

  @Post()
  async create(
    @CurrentUser() user: any,
    @Body() userData: {
    email: string;
    name?: string;
    firstName?: string;
    lastName?: string;
    phone?: string;
    role?: string;
  }) {
    if (user?.role === 'superadmin') {
      // superadmin must specify tenantId explicitly when creating tenant admins/users
      return this.usersService.create(userData);
    }
    // tenant admins create users within their tenant only
    if (user?.role !== 'tenant_admin') {
      throw new ForbiddenException('Only tenant_admin can create users in tenant');
    }
    return this.usersService.create({ ...userData, tenantId: user?.tenantId });
  }

  @Put(':id')
  async update(@Param('id') id: string, @Body() userData: any) {
    return this.usersService.update(id, userData);
  }

  @Delete(':id')
  async remove(@Param('id') id: string) {
    return this.usersService.remove(id);
  }
}

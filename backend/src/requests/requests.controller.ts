import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards } from '@nestjs/common';
import { RequestsService } from './requests.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { CurrentUser } from '../auth/decorators/current-user.decorator';

@Controller('requests')
@UseGuards(JwtAuthGuard)
export class RequestsController {
  constructor(private readonly requestsService: RequestsService) {}

  @Get()
  async findAll(
    @CurrentUser() user: any,
    @Query('status') status?: string,
    @Query('requesterId') requesterId?: string,
    @Query('approverId') approverId?: string,
    @Query('priority') priority?: string,
    @Query('page') page?: string,
    @Query('limit') limit?: string,
  ) {
    return this.requestsService.findAll({
      status,
      requesterId,
      approverId,
      priority,
      page: page ? parseInt(page) : undefined,
      limit: limit ? parseInt(limit) : undefined,
      tenantId: user?.tenantId,
    });
  }

  @Get('stats')
  async getStats(@Query('userId') userId?: string) {
    return this.requestsService.getStats(userId);
  }

  @Get('recent')
  async getRecentActivity(@Query('limit') limit?: string) {
    return this.requestsService.getRecentActivity(
      limit ? parseInt(limit) : undefined
    );
  }

  @Get(':id')
  async findOne(@Param('id') id: string) {
    return this.requestsService.findOne(id);
  }

  @Post()
  async create(
    @CurrentUser() user: any,
    @Body() requestData: {
      title: string;
      description: string;
      category: string;
      amount: number;
      priority: string;
      metadata?: any;
      expiresAt?: Date;
    }
  ) {
    return this.requestsService.create({
      ...requestData,
      requesterId: user.sub, // sub es el ID del usuario en el token JWT
      tenantId: user?.tenantId,
    });
  }

  @Put(':id/approve')
  async approve(
    @CurrentUser() user: any,
    @Param('id') id: string,
    @Body() data: { comment?: string }
  ) {
    return this.requestsService.approve(id, user.sub, data.comment);
  }

  @Put(':id/reject')
  async reject(
    @CurrentUser() user: any,
    @Param('id') id: string,
    @Body() data: { reason: string }
  ) {
    return this.requestsService.reject(id, user.sub, data.reason);
  }

  @Put(':id/cancel')
  async cancel(
    @CurrentUser() user: any,
    @Param('id') id: string
  ) {
    return this.requestsService.cancel(id, user.sub);
  }

  @Delete(':id')
  async remove(@Param('id') id: string) {
    return this.requestsService.remove(id);
  }
}
